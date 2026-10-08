"""VSE_Transcribe - Blender VSE Transcription Addon.

AI-powered transcription and subtitle generation for the Blender Video Sequence Editor.
"""

from __future__ import annotations

try:
    import bpy
    _HAS_BPY = True
except ImportError:
    _HAS_BPY = False

# Import all modules to register their classes
from . import properties
from . import operators
from . import panels
from . import engines
from . import core
from . import models
from . import utils

# Re-export key types for external access
from .engines.base import (
    EngineConfig,
    EngineNotAvailableError,
    TranscriptionEngine,
    TranscriptionError,
    InvalidConfigError,
)
from .models.transcript import Transcript, TranscriptSegment, TranscriptWord

# -----------------------------------------------------------------------------
# bl_info - REQUIRED for Blender addon recognition
# -----------------------------------------------------------------------------

bl_info = {
    "name": "VSE_Transcribe",
    "author": "Italo Nicacio",
    "description": "AI-powered transcription and subtitle generation for the Blender Video Sequence Editor.",
    "blender": (5, 2, 0),
    "version": (0, 1, 11),
    "location": "Video Sequencer > Sidebar > VSE_Transcribe",
    "category": "Sequencer",
    "wiki_url": "https://github.com/ItaloNicacioDev/VSE_Transcribe",
    "tracker_url": "https://github.com/ItaloNicacioDev/VSE_Transcribe/issues",
    "support": "COMMUNITY",
}

__version__ = "0.1.11"


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

CLASSES = (
    # Operators
    operators.VSETRANSCRIBE_OT_transcribe,
    operators.VSETRANSCRIBE_OT_generate_subtitles,
    operators.VSETRANSCRIBE_OT_clear_subtitles,
    operators.VSETRANSCRIBE_OT_export_subtitles,

    # Panels
    panels.VSETRANSCRIBE_PT_sidebar,
)


def register() -> None:
    """Register all VSE_Transcribe classes and properties."""
    if not _HAS_BPY:
        raise RuntimeError("Cannot register: not running inside Blender")

    # Register properties first (operators/panels depend on them)
    properties.register_properties()

    # Register all other classes
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    # Register menus
    from . import ui
    ui.register_menus()

    print("[VSE_Transcribe] Addon registered successfully.")


def unregister() -> None:
    """Unregister all VSE_Transcribe classes and properties."""
    if not _HAS_BPY:
        return

    # Unregister menus first
    try:
        from . import ui
        ui.unregister_menus()
    except Exception:
        pass

    # Unregister classes in reverse order
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

    # Unregister properties
    properties.unregister_properties()

    print("[VSE_Transcribe] Addon unregistered successfully.")


# -----------------------------------------------------------------------------
# Development entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    register()
