"""Transcribe operator for VSE_Transcribe.

Runs transcription using the selected engine and stores the result.
"""

from __future__ import annotations

import functools
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


def _transcript_to_json(transcript) -> str:
    """Serialize Transcript to JSON."""
    data = {
        "language": transcript.language,
        "duration": transcript.duration,
        "metadata": transcript.metadata,
        "segments": [],
    }
    for seg in transcript.segments:
        data["segments"].append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
            "words": [
                {"text": w.text, "start": w.start, "end": w.end, "confidence": w.confidence}
                for w in seg.words
            ],
        })
    return json.dumps(data, ensure_ascii=False)


def _set_job(job_id: str, **fields) -> None:
    with _transcription_lock:
        if job_id in _transcription_results:
            _transcription_results[job_id].update(fields)


def _run_transcription_thread(job_id: str, audio_path: str, config) -> None:
    """Background thread: touches NO bpy data."""
    try:
        from VSE_Transcrib.engines.local_whisper import LocalWhisperEngine
        from VSE_Transcrib.engines.groq_api import GroqConfig, GroqEngine
        from VSE_Transcrib.core.transcription import validate_transcript, normalize_transcript

        def on_progress(progress: float, word: str = "") -> None:
            _set_job(job_id, progress=progress, current_word=word)

        engine = GroqEngine() if isinstance(config, GroqConfig) else LocalWhisperEngine()
        transcript = engine.transcribe(audio_path, config, progress_callback=on_progress)
        validate_transcript(transcript)  # warnings only
        transcript = normalize_transcript(transcript)
        _set_job(job_id, status="finished", result=transcript)
    except Exception as e:
        import traceback
        traceback.print_exc()
        _set_job(job_id, status="error", error=f"{type(e).__name__}: {e}")
    finally:
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass


def _tag_redraw() -> None:
    """Redraw the VSE so the progress shows without moving the mouse."""
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == "SEQUENCE_EDITOR":
                    area.tag_redraw()
    except Exception:
        pass


def _poll_job(job_id: str):
    """Main-thread timer: updates UI props and finalizes the job."""
    with _transcription_lock:
        data = _transcription_results.get(job_id)
        if data is None:
            return None
        snapshot = dict(data)

    scene = bpy.data.scenes.get(snapshot["scene_name"])
    settings = getattr(scene, "vse_transcribe", None) if scene else None
    if settings is None:
        with _transcription_lock:
            _transcription_results.pop(job_id, None)
        return None

    status = snapshot["status"]
    if status in {"started", "running"}:
        settings.is_transcribing = True
        settings.transcription_progress = snapshot["progress"]
        settings.last_word = snapshot["current_word"]
        _tag_redraw()
        return 0.5

    settings.is_transcribing = False
    with _transcription_lock:
        _transcription_results.pop(job_id, None)

    if status == "error":
        print(f"[VSE_Transcribe] Transcription failed: {snapshot['error']}")
        settings.status_text = f"Error: {snapshot['error']}"
        return None

    _finalize_transcript(scene, settings, snapshot["result"], snapshot.get("frame_offset", 0))
    _tag_redraw()
    return None


def _finalize_transcript(scene, settings, transcript, frame_offset: int = 0) -> None:
    """Store transcript and auto-create subtitle strips (main thread)."""
    if not transcript or transcript.is_empty:
        settings.status_text = "No speech detected"
        print("[VSE_Transcribe] No transcript result received")
        return

    settings.transcript_storage = _transcript_to_json(transcript)
    settings.transcription_progress = 1.0

    try:
        from VSE_Transcrib.core.subtitle_engine import SubtitleConfig, prepare_subtitles
        from VSE_Transcrib.core.strip_manager import (
            StripManager, MANAGED_KEY, _get_sequences_local,
        )

        blocks = prepare_subtitles(transcript, SubtitleConfig(
            max_chars_per_line=settings.subtitle.max_chars_per_line,
            max_lines=settings.subtitle.max_lines,
            min_duration=settings.subtitle.min_duration,
            gap_threshold=settings.subtitle.gap_threshold,
        ))
        if not blocks:
            settings.status_text = "No subtitle blocks generated"
            return

        if not scene.sequence_editor:
            scene.sequence_editor_create()

        manager = StripManager(scene, scene.sequence_editor)
        manager.clear_managed_strips()  # evita legendas duplicadas ao re-transcrever

        # Canal logo acima de TODOS os strips que não são legenda
        others = [
            s.channel for s in _get_sequences_local(scene.sequence_editor)
            if not s.get(MANAGED_KEY)
        ]
        channel = (max(others) + 1) if others else 1
        strips = manager.create_subtitle_strips(blocks, channel, frame_offset=frame_offset)

        settings.generated_strips.clear()
        for strip in strips:
            settings.generated_strips.add().name = strip.name
        settings.status_text = (
            f"Created {len(strips)} strips on channel {channel} | "
            f"language: {transcript.language} | audio: {transcript.duration:.1f}s"
        )
        print(f"[VSE_Transcribe] {settings.status_text}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        settings.status_text = f"Failed to generate subtitle strips: {e}"


class VSETRANSCRIBE_OT_transcribe(Operator):
    """Transcribe audio using the selected engine."""

    bl_idname = "vse_transcribe.transcribe"
    bl_label = "Transcribe Audio"
    bl_description = "Transcribe selected audio using the configured engine"
    bl_options = {"REGISTER"}  # no UNDO: an undo push of a big video project freezes Blender

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

        if settings.engine_type == "GROQ":
            from VSE_Transcrib.properties.settings import get_groq_api_key
            if not get_groq_api_key():
                self.report(
                    {"ERROR"},
                    "Groq API key missing: Edit > Preferences > Add-ons > VSE_Transcribe "
                    "(or set env var GROQ_API_KEY)",
                )
                return {"CANCELLED"}

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

        # Build engine config on the MAIN thread (bpy properties are not thread-safe)
        config = self._build_engine_config(settings)

        import uuid
        job_id = str(uuid.uuid4())[:8]

        with _transcription_lock:
            _transcription_results[job_id] = {
                "status": "started",
                "scene_name": context.scene.name,
                "result": None,
                "error": None,
                "start_time": time.time(),
                "progress": 0.0,
                "current_word": "",
                "frame_offset": int(strip.frame_final_start),
            }

        settings.is_transcribing = True
        settings.transcription_job_id = job_id
        settings.transcription_icon_index = 0
        settings.transcription_progress = 0.0
        self.report({"INFO"}, f"Starting transcription (job: {job_id})...")

        thread = threading.Thread(
            target=_run_transcription_thread,
            args=(job_id, audio_path, config),
            daemon=True,
        )
        thread.start()

        # Module-level timer: does NOT depend on this operator instance (freed after execute)
        bpy.app.timers.register(functools.partial(_poll_job, job_id), first_interval=0.5)
        return {"FINISHED"}

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
        strips = None
        for attr in ("strips_all", "sequences_all", "strips", "sequences"):
            strips = getattr(seq_editor, attr, None)
            if strips is not None:
                break
        if strips is None:
            strips = []

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
        """Build engine config from settings (runs on the main thread)."""
        lw = settings.local_whisper

        if settings.engine_type == "GROQ":
            from VSE_Transcrib.engines.groq_api import GroqConfig
            from VSE_Transcrib.properties.settings import get_groq_api_key
            return GroqConfig(
                language=lw.language or None,
                api_key=get_groq_api_key(),
                model=settings.groq_model,
                word_timestamps=lw.word_timestamps,
            )

        from VSE_Transcrib.engines.local_whisper import LocalWhisperConfig
        return LocalWhisperConfig(
            language=lw.language or None,
            model_size=lw.model_size,
            device=lw.device,
            compute_type=lw.compute_type,
            word_timestamps=lw.word_timestamps,
            model_dir=lw.model_dir or "",
            cpu_threads=lw.cpu_threads,
            vad_filter=lw.vad_filter,
        )

    def _transcript_to_json(self, transcript: "Transcript") -> str:
        """Serialize Transcript to JSON."""
        return _transcript_to_json(transcript)


# Registration handled by __init__.py