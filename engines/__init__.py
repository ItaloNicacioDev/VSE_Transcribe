"""Engines package for VSE_Transcribe.

Exports the base engine interface, exceptions, and registry.
Auto-registers built-in engines when imported.
"""

from .base import (
    EngineConfig,
    EngineNotAvailableError,
    InvalidConfigError,
    TranscriptionEngine,
    TranscriptionError,
    get_engine,
    list_engines,
    register_engine,
)

# Auto-register built-in engines
try:
    from . import local_whisper  # noqa: F401
except ImportError:
    pass

try:
    from . import external_api  # noqa: F401
except ImportError:
    pass

__all__ = [
    "EngineConfig",
    "TranscriptionEngine",
    "TranscriptionError",
    "EngineNotAvailableError",
    "InvalidConfigError",
    "register_engine",
    "get_engine",
    "list_engines",
]
