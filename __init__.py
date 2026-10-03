bl_info = {
    "name": "VSE_Transcribe",
    "author": "ItaloNicacioDev",
    "description": "AI-powered transcription and subtitle generation for Blender VSE",
    "blender": (5, 2, 0),
    "version": (0, 1, 0),
    "location": "Video Sequencer > Sidebar > VSE_Transcribe",
    "category": "Sequencer",
}

import bpy

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

from .panels.sidebar import (
    VSETRANSCRIBE_PT_sidebar,
)


CLASSES = (
    VSETranscribeSettings,

    VSETRANSCRIBE_OT_transcribe,
    VSETRANSCRIBE_OT_generate_subtitles,
    VSETRANSCRIBE_OT_clear_subtitles,

    VSETRANSCRIBE_PT_sidebar,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.vse_transcribe = bpy.props.PointerProperty(
        type=VSETranscribeSettings
    )

    print("[VSE_Transcribe] Registered")


def unregister():
    del bpy.types.Scene.vse_transcribe

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

    print("[VSE_Transcribe] Unregistered")


if __name__ == "__main__":
    register()