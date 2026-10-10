"""VSE_Transcribe settings for Blender.

Properties stored on Scene.vse_transcribe (PointerProperty).
Lazy bpy imports for compatibility outside Blender.
"""

from __future__ import annotations

import os

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
    from bpy.types import PropertyGroup, Scene, AddonPreferences
    _HAS_BPY = True
except ImportError:
    # Outside Blender - for syntax checking only
    class PropertyGroup:
        pass
    class AddonPreferences:
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


ADDON_ID = (__package__ or "VSE_Transcrib").split(".")[0]


class VSETranscribePreferences(AddonPreferences):
    """Add-on preferences (API keys live here, NOT inside the .blend project)."""

    bl_idname = ADDON_ID

    groq_api_key: StringProperty(
        name="Groq API Key",
        description="Key from console.groq.com/keys (or set the GROQ_API_KEY environment variable)",
        default="",
        subtype="PASSWORD",
    )

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "groq_api_key")
        col.label(text="Free key: console.groq.com/keys  (or env var GROQ_API_KEY)", icon="INFO")


def get_groq_api_key() -> str:
    """API key from add-on preferences, falling back to GROQ_API_KEY."""
    key = ""
    try:
        key = bpy.context.preferences.addons[ADDON_ID].preferences.groq_api_key
    except Exception:
        pass
    return (key or os.environ.get("GROQ_API_KEY", "")).strip()


class LocalWhisperProps(PropertyGroup):
    """Settings for Local Whisper engine."""

    model_size: EnumProperty(
        name="Model Size",
        description="Whisper model size (Small=fastest, Large-v3-Turbo=most accurate)",
        items=[
            ("tiny", "Tiny", "Fastest, lowest accuracy (~75 MB)"),
            ("base", "Base", "Fast, basic accuracy (~145 MB)"),
            ("small", "Small", "Better accuracy, good speed (~244 MB)"),
            ("medium", "Medium", "High accuracy, moderate speed (~769 MB)"),
            ("large-v3-turbo", "Large-v3-Turbo", "Very accurate, optimized for speed (~1550 MB)"),
            ("large-v3", "Large-v3", "Most accurate, slowest (~3 GB)"),
        ],
        default="small",
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
        default="int8",
    )

    word_timestamps: BoolProperty(
        name="Word Timestamps",
        description="Generate word-level timestamps",
        default=False,
    )

    language: StringProperty(
        name="Language",
        description="Language code, e.g. pt, en, es (empty = auto-detect)",
        default="pt",
        maxlen=10,
    )

    model_dir: StringProperty(
        name="Model Directory",
        description="Directory to store Whisper models",
        default="",
        subtype='DIR_PATH',
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
        description="Where the transcription runs",
        items=[
            ("LOCAL", "Local Whisper", "Runs on this PC (downloads the model on first use)"),
            ("GROQ", "Groq API", "Cloud Whisper, very fast. Needs a Groq API key"),
        ],
        default="LOCAL",
    )

    groq_model: EnumProperty(
        name="Groq Model",
        description="Whisper model used on Groq",
        items=[
            ("whisper-large-v3-turbo", "Large-v3-Turbo", "Fast and cheap"),
            ("whisper-large-v3", "Large-v3", "Most accurate"),
        ],
        default="whisper-large-v3-turbo",
    )

    # Local Whisper settings
    local_whisper: PointerProperty(type=LocalWhisperProps)

    # Subtitle generation settings
    subtitle: PointerProperty(type=SubtitleProps)

    # Use VSE strip
    use_vse_strip: BoolProperty(
        name="Use VSE Strip",
        description="When enabled, transcribes the selected sound/movie strip from the VSE.",
        default=True,
    )
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

    status_text: StringProperty(
        name="Status",
        description="Current status text",
        default="",
    )

    last_word: StringProperty(
        name="Last Word",
        description="Last transcribed word",
        default="",
    )

    transcription_progress: FloatProperty(
        name="Transcription Progress",
        description="Progress of transcription (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )

    transcription_elapsed: FloatProperty(
        name="Elapsed",
        description="Elapsed time in seconds",
        default=0.0,
        min=0.0,
        soft_max=3600.0,  # 1 hour max
    )

    transcription_icon_index: IntProperty(
        name="Icon Index",
        description="Index for transcribing animation",
        default=0,
        min=0,
        max=7,
    )

    transcription_job_id: StringProperty(
        name="Transcription Job ID",
        description="ID of the current transcription job",
        default="",
        options={"HIDDEN", "SKIP_SAVE"},
    )


# Registration functions
def register_properties():
    """Register all property groups."""
    if not _HAS_BPY:
        return
    bpy.utils.register_class(VSETranscribePreferences)
    bpy.utils.register_class(LocalWhisperProps)
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
    bpy.utils.unregister_class(LocalWhisperProps)
    bpy.utils.unregister_class(VSETranscribePreferences)