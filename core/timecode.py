"""Pure timecode/frame utilities for VSE_Transcribe.

No bpy, no external dependencies. All functions are pure and deterministic.
Frame conversion uses round() to align fractional seconds to the nearest
frame boundary; timecode strings use HH:MM:SS.mmm format.
"""

from __future__ import annotations


def _validate_fps(fps: float) -> None:
    """Raise ValueError if fps is not a positive, non-zero number."""
    if not isinstance(fps, (int, float)) or isinstance(fps, bool):
        raise ValueError(f"fps must be a number, got {type(fps).__name__}")
    if fps <= 0:
        raise ValueError(f"fps must be positive and non-zero, got {fps}")


def seconds_to_frames(seconds: float, fps: float) -> int:
    """Convert seconds to the nearest frame number at the given fps.

    Args:
        seconds: Time in seconds (must be >= 0).
        fps: Frames per second (must be > 0).

    Returns:
        Frame number as an integer (rounded to the nearest frame).

    Raises:
        ValueError: If fps is invalid or seconds is negative.
    """
    _validate_fps(fps)
    if seconds < 0:
        raise ValueError(f"seconds must be non-negative, got {seconds}")
    return int(round(seconds * fps))


def frames_to_seconds(frames: int, fps: float) -> float:
    """Convert a frame number to seconds at the given fps.

    Args:
        frames: Frame number (must be >= 0).
        fps: Frames per second (must be > 0).

    Returns:
        Time in seconds.

    Raises:
        ValueError: If fps is invalid or frames is negative.
    """
    _validate_fps(fps)
    if frames < 0:
        raise ValueError(f"frames must be non-negative, got {frames}")
    return frames / fps


def seconds_to_timecode(seconds: float) -> str:
    """Format seconds as a HH:MM:SS.mmm timecode string.

    The fractional part is rendered with millisecond precision.

    Args:
        seconds: Time in seconds (must be >= 0).

    Returns:
        Timecode string, e.g. "01:02:03.500".

    Raises:
        ValueError: If seconds is negative.
    """
    if seconds < 0:
        raise ValueError(f"seconds must be non-negative, got {seconds}")
    total_ms = int(round(seconds * 1000.0))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def timecode_to_seconds(timecode: str) -> float:
    """Parse a timecode string into seconds.

    Accepts "HH:MM:SS.mmm", "HH:MM:SS", "MM:SS.mmm" and "MM:SS".
    The fractional part, when present, is a decimal fraction of a second
    (".5" means half a second, not 5 milliseconds).

    Args:
        timecode: Timecode string.

    Returns:
        Time in seconds.

    Raises:
        ValueError: If the string is not a valid timecode.
    """
    if not isinstance(timecode, str):
        raise ValueError(f"timecode must be a string, got {type(timecode).__name__}")
    parts = timecode.strip().split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"invalid timecode format: {timecode!r}")
    try:
        sec = float(parts[-1])
        minute = int(parts[-2])
        hour = int(parts[0]) if len(parts) == 3 else 0
    except ValueError as exc:
        raise ValueError(f"invalid timecode format: {timecode!r}") from exc
    if minute < 0 or minute >= 60 or sec < 0 or sec >= 60 or hour < 0:
        raise ValueError(f"invalid timecode values: {timecode!r}")
    return hour * 3600.0 + minute * 60.0 + sec
