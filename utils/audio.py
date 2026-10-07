"""Audio utilities for VSE_Transcribe.

Extracts audio from video/audio strips and converts to WAV for transcription.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bpy
    from bpy.types import Sequence, Scene

try:
    import bpy
    _HAS_BPY = True
except ImportError:
    _HAS_BPY = False


def _get_sequences(seq_editor):
    """Get sequences list with Blender version compatibility.
    
    Blender 5.2+ uses sequences_all, older versions use sequences.
    """
    if seq_editor is None:
        return []
    # Blender 5.2+ uses sequences_all, older versions use sequences
    return getattr(seq_editor, "sequences_all", None) or getattr(seq_editor, "sequences", [])


def extract_audio_from_strip(
    strip: "Sequence",
    scene: "Scene",
    output_path: str | None = None,
    sample_rate: int = 16000,
    channels: int = 1,
) -> str | None:
    """Extract audio from a VSE strip to a WAV file.

    Uses Blender's built-in audio mixing to render the strip's audio.
    If output_path is not provided, creates a temporary file.

    Args:
        strip: A VSE sequence strip of type 'SOUND' or 'MOVIE'.
        scene: The Blender scene.
        output_path: Optional output WAV file path.
        sample_rate: Target sample rate (default 16000 for Whisper).
        channels: Target channels (default 1/mono).

    Returns:
        Path to the extracted WAV file, or None on failure.
    """
    if not _HAS_BPY:
        return None

    if strip.type not in {"SOUND", "MOVIE"}:
        return None

    # Create temp file if not provided
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="vse_transcribe_")
        os.close(fd)

    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Store original render settings (before try for finally access)
    original_audio_codec = getattr(scene.render.ffmpeg, "audio_codec", None)
    original_audio_bitrate = getattr(scene.render.ffmpeg, "audio_bitrate", None)
    original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_sample_rate", None)
    if original_audio_samplerate is None:
        original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_samplerate", None)
    original_filepath = scene.render.filepath
    original_format = scene.render.image_settings.file_format
    original_frame_start = scene.frame_start
    original_frame_end = scene.frame_end

    # Mute all other sequences
    seq_editor = scene.sequence_editor
    if seq_editor:
        for seq in _get_sequences(seq_editor):
            seq.mute = (seq != strip)

    # Configure for WAV export
    scene.render.filepath = output_path
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "WAV"
    scene.render.ffmpeg.audio_codec = "PCM"
    scene.render.ffmpeg.audio_bitrate = 128
    # Try both attribute names for sample rate
    if hasattr(scene.render.ffmpeg, "audio_sample_rate"):
        scene.render.ffmpeg.audio_sample_rate = sample_rate
    elif hasattr(scene.render.ffmpeg, "audio_samplerate"):
        scene.render.ffmpeg.audio_samplerate = sample_rate

    # Set frame range to strip duration
    original_frame_start = scene.frame_start
    original_frame_end = scene.frame_end
    scene.frame_start = int(strip.frame_final_start)
    scene.frame_end = int(strip.frame_final_end)

    # Mute all other sequences
    seq_editor = scene.sequence_editor
    if seq_editor:
        for seq in _get_sequences(seq_editor):
            seq.mute = (seq != strip)

            # Render audio
            try:
        bpy.ops.render.render(animation=True, write_still=False)

        # Verify output
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path

    except Exception:
        pass
    finally:
        # Restore settings
        if original_audio_codec is not None:
            scene.render.ffmpeg.audio_codec = original_audio_codec
        if original_audio_bitrate is not None:
            scene.render.ffmpeg.audio_bitrate = original_audio_bitrate
        # Restore sample rate with correct attribute name
        if original_audio_samplerate is not None:
            if hasattr(scene.render.ffmpeg, "audio_sample_rate"):
                scene.render.ffmpeg.audio_sample_rate = original_audio_samplerate
            elif hasattr(scene.render.ffmpeg, "audio_samplerate"):
                scene.render.ffmpeg.audio_samplerate = original_audio_samplerate
        scene.render.filepath = original_filepath
        scene.render.image_settings.file_format = original_format
        scene.frame_start = original_frame_start
        scene.frame_end = original_frame_end

        # Unmute all sequences
        if seq_editor:
            for seq in _get_sequences(seq_editor):
                seq.mute = False

    return None


def extract_audio_from_strips(
    strips: list["Sequence"],
    scene: "Scene",
    output_path: str | None = None,
    sample_rate: int = 16000,
) -> str | None:
    """Extract combined audio from multiple strips.

    Args:
        strips: List of VSE sequence strips (SOUND or MOVIE).
        scene: The Blender scene.
        output_path: Optional output WAV file path.
        sample_rate: Target sample rate.

    Returns:
        Path to the extracted WAV file, or None on failure.
    """
    if not strips:
        return None

    # If only one strip, use single extraction
    if len(strips) == 1:
        return extract_audio_from_strip(strips[0], scene, output_path, sample_rate)

    # For multiple strips, we need to render the full mix
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="vse_transcribe_")
        os.close(fd)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Store original settings
    original_audio_codec = getattr(scene.render.ffmpeg, "audio_codec", None)
    original_audio_bitrate = getattr(scene.render.ffmpeg, "audio_bitrate", None)
    original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_sample_rate", None)
    if original_audio_samplerate is None:
        original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_samplerate", None)
    original_filepath = scene.render.filepath
    original_format = scene.render.image_settings.file_format

    seq_editor = scene.sequence_editor
    if not seq_editor:
        return None

    # Store original mute states
    original_mutes = {seq: seq.mute for seq in _get_sequences(seq_editor)}

    try:
        # Configure for WAV export
        scene.render.filepath = output_path
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "WAV"
        scene.render.ffmpeg.audio_codec = "PCM"
        scene.render.ffmpeg.audio_bitrate = 128
        # Try both attribute names for sample rate
        if hasattr(scene.render.ffmpeg, "audio_sample_rate"):
            scene.render.ffmpeg.audio_sample_rate = sample_rate
        elif hasattr(scene.render.ffmpeg, "audio_samplerate"):
            scene.render.ffmpeg.audio_samplerate = sample_rate

        # Set frame range to cover all strips
        frame_start = min(int(s.frame_final_start) for s in strips)
        frame_end = max(int(s.frame_final_end) for s in strips)
        original_frame_start = scene.frame_start
        original_frame_end = scene.frame_end
        scene.frame_start = frame_start
        scene.frame_end = frame_end

        # Mute non-target strips
        for seq in _get_sequences(seq_editor):
            seq.mute = seq not in strips

        # Render audio
        bpy.ops.render.render(animation=True, write_still=False)

        # Verify output
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path

    except Exception:
        pass
    finally:
        # Restore settings
        if original_audio_codec is not None:
            scene.render.ffmpeg.audio_codec = original_audio_codec
        if original_audio_bitrate is not None:
            scene.render.ffmpeg.audio_bitrate = original_audio_bitrate
        # Restore sample rate with correct attribute name
        if original_audio_samplerate is not None:
            if hasattr(scene.render.ffmpeg, "audio_sample_rate"):
                scene.render.ffmpeg.audio_sample_rate = original_audio_samplerate
            elif hasattr(scene.render.ffmpeg, "audio_samplerate"):
                scene.render.ffmpeg.audio_samplerate = original_audio_samplerate
        scene.render.filepath = original_filepath
        scene.render.image_settings.file_format = original_format
        scene.frame_start = original_frame_start
        scene.frame_end = original_frame_end

        # Restore mute states
        for seq, mute in original_mutes.items():
            if seq:
                seq.mute = mute

    return None


def cleanup_temp_file(filepath: str | None) -> None:
    """Safely delete a temporary file."""
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass