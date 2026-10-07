"""Path utilities for VSE_Transcribe.

Handles addon paths, user preferences paths, and temp file management.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bpy


def get_addon_directory() -> Path:
    """Get the addon installation directory."""
    # This file is at: <addon>/utils/paths.py
    return Path(__file__).parent.parent


def get_addon_name() -> str:
    """Get the addon name from directory."""
    return get_addon_directory().name


def get_user_addon_path() -> Path | None:
    """Get the user-specific addon path (config/scripts/addons)."""
    try:
        import bpy
        return Path(bpy.utils.user_resource("SCRIPTS", "addons"))
    except Exception:
        return None


def get_temp_directory() -> Path:
    """Get the system temp directory for VSE_Transcribe."""
    return Path(tempfile.gettempdir()) / "vse_transcribe"


def ensure_temp_directory() -> Path:
    """Ensure temp directory exists and return it."""
    temp_dir = get_temp_directory()
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_temp_audio_path(prefix: str = "vse_transcribe_", suffix: str = ".wav") -> Path:
    """Get a temporary audio file path."""
    temp_dir = ensure_temp_directory()
    return temp_dir / f"{prefix}{os.urandom(8).hex()}{suffix}"


def get_temp_export_path(
    format: str = "srt",
    prefix: str = "subtitles_",
) -> Path:
    """Get a temporary export file path."""
    temp_dir = ensure_temp_directory()
    return temp_dir / f"{prefix}{os.urandom(8).hex()}.{format}"


def resolve_relative_path(filepath: str, relative_to: str | Path | None = None) -> Path:
    """Resolve a relative path to absolute.

    Args:
        filepath: The path to resolve (may be relative or absolute).
        relative_to: Base directory for relative paths (default: addon directory).

    Returns:
        Absolute Path.
    """
    path = Path(filepath)
    if path.is_absolute():
        return path

    if relative_to is None:
        relative_to = get_addon_directory()

    return (Path(relative_to) / path).resolve()


def is_audio_file(filepath: str | Path) -> bool:
    """Check if file has an audio extension."""
    audio_extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma"}
    return Path(filepath).suffix.lower() in audio_extensions


def is_video_file(filepath: str | Path) -> bool:
    """Check if file has a video extension."""
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
    return Path(filepath).suffix.lower() in video_extensions


def is_media_file(filepath: str | Path) -> bool:
    """Check if file is audio or video."""
    return is_audio_file(filepath) or is_video_file(filepath)


# Import os at module level for get_temp_audio_path
import os