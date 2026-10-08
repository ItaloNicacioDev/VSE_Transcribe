""""Audio file browser operator."""

from __future__ import annotations

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


class VSETRANSCRIBE_OT_browse_audio(Operator):
    """Open a file browser to select an audio file."""

    bl_idname = "vse_transcribe.browse_audio"
    bl_label = "Browse Audio"
    bl_description = "Select an audio file for transcription"
    bl_options = {"REGISTER"}

    filepath: StringProperty(
        name="File Path",
        description="Audio file path",
        default="",
        subtype="FILE_PATH",
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can run."""
        return _HAS_BPY

    def execute(self, context: Context) -> set:
        """Set the selected audio file in settings."""
        if not _HAS_BPY:
            return {"CANCELLED"}

        settings = context.scene.vse_transcribe
        settings.audio_source = self.filepath
        self.report({"INFO"}, f"Selected: {os.path.basename(self.filepath)}")
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# Registration handled by __init__.py
