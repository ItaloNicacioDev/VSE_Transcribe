"""Download Whisper model operator."""

from __future__ import annotations

import json
import os
import threading
import uuid

from VSE_Transcrib.core.job_store import get_job, set_job
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


class VSETRANSCRIBE_OT_download_model(Operator):
    """Download the selected Whisper model."""

    bl_idname = "vse_transcribe.download_model"
    bl_label = "Download Model"
    bl_description = "Download the selected Whisper model for local use"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can run."""
        if not _HAS_BPY:
            return False
        settings = context.scene.vse_transcribe
        # Check if the model is already downloaded
        return not cls._is_model_downloaded(settings)

    def execute(self, context: Context) -> set:
        """Execute download (async)."""
        if not _HAS_BPY:
            self.report({"ERROR"}, "Not running inside Blender")
            return {"CANCELLED"}

        settings = context.scene.vse_transcribe
        
        # Store job info for async processing
        job_id = str(uuid.uuid4())[:8]

        set_job(
            job_id,
            status="started",
            scene_name=context.scene.name,
            error=None,
        )

        # Mark as downloading
        settings.is_transcribing = True  # reuse the flag for simplicity
        settings.transcription_job_id = job_id
        settings.transcription_icon_index = 0
        self.report({"INFO"}, f"Starting model download (job: {job_id})...")

        # Start background thread
        thread = threading.Thread(
            target=self._run_download_thread,
            args=(job_id, settings),
            daemon=True
        )
        thread.start()

        # Register timer to check progress
        def check_progress():
            job = get_job(job_id)
            if job is None:
                # Job was removed (cancelled / operator gone)
                settings.is_transcribing = False
                return None

            if job.get("status") == "error":
                settings.is_transcribing = False
                settings.transcription_job_id = ""
                self.report({"ERROR"}, f"Model download failed: {job.get('error')}")
                return None

            if self._is_model_downloaded(settings):
                settings.is_transcribing = False
                settings.transcription_job_id = ""
                self.report({"INFO"}, "Model download completed.")
                return None  # Stop timer

            return 2.0  # Check again in 2 seconds

        bpy.app.timers.register(check_progress, first_interval=2.0)
        
        return {"FINISHED"}

    def _is_model_downloaded(self, settings) -> bool:
        """Check if the model is already downloaded."""
        model_size = settings.local_whisper.model_size
        model_dir = settings.local_whisper.model_dir
        if not model_dir:
            # Default model directory
            addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_dir = os.path.join(addon_root, "models")
        # Check if the model exists in the directory
        # For faster-whisper, the model is stored in a subdirectory named after the model size
        model_path = os.path.join(model_dir, model_size)
        return os.path.exists(model_path)

    def _run_download_thread(self, job_id: int, settings):
        """Background thread for model download."""
        try:
            # Import engine and config
            from VSE_Transcrib.engines.local_whisper import LocalWhisperEngine, LocalWhisperConfig
            from VSE_Transcrib.engines.base import EngineNotAvailableError

            engine = LocalWhisperEngine()

            # Build engine config from settings (just to get the model directory)
            config = LocalWhisperConfig(
                language=settings.local_whisper.language or None,
                model_size=settings.local_whisper.model_size,
                device=settings.local_whisper.device,
                compute_type=settings.local_whisper.compute_type,
                word_timestamps=settings.local_whisper.word_timestamps,
                model_dir=settings.local_whisper.model_dir,
            )
            
            # Trigger download by loading the model (this will download if not present)
            engine._get_or_load_model(
                config.model_size,
                config.device,
                config.compute_type,
                config.model_dir,
            )

            set_job(job_id, status="done")

        except EngineNotAvailableError as e:
            set_job(job_id, status="error", error=f"Local Whisper engine not available: {e}")
        except Exception as e:
            set_job(job_id, status="error", error=f"Unexpected error: {e}")


# Registration handled by __init__.py
