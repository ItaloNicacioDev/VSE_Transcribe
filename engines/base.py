"""Base engine interface for VSE_Transcribe.

All transcription engines (local, API) must implement this interface.
Pure Python, no bpy dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..models.transcript import Transcript


@dataclass
class EngineConfig:
    """Base configuration for transcription engines."""

    language: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


class EngineNotAvailableError(RuntimeError):
    """Raised when a required engine dependency is not installed."""


class TranscriptionEngine(ABC):
    """Abstract base class for transcription engines.

    Implementations must provide:
    - _validate_config(): Validate engine-specific config
    - transcribe(): Run transcription and return a Transcript
    """

    name: str = "base"
    """Human-readable engine identifier."""

    @abstractmethod
    def _validate_config(self, config: EngineConfig) -> None:
        """Validate engine-specific configuration.

        Args:
            config: Engine configuration to validate.

        Raises:
            ValueError: If config is invalid.
        """
        pass

    @abstractmethod
    def transcribe(self, audio_path: str, config: EngineConfig) -> Transcript:
        """Transcribe an audio file.

        Args:
            audio_path: Path to the audio file to transcribe.
            config: Engine configuration.

        Returns:
            Transcript: The transcription result.

        Raises:
            EngineNotAvailableError: If the engine's dependencies are not available.
            RuntimeError: If transcription fails.
        """
        pass

    def _check_dependencies(self) -> bool:
        """Check if engine dependencies are available.

        Override in subclasses to check for specific libraries.

        Returns:
            True if dependencies are available, False otherwise.
        """
        return True