"""VSE_Transcribe - Blender VSE Transcription Addon."""

from .engines import (
    EngineConfig,
    EngineNotAvailableError,
    TranscriptionEngine,
    LocalWhisperConfig,
    LocalWhisperEngine,
    ExternalAPIConfig,
    ExternalAPIEngine,
)
from .models.transcript import Transcript, TranscriptSegment, TranscriptWord

__version__ = "0.1.0"