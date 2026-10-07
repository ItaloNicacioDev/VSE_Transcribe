"""Properties package for VSE_Transcribe.

Exports property classes and registration functions.
"""

from .settings import (
    LocalWhisperProps,
    ExternalAPIProps,
    SubtitleProps,
    GeneratedStripName,
    VSETranscribeSettings,
    register_properties,
    unregister_properties,
)

__all__ = [
    "LocalWhisperProps",
    "ExternalAPIProps",
    "SubtitleProps",
    "GeneratedStripName",
    "VSETranscribeSettings",
    "register_properties",
    "unregister_properties",
]