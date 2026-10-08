"""Generate subtitles operator for VSE_Transcribe.

Converts stored transcript to SubtitleBlocks and creates Text Strips in VSE.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from VSE_Transcrib.models.transcript import Transcript

try:
    import bpy
    from bpy.types import Operator, Context
    _HAS_BPY = True
except ImportError:
    class Operator:
        pass
    class Context:
        pass
    _HAS_BPY = False


class VSETRANSCRIBE_OT_generate_subtitles(Operator):
    """Generate subtitle Text Strips from transcribed text."""

    bl_idname = "vse_transcribe.generate_subtitles"
    bl_label = "Generate Subtitles"
    bl_description = "Create subtitle Text Strips from the stored transcript"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can run."""
        if not _HAS_BPY:
            return False
        settings = context.scene.vse_transcribe
        return bool(settings.transcript_storage)

    def execute(self, context: Context) -> set:
        """Generate subtitle strips."""
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
            self.report({"WARNING"}, "Transcript is empty, no subtitles to generate")
            return {"CANCELLED"}

        # Prepare subtitle config
        from VSE_Transcrib.core.subtitle_engine import SubtitleConfig, prepare_subtitles
        subtitle_config = SubtitleConfig(
            max_chars_per_line=settings.subtitle.max_chars_per_line,
            max_lines=settings.subtitle.max_lines,
            min_duration=settings.subtitle.min_duration,
            gap_threshold=settings.subtitle.gap_threshold,
        )

        # Generate subtitle blocks
        try:
            blocks = prepare_subtitles(transcript, subtitle_config)
        except Exception as e:
            self.report({"ERROR"}, f"Failed to prepare subtitles: {e}")
            return {"CANCELLED"}

        if not blocks:
            self.report({"WARNING"}, "No subtitle blocks generated")
            return {"CANCELLED"}

        # Get or create sequence editor
        scene = context.scene
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        sequencer = scene.sequence_editor

        # Create strips via StripManager
        from VSE_Transcrib.core.strip_manager import StripManager

        try:
            manager = StripManager(scene, sequencer)
            # Use a reasonable default channel (e.g., channel 5 for subtitles)
            channel = 5
            strips = manager.create_subtitle_strips(blocks, channel)

            # Store strip names for clearing later
            settings.generated_strips.clear()
            for strip in strips:
                item = settings.generated_strips.add()
                item.name = strip.name

            self.report({"INFO"}, f"Created {len(strips)} subtitle strips on channel {channel}")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to create subtitle strips: {e}")
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


# Registration handled by __init__.py