"""VSE_Transcribe settings for Blender.

Properties stored on Scene.vse_transcribe (PointerProperty).
Lazy bpy imports for compatibility outside Blender.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bpy
    from bpy.props import (
        EnumProperty,
        StringProperty,
        BoolProperty,
        IntProperty,
        FloatProperty,
        PointerProperty,
        CollectionProperty,
    )
    from bpy.types import PropertyGroup, Scene

try:
    import bpy
    from bpy.props import (
        EnumProperty,
        StringProperty,
        BoolProperty,
        IntProperty,
        FloatProperty,
        PointerProperty,
        CollectionProperty,
    )
    from bpy.types import PropertyGroup, Scene
    _HAS_BPY = True
except ImportError:
    # Outside Blender - for syntax checking only
    class PropertyGroup:
        pass
    class Scene:
        pass
    def EnumProperty(**kwargs):
        return None
    def StringProperty(**kwargs):
        return None
    def BoolProperty(**kwargs):
        return None
    def IntProperty(**kwargs):
        return None
    def FloatProperty(**kwargs):
        return None
    def PointerProperty(**kwargs):
        return None
    def CollectionProperty(**kwargs):
        return None
    _HAS_BPY = False


class LocalWhisperProps(PropertyGroup):
    """Settings for Local Whisper engine."""

    model_size: EnumProperty(
        name="Model Size",
        description="Whisper model size (larger = more accurate, slower)",
        items=[
            ("tiny", "Tiny", "Fastest, least accurate"),
            ("base", "Base", "Good balance"),
            ("small", "Small", "Better accuracy"),
            ("medium", "Medium", "High accuracy"),
            ("large", "Large", "Highest accuracy (slow)"),
            ("large-v2", "Large v2", "Improved large model"),
            ("large-v3", "Large v3", "Latest large model"),
        ],
        default="base",
    )

    device: EnumProperty(
        name="Device",
        description="Compute device",
        items=[
            ("auto", "Auto", "CUDA if available, else CPU"),
            ("cpu", "CPU", "Run on CPU"),
            ("cuda", "CUDA", "Run on NVIDIA GPU"),
        ],
        default="auto",
    )

    compute_type: EnumProperty(
        name="Compute Type",
        description="Precision for faster-whisper",
        items=[
            ("int8", "INT8", "Fastest, lowest memory (CPU/GPU)"),
            ("int8_float16", "INT8 Float16", "Balanced (GPU)"),
            ("float16", "Float16", "Standard GPU precision"),
            ("float32", "Float32", "Highest precision"),
        ],
        default="float16",
    )

    word_timestamps: BoolProperty(
        name="Word Timestamps",
        description="Generate word-level timestamps",
        default=False,
    )

    language: StringProperty(
        name="Language",
        description="Language code (empty = auto-detect)",
        default="",
        maxlen=10,
    )


class ExternalAPIProps(PropertyGroup):
    """Settings for External API engine."""

    endpoint: StringProperty(
        name="API Endpoint",
        description="Transcription API endpoint URL",
        default="https://api.openai.com/v1/audio/transcriptions",
        # subtype="URL" not valid in Blender 5.2; using NONE
    )

    api_key: StringProperty(
        name="API Key",
        description="API authentication key",
        default="",
        subtype="PASSWORD",
    )

    model: StringProperty(
        name="Model",
        description="Model identifier for the API",
        default="whisper-1",
    )

    timeout: FloatProperty(
        name="Timeout (s)",
        description="Request timeout in seconds",
        default=30.0,
        min=1.0,
        max=300.0,
    )

    language: StringProperty(
        name="Language",
        description="Language code (empty = auto-detect)",
        default="",
        maxlen=10,
    )


class SubtitleProps(PropertyGroup):
    """Settings for subtitle generation."""

    max_chars_per_line: IntProperty(
        name="Max Characters/Line",
        description="Maximum characters per subtitle line",
        default=42,
        min=10,
        max=100,
    )

    max_lines: IntProperty(
        name="Max Lines",
        description="Maximum lines per subtitle",
        default=2,
        min=1,
        max=5,
    )

    min_duration: FloatProperty(
        name="Min Duration (s)",
        description="Minimum subtitle duration",
        default=1.0,
        min=0.1,
        max=10.0,
    )

    gap_threshold: FloatProperty(
        name="Gap Threshold (s)",
        description="Merge segments with gaps smaller than this",
        default=0.5,
        min=0.0,
        max=5.0,
    )


class GeneratedStripName(PropertyGroup):
    """Stores a generated strip name for tracking."""

    name: StringProperty()


class VSETranscribeSettings(PropertyGroup):
    """Main settings for VSE_Transcribe addon."""

    # Engine selection
    engine_type: EnumProperty(
        name="Engine",
        description="Transcription engine to use",
        items=[
            ("local_whisper", "Local Whisper", "Run Whisper locally (faster-whisper / whisper)"),
            ("external_api", "External API", "Use cloud transcription API (OpenAI-compatible)"),
        ],
        default="local_whisper",
    )

    # Engine-specific settings (nested PropertyGroups)
    local_whisper: PointerProperty(type=LocalWhisperProps)
    external_api: PointerProperty(type=ExternalAPIProps)

    # Subtitle generation settings
    subtitle: PointerProperty(type=SubtitleProps)

    # Audio source
    audio_source: StringProperty(
        name="Audio Source",
        description="Path to audio file or name of sound strip",
        default="",
        subtype="FILE_PATH",
    )

    # Transcript storage (JSON serialized)
    transcript_storage: StringProperty(
        name="Transcript Storage",
        description="Serialized transcript data (JSON)",
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    # Track generated strips for clearing
    generated_strips: CollectionProperty(type=GeneratedStripName)

    # UI state
    show_advanced: BoolProperty(
        name="Advanced Settings",
        description="Show advanced engine settings",
        default=False,
    )

    is_transcribing: BoolProperty(
        name="Is Transcribing",
        description="Whether transcription is in progress",
        default=False,
        options={"HIDDEN", "SKIP_SAVE"},
    )


# Registration functions
def register_properties():
    """Register all property groups."""
    if not _HAS_BPY:
        return
    bpy.utils.register_class(LocalWhisperProps)
    bpy.utils.register_class(ExternalAPIProps)
    bpy.utils.register_class(SubtitleProps)
    bpy.utils.register_class(GeneratedStripName)
    bpy.utils.register_class(VSETranscribeSettings)

    Scene.vse_transcribe = PointerProperty(type=VSETranscribeSettings)


def unregister_properties():
    """Unregister all property groups."""
    if not _HAS_BPY:
        return
    if hasattr(Scene, "vse_transcribe"):
        del Scene.vse_transcribe

    bpy.utils.unregister_class(VSETranscribeSettings)
    bpy.utils.unregister_class(GeneratedStripName)
    bpy.utils.unregister_class(SubtitleProps)
    bpy.utils.unregister_class(ExternalAPIProps)
    bpy.utils.unregister_class(LocalWhisperProps)