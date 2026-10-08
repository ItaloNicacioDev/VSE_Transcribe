"""Export subtitles operator for VSE_Transcribe.

Exports transcript or generated subtitles to SRT, VTT, or ASS format.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from VSE_Transcrib.models.transcript import Transcript

try:
    import bpy
    from bpy.props import EnumProperty, StringProperty
    from bpy.types import Operator, Context
    _HAS_BPY = True
except ImportError:
    class Operator:
        pass
    class Context:
        pass
    def EnumProperty(**kwargs):
        return None
    def StringProperty(**kwargs):
        return None
    _HAS_BPY = False


class VSETRANSCRIBE_OT_export_subtitles(Operator):
    """Export subtitles to file (SRT, VTT, ASS)."""

    bl_idname = "vse_transcribe.export_subtitles"
    bl_label = "Export Subtitles"
    bl_description = "Export transcript or generated subtitles to a file"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(
        name="File Path",
        description="Output file path",
        default="",
        subtype="FILE_PATH",
    )

    format: EnumProperty(
        name="Format",
        description="Subtitle format",
        items=[
            ("SRT", "SubRip (.srt)", "Standard subtitle format with timecodes"),
            ("VTT", "WebVTT (.vtt)", "Web video text tracks format"),
            ("ASS", "Advanced SubStation Alpha (.ass)", "Advanced formatting support"),
        ],
        default="SRT",
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can run."""
        if not _HAS_BPY:
            return False
        settings = context.scene.vse_transcribe
        return bool(settings.transcript_storage)

    def execute(self, context: Context) -> set:
        """Export subtitles to file."""
        if not _HAS_BPY:
            self.report({"ERROR"}, "Not running inside Blender")
            return {"CANCELLED"}

        settings = context.scene.vse_transcribe

        # Deserialize transcript with error handling
        try:
            transcript = self._json_to_transcript(settings.transcript_storage)
        except json.JSONDecodeError as e:
            self.report({"ERROR"}, f"Invalid transcript JSON: {e}")
            return {"CANCELLED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to parse transcript: {e}")
            return {"CANCELLED"}

        if transcript.is_empty:
            self.report({"WARNING"}, "Transcript is empty, nothing to export")
            return {"CANCELLED"}

        # Determine output path
        if not self.filepath:
            self.report({"ERROR"}, "No output file path specified")
            return {"CANCELLED"}

        filepath = bpy.path.abspath(self.filepath)

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        # Export based on format
        try:
            if self.format == "SRT":
                content = self._export_srt(transcript)
            elif self.format == "VTT":
                content = self._export_vtt(transcript)
            elif self.format == "ASS":
                content = self._export_ass(transcript, settings.subtitle)
            else:
                self.report({"ERROR"}, f"Unknown format: {self.format}")
                return {"CANCELLED"}

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            self.report({"INFO"}, f"Exported {len(transcript.segments)} segments to {filepath}")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}

    def _json_to_transcript(self, json_str: str) -> "Transcript":
        """Deserialize JSON to Transcript."""
        from VSE_Transcrib.models.transcript import Transcript, TranscriptSegment, TranscriptWord

        data = json.loads(json_str)

        segments = []
        for seg_data in data.get("segments", []):
            words = []
            for w_data in seg_data.get("words", []):
                words.append(TranscriptWord(
                    text=w_data["text"],
                    start=w_data["start"],
                    end=w_data["end"],
                    confidence=w_data.get("confidence"),
                ))

            segments.append(TranscriptSegment(
                start=seg_data["start"],
                end=seg_data["end"],
                text=seg_data["text"],
                words=words,
            ))

        return Transcript(
            language=data.get("language", "unknown"),
            duration=data.get("duration", 0.0),
            segments=segments,
            metadata=data.get("metadata", {}),
        )

    def _format_time_srt(self, seconds: float) -> str:
        """Format time for SRT (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_time_vtt(self, seconds: float) -> str:
        """Format time for VTT (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _format_time_ass(self, seconds: float) -> str:
        """Format time for ASS (H:MM:SS.cc)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

    def _export_srt(self, transcript: "Transcript") -> str:
        """Export to SRT format."""
        lines = []
        for i, seg in enumerate(transcript.segments, 1):
            lines.append(str(i))
            lines.append(f"{self._format_time_srt(seg.start)} --> {self._format_time_srt(seg.end)}")
            lines.append(seg.text)
            lines.append("")  # Blank line between entries
        return "\n".join(lines)

    def _export_vtt(self, transcript: "Transcript") -> str:
        """Export to WebVTT format."""
        lines = ["WEBVTT", ""]
        for seg in transcript.segments:
            lines.append(f"{self._format_time_vtt(seg.start)} --> {self._format_time_vtt(seg.end)}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)

    def _export_ass(self, transcript: "Transcript", subtitle_settings) -> str:
        """Export to ASS format using subtitle settings."""
        # ASS header with configurable style
        font_name = "Arial"
        font_size = 20
        primary_color = "&H00FFFFFF"
        outline_color = "&H00000000"
        back_color = "&H00000000"
        
        header = [
            "[Script Info]",
            "Title: VSE_Transcribe Export",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: TV.709",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},{back_color},0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        events = []
        for seg in transcript.segments:
            start = self._format_time_ass(seg.start)
            end = self._format_time_ass(seg.end)
            text = seg.text.replace("\n", "\\N")
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        return "\n".join(header + events)


# Registration handled by __init__.py