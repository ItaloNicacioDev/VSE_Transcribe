""""Cancel transcription operator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from VSE_Transcrib.core.job_store import pop_job

if TYPE_CHECKING:
    from VSE_Transcrib.models.transcript import Transcript

try:
    import bpy
    from bpy.types import Operator, Context
    _HAS_BPY = True
except ImportError:
    # Outside Blender - for syntax checking only
    class Operator:
        pass
    class Context:
        pass
    _HAS_BPY = False


class VSETRANSCRIBE_OT_cancel_transcription(Operator):
    """Cancel the ongoing transcription."""

    bl_idname = "vse_transcribe.cancel_transcription"
    bl_label = "Cancel Transcription"
    bl_description = "Cancel the current transcription job"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can run."""
        if not _HAS_BPY:
            return False
        settings = context.scene.vse_transcribe
        return settings.is_transcribing

    def execute(self, context: Context) -> set:
        """Cancel the transcription."""
        if not _HAS_BPY:
            return {"CANCELLED"}

        settings = context.scene.vse_transcribe
        job_id = settings.transcription_job_id
        
        if not job_id:
            self.report({"WARNING"}, "No active transcription job")
            settings.is_transcribing = False
            return {"FINISHED"}

        # Remove the job from the shared store so the transcription timer stops
        # updating the UI. The background thread finishes on its own and cleans
        # up the temp audio file in its finally block.
        pop_job(job_id)
        
        settings.is_transcribing = False
        settings.transcription_job_id = ""
        self.report({"INFO"}, "Transcription cancelled")
        return {"FINISHED"}


# Registration handled by __init__.py
