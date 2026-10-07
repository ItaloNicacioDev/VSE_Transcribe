"""Transcribe operator for VSE_Transcribe.

Runs transcription using the selected engine and stores the result.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from VSE_Transcrib.models.transcript import Transcript

try:
    import bpy
    from bpy.props import StringProperty
    from bpy.types import Operator, Context
    _HAS_BPY = True
except ImportError:
    # Outside Blender - for syntax checking only
    class Operator:
        pass
    class Context:
        pass
    def StringProperty(**kwargs):
        return None
    _HAS_BPY = False


class VSETRANSCRIBE_OT_transcribe(Operator):
    """Transcribe audio using the selected engine."""

    bl_idname = "vse_transcribe.transcribe"
    bl_label = "Transcribe Audio"
    bl_description = "Transcribe selected audio using the configured engine"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can run."""
        if not _HAS_BPY:
            return False
        settings = context.scene.vse_transcribe
        # Need either an audio strip selected or audio_source path
        has_audio_strip = cls._get_active_audio_strip(context) is not None
        has_audio_source = bool(settings.audio_source and os.path.exists(settings.audio_source))
        return has_audio_strip or has_audio_source

    def execute(self, context: Context) -> set:
        """Execute transcription."""
        if not _HAS_BPY:
            self.report({"ERROR"}, "Not running inside Blender")
            return {"CANCELLED"}

        settings = context.scene.vse_transcribe

        # Get audio file path
        audio_path = self._get_audio_path(context, settings)
        if not audio_path:
            self.report({"ERROR"}, "No audio source found. Select an audio strip or set audio file path.")
            return {"CANCELLED"}

        if not os.path.exists(audio_path):
            self.report({"ERROR"}, f"Audio file not found: {audio_path}")
            return {"CANCELLED"}

        # Mark as transcribing
        settings.is_transcribing = True

        try:
            # Import engine and config
            from VSE_Transcrib.engines import get_engine
            from VSE_Transcrib.engines.local_whisper import LocalWhisperConfig
            from VSE_Transcrib.engines.external_api import ExternalAPIConfig
            from VSE_Transcrib.engines.base import EngineNotAvailableError, InvalidConfigError, TranscriptionError

            # Get engine class
            try:
                engine_cls = get_engine(settings.engine_type)
            except Exception as e:
                self.report({"ERROR"}, f"Engine '{settings.engine_type}' not available: {e}")
                return {"CANCELLED"}

            engine = engine_cls()

            # Build engine config from settings
            config = self._build_engine_config(settings)
            if config is None:
                return {"CANCELLED"}

            # Report progress
            self.report({"INFO"}, f"Starting transcription with {engine.name}...")

            # Run transcription
            transcript = engine.transcribe(audio_path, config)

            # Validate transcript
            from VSE_Transcrib.core.transcription import validate_transcript, normalize_transcript
            problems = validate_transcript(transcript)
            if problems:
                self.report({"WARNING"}, f"Transcript validation issues: {'; '.join(problems)}")

            # Normalize
            transcript = normalize_transcript(transcript)

            # Serialize and store
            transcript_json = self._transcript_to_json(transcript)
            settings.transcript_storage = transcript_json

            self.report({"INFO"}, f"Transcription complete: {len(transcript.segments)} segments, {transcript.total_words} words")
            return {"FINISHED"}

        except EngineNotAvailableError as e:
            self.report({"ERROR"}, f"Engine not available: {e}")
            return {"CANCELLED"}
        except InvalidConfigError as e:
            self.report({"ERROR"}, f"Invalid configuration: {e}")
            return {"CANCELLED"}
        except TranscriptionError as e:
            self.report({"ERROR"}, f"Transcription failed: {e}")
            return {"CANCELLED"}
        except Exception as e:
            self.report({"ERROR"}, f"Unexpected error: {e}")
            return {"CANCELLED"}
        finally:
            settings.is_transcribing = False

    @staticmethod
    def _get_active_audio_strip(context: Context):
        """Get the active sound strip in the VSE."""
        if not _HAS_BPY:
            return None

        seq_editor = context.scene.sequence_editor
        if not seq_editor:
            return None

        for strip in context.selected_sequences:
            if strip.type == "SOUND":
                return strip

        # Also check active strip
        active = seq_editor.active_strip
        if active and active.type == "SOUND":
            return active

        return None

    def _get_audio_path(self, context: Context, settings) -> str | None:
        """Get the audio file path from strip or settings."""
        # Try selected/active sound strip first
        strip = self._get_active_audio_strip(context)
        if strip and strip.sound:
            filepath = bpy.path.abspath(strip.sound.filepath)
            if os.path.exists(filepath):
                return filepath

        # Fallback to audio_source setting
        if settings.audio_source:
            return bpy.path.abspath(settings.audio_source)

        return None

    def _build_engine_config(self, settings):
        """Build engine config from settings."""
        if settings.engine_type == "local_whisper":
            from VSE_Transcrib.engines.local_whisper import LocalWhisperConfig
            lw = settings.local_whisper
            return LocalWhisperConfig(
                language=lw.language or None,
                model_size=lw.model_size,
                device=lw.device,
                compute_type=lw.compute_type,
                word_timestamps=lw.word_timestamps,
            )
        elif settings.engine_type == "external_api":
            from VSE_Transcrib.engines.external_api import ExternalAPIConfig
            ea = settings.external_api
            if not ea.endpoint or not ea.api_key:
                self.report({"ERROR"}, "External API requires endpoint and API key")
                return None
            return ExternalAPIConfig(
                language=ea.language or None,
                endpoint=ea.endpoint,
                api_key=ea.api_key,
                model=ea.model,
                timeout=ea.timeout,
            )
        else:
            self.report({"ERROR"}, f"Unknown engine type: {settings.engine_type}")
            return None

    def _transcript_to_json(self, transcript: "Transcript") -> str:
        """Serialize Transcript to JSON."""
        from VSE_Transcrib.models.transcript import TranscriptSegment, TranscriptWord

        data = {
            "language": transcript.language,
            "duration": transcript.duration,
            "metadata": transcript.metadata,
            "segments": [],
        }

        for seg in transcript.segments:
            seg_data = {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "words": [],
            }
            for word in seg.words:
                seg_data["words"].append({
                    "text": word.text,
                    "start": word.start,
                    "end": word.end,
                    "confidence": word.confidence,
                })
            data["segments"].append(seg_data)

        return json.dumps(data, ensure_ascii=False)


# Registration handled by __init__.py