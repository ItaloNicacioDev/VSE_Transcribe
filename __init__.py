
bl_info = {
    "name": "VSE_Transcribe",
    "author": "Italo Nicacio",
    "description": "AI-powered transcription and subtitle generation for the Blender Video Sequence Editor.",
    "blender": (5, 2, 0),
    "version": (0, 1, 0),
    "location": "Video Sequencer > Sidebar > VSE_Transcribe",
    "category": "Sequencer",
}

import bpy


# ------------------------------------------------------------------------
# Module imports
# ------------------------------------------------------------------------

from .properties.settings import (
    VSETranscribeSettings,
)

from .operators.transcribe import (
    VSETRANSCRIBE_OT_transcribe,
)

from .operators.generate_subtitles import (
    VSETRANSCRIBE_OT_generate_subtitles,
)

from .operators.clear_subtitles import (
    VSETRANSCRIBE_OT_clear_subtitles,
)

from .operators.export_subtitles import (
    VSETRANSCRIBE_OT_export_subtitles,
)

from .panels.sidebar import (
    VSETRANSCRIBE_PT_sidebar,
)

from .ui.menus import (
    VSETRANSCRIBE_MT_main_menu,
)


# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------

CLASSES = (
    VSETranscribeSettings,

    VSETRANSCRIBE_OT_transcribe,
    VSETRANSCRIBE_OT_generate_subtitles,
    VSETRANSCRIBE_OT_clear_subtitles,
    VSETRANSCRIBE_OT_export_subtitles,

    VSETRANSCRIBE_PT_sidebar,

    VSETRANSCRIBE_MT_main_menu,
)


def register():
    """Register all VSE_Transcribe classes and properties."""

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.vse_transcribe = bpy.props.PointerProperty(
        type=VSETranscribeSettings
    )

    print("[VSE_Transcribe] Addon registered successfully.")


def unregister():
    """Unregister all VSE_Transcribe classes and properties."""

    if hasattr(bpy.types.Scene, "vse_transcribe"):
        del bpy.types.Scene.vse_transcribe

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

    print("[VSE_Transcribe] Addon unregistered successfully.")


# ------------------------------------------------------------------------
# Development entry point
# ------------------------------------------------------------------------

if __name__ == "__main__":
    register()

