"""Base engine interface for VSE_Transcribe.

All transcription engines (local, API) must implement this interface.
Pure Python, no bpy dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type

try:
    from ..models.transcript import Transcript
except ImportError:
    # Allow running tests directly from engines/ directory
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from models.transcript import Transcript


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


class TranscriptionError(RuntimeError):
    """Raised when transcription fails."""


class InvalidConfigError(ValueError):
    """Raised when engine configuration is invalid."""


# Registry for engine implementations
_engine_registry: Dict[str, Type["TranscriptionEngine"]] = {}


def register_engine(name: str, cls: Type["TranscriptionEngine"]) -> None:
    """Register a transcription engine implementation.

    Args:
        name: Unique engine identifier (e.g., "whisper", "openai").
        cls: Engine class inheriting from TranscriptionEngine.

    Raises:
        ValueError: If name is already registered.
    """
    if name in _engine_registry:
        raise ValueError(f"Engine '{name}' already registered")
    _engine_registry[name] = cls


def get_engine(name: str) -> Type["TranscriptionEngine"]:
    """Get a registered engine class by name.

    Args:
        name: Engine identifier.

    Returns:
        The engine class.

    Raises:
        EngineNotAvailableError: If engine is not registered.
    """
    if name not in _engine_registry:
        raise EngineNotAvailableError(f"Engine '{name}' not registered")
    return _engine_registry[name]


def list_engines() -> Dict[str, Type["TranscriptionEngine"]]:
    """Return all registered engines.

    Returns:
        Dict mapping engine names to engine classes.
    """
    return dict(_engine_registry)


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
            InvalidConfigError: If config is invalid.
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
            TranscriptionError: If transcription fails.
        """
        pass

    def _check_dependencies(self) -> bool:
        """Check if engine dependencies are available.

        Override in subclasses to check for specific libraries.

        Returns:
            True if dependencies are available, False otherwise.
        """
        return True