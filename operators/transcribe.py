"""Transcribe operator for VSE_Transcribe.

Runs transcription using the selected engine and stores the result.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from typing import TYPE_CHECKING, Callable, Optional

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


# Global storage for async transcription results
_transcription_results = {}
_transcription_lock = threading.Lock()


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
        # Need a SOUND or MOVIE strip selected
        return cls._get_active_audio_strip(context) is not None

    def execute(self, context: Context) -> set:
        """Execute transcription (async)."""
        if not _HAS_BPY:
            self.report({"ERROR"}, "Not running inside Blender")
            return {"CANCELLED"}

        settings = context.scene.vse_transcribe

        # Get audio strip (SOUND or MOVIE)
        strip = self._get_active_audio_strip(context)
        if not strip:
            self.report({"ERROR"}, "No audio strip selected. Select a SOUND or MOVIE strip in the VSE.")
            return {"CANCELLED"}

        # Extract audio from strip via sound.mixdown (fast, respects trims, volume, effects)
        self.report({"INFO"}, "Extracting audio from strip...")
        from VSE_Transcrib.utils.audio import extract_audio_from_strip
        audio_path = extract_audio_from_strip(strip, context.scene)

        if not audio_path or not os.path.exists(audio_path):
            # Try to get more specific error from the extraction
            from VSE_Transcrib.utils.audio import _mixdown_audio
            seq_editor = context.scene.sequence_editor
            if seq_editor:
                # Try to get more specific error
                try:
                    temp_path = os.path.join(tempfile.gettempdir(), f"vse_transcribe_debug_{os.getpid()}.wav")
                    success, error = _mixdown_audio(context.scene, context.scene.sequence_editor, temp_path, 16000, [strip])
                    if error:
                        self.report({"ERROR"}, f"Failed to extract audio from strip: {error}")
                    else:
                        self.report({"ERROR"}, "Failed to extract audio from strip (unknown error)")
                except Exception as e:
                    self.report({"ERROR"}, f"Failed to extract audio from strip: {e}")
            else:
                self.report({"ERROR"}, "Failed to extract audio from strip (no sequence editor)")
            return {"CANCELLED"}

        # Generate unique job ID
        import uuid
        job_id = str(uuid.uuid4())[:8]
        
        # Store job info for async processing
        with _transcription_lock:
            _transcription_results[job_id] = {
                "status": "started",
                "audio_path": audio_path,
                "settings": settings,
                "context": context,
                "result": None,
                "error": None,
                "start_time": time.time(),
                "transcript_duration": 0.0,
                "word_list": [],
                "progress": 0.0,
                "current_word": "",
                "last_update": time.time(),
            }

        # Mark as transcribing
        settings.is_transcribing = True
        settings.transcription_job_id = job_id
        settings.transcription_icon_index = 0  # reset animation icon
        self.report({"INFO"}, f"Starting transcription (job: {job_id})...")

        # Start background thread
        thread = threading.Thread(
            target=self._run_transcription_thread,
            args=(job_id, audio_path, settings, strip),
            daemon=True
        )
        thread.start()

        # Register timer to check progress
        def check_progress():
            import bpy
            with _transcription_lock:
                if job_id not in _transcription_results:
                    return None
                result = _transcription_results[job_id]
                if result["status"] == "finished":
                    # Process result
                    self._process_transcription_result(result, settings, context)
                    del _transcription_results[job_id]
                    settings.is_transcribing = False
                    return None  # Stop timer
                elif result["status"] == "error":
                    self.report({"ERROR"}, f"Transcription failed: {result['error']}")
                    settings.is_transcribing = False
                    del _transcription_results[job_id]
                    return None  # Stop timer
            return 0.5  # Check every 0.5 seconds

        bpy.app.timers.register(check_progress, first_interval=0.5)
        
        return {"FINISHED"}

    def _transcription_progress_callback(self, job_id: str, progress: float, current_word: str = ""):
        """Callback for transcription progress updates."""
        with _transcription_lock:
            if job_id in _transcription_results:
                _transcription_results[job_id]["progress"] = progress
                _transcription_results[job_id]["current_word"] = current_word
                _transcription_results[job_id]["last_update"] = time.time()

    def _run_transcription_thread(self, job_id: str, audio_path: str, settings, strip):
        """Background thread for transcription."""
        try:
            # Import engine and config
            from VSE_Transcrib.engines import get_engine
            from VSE_Transcrib.engines.local_whisper import LocalWhisperConfig
            from VSE_Transcrib.engines.base import EngineNotAvailableError, InvalidConfigError, TranscriptionError

            # Get engine class
            try:
                engine_cls = get_engine(settings.engine_type)
            except Exception as e:
                with _transcription_lock:
                    _transcription_results[job_id]["status"] = "error"
                    _transcription_results[job_id]["error"] = f"Engine '{settings.engine_type}' not available: {e}"
                return

            engine = engine_cls()

            # Build engine config from settings
            config = self._build_engine_config(settings)
            if config is None:
                with _transcription_lock:
                    _transcription_results[job_id]["status"] = "error"
                    _transcription_results[job_id]["error"] = "Invalid configuration"
                return

            # Run transcription with progress callback if supported
            transcript = engine.transcribe(audio_path, config, progress_callback=self._transcription_progress_callback)

            # Validate transcript
            from VSE_Transcrib.core.transcription import validate_transcript, normalize_transcript
            problems = validate_transcript(transcript)
            if problems:
                # Just log warnings, don't fail
                pass

            # Normalize
            transcript = normalize_transcript(transcript)

            # Store result
            with _transcription_lock:
                if job_id in _transcription_results:
                    _transcription_results[job_id]["status"] = "finished"
                    _transcription_results[job_id]["result"] = transcript

        except EngineNotAvailableError as e:
            with _transcription_lock:
                if job_id in _transcription_results:
                    _transcription_results[job_id]["status"] = "error"
                    _transcription_results[job_id]["error"] = f"Engine '{settings.engine_type}' not available: {e}"
            return
        except InvalidConfigError as e:
            with _transcription_lock:
                if job_id in _transcription_results:
                    _transcription_results[job_id]["status"] = "error"
                    _transcription_results[job_id]["error"] = f"Invalid configuration: {e}"
            return
        except TranscriptionError as e:
            with _transcription_lock:
                if job_id in _transcription_results:
                    _transcription_results[job_id]["status"] = "error"
                    _transcription_results[job_id]["error"] = f"Transcription failed: {e}"
            return
        except Exception as e:
            # Catch any other unexpected errors
            with _transcription_lock:
                if job_id in _transcription_results:
                    _transcription_results[job_id]["status"] = "error"
                    _transcription_results[job_id]["error"] = f"Unexpected error: {e}"
            return
        finally:
            # Cleanup temp audio file
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception:
                pass

    @classmethod
    def _process_transcription_result(cls, result, settings, context):
        """Process completed transcription result on main thread."""
        cls._report_info(context, f"[_process_transcription_result] Called with result status: {result.get('status', 'unknown')}")
        transcript = result["result"]
        if not transcript:
            cls._report_warning(context, "No transcript result received")
            return
            # Serialize and store
            transcript_json = cls._transcript_to_json(transcript)
            settings.transcript_storage = transcript_json
            cls._report_info(context, f"Transcription complete: {len(transcript.segments)} segments, {transcript.total_words} words")
            
            # Auto-generate subtitle strips
            try:
                # Prepare subtitle config from settings
                from VSE_Transcrib.core.subtitle_engine import SubtitleConfig, prepare_subtitles
                subtitle_config = SubtitleConfig(
                    max_chars_per_line=settings.subtitle.max_chars_per_line,
                    max_lines=settings.subtitle.max_lines,
                    min_duration=settings.subtitle.min_duration,
                    gap_threshold=settings.subtitle.gap_threshold,
                )
                
                # Generate subtitle blocks
                blocks = prepare_subtitles(transcript, subtitle_config)
                
                if blocks:
                    # Get or create sequence editor
                    scene = context.scene
                    if not scene.sequence_editor:
                        scene.sequence_editor_create()
                    
                    sequencer = scene.sequence_editor
                    
                    # Create strips via StripManager
                    from VSE_Transcrib.core.strip_manager import StripManager
                    manager = StripManager(scene, sequencer)
                    # Use a reasonable default channel (e.g., channel 5 for subtitles)
                    channel = 5
                    strips = manager.create_subtitle_strips(blocks, channel)
                    
                    # Store strip names for clearing later
                    settings.generated_strips.clear()
                    for strip in strips:
                        item = settings.generated_strips.add()
                        item.name = strip.name
                    
                    cls._report_info(context, f"Created {len(strips)} subtitle strips on channel {channel}")
                else:
                    cls._report_warning(context, "No subtitle blocks generated from transcript")
            except Exception as e:
                cls._report_error(context, f"Failed to generate subtitle strips: {e}")
    
    @staticmethod
    def _report_info(context, message):
        if hasattr(context, 'window_manager'):
            context.window_manager.popup_menu(lambda self, ctx: self.layout.label(text=message), title="Info", icon='INFO')
    
    @staticmethod
    def _report_warning(context, message):
        if hasattr(context, 'window_manager'):
            context.window_manager.popup_menu(lambda self, ctx: self.layout.label(text=message), title="Warning", icon='WARNING')
    
    @staticmethod
    def _report_error(context, message):
        if hasattr(context, 'window_manager'):
            context.window_manager.popup_menu(lambda self, ctx: self.layout.label(text=message), title="Error", icon='ERROR')

    @staticmethod
    def _get_active_audio_strip(context: Context):
        """Get the active sound/movie strip in the VSE."""
        if not _HAS_BPY:
            return None

        seq_editor = context.scene.sequence_editor
        if not seq_editor:
            return None

        # Try sequences_all (Blender 5.2+) fallback to sequences
        strips = getattr(seq_editor, "sequences_all", None)
        if strips is None:
            strips = getattr(seq_editor, "sequences", [])

        # Check selected strips first (SOUND and MOVIE types have audio)
        for strip in strips:
            if strip.select and strip.type in {"SOUND", "MOVIE"}:
                return strip

        # Also check active strip
        active = getattr(seq_editor, "active_strip", None)
        if active and active.type in {"SOUND", "MOVIE"}:
            return active

        return None
    
    @staticmethod
    def _get_strip_audio_path(strip, context: Context) -> str | None:
        """Get the audio file path from a strip (handles both SOUND and MOVIE types)."""
        if not _HAS_BPY:
            return None
        
        import bpy
        if strip.type == "SOUND" and strip.sound:
            filepath = bpy.path.abspath(strip.sound.filepath)
            if os.path.exists(filepath):
                return filepath
        elif strip.type == "MOVIE":
            # MOVIE strips: check elements for sound
            try:
                for element in strip.elements:
                    if element.sound:
                        filepath = bpy.path.abspath(element.sound.filepath)
                        if os.path.exists(filepath):
                            return filepath
            except Exception:
                pass
        
        return None

    def _get_audio_path(self, context: Context, settings) -> str | None:
        """Get the audio file path from strip or settings."""
        # Try selected/active sound strip first
        strip = self._get_active_audio_strip(context)
        if strip:
            audio_path = self._get_strip_audio_path(strip, context)
            if audio_path:
                return audio_path

        # Fallback to audio_source setting
        if settings.audio_source:
            return bpy.path.abspath(settings.audio_source)

        return None

    def _build_engine_config(self, settings):
        """Build engine config from settings."""
        from VSE_Transcrib.engines.local_whisper import LocalWhisperConfig
        lw = settings.local_whisper
        return LocalWhisperConfig(
            language=lw.language or None,
            model_size=lw.model_size,
            device=lw.device,
            compute_type=lw.compute_type,
            word_timestamps=lw.word_timestamps,
        )

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