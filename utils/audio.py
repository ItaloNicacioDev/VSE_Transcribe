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


def _mixdown_audio(
    scene: "Scene",
    seq_editor,
    output_path: str,
    sample_rate: int,
    strips: list["Sequence"],
) -> tuple[bool, str]:
    """Extract audio using Blender's sound.mixdown (much faster than render).
    
    Returns (success: bool, error_message: str)
    """
    try:
        # Validate strips have audio
        audio_strips = [s for s in strips if s.type in {"SOUND", "MOVIE"}]
        if not audio_strips:
            return False, "No audio strips found (need SOUND or MOVIE type)"
        
        # Check if strips have audio data
        for s in audio_strips:
            if s.type == "MOVIE":
                # Check if movie strip has audio - we'll try anyway
                pass
        
        # Determine frame range
        frame_start = min(int(s.frame_final_start) for s in strips)
        frame_end = max(int(s.frame_final_end) for s in strips)
        
        if frame_start >= frame_end:
            return False, f"Invalid frame range: {frame_start} >= {frame_end}"
        
        # Mute non-target strips
        original_mutes = {}
        for seq in _get_sequences(seq_editor):
            original_mutes[seq] = seq.mute
            seq.mute = seq not in strips
        
        try:
            # Configure render settings for audio mixdown
            original_filepath = scene.render.filepath
            original_format = scene.render.image_settings.file_format
            original_ffmpeg_format = getattr(scene.render.ffmpeg, "format", None)
            original_audio_codec = getattr(scene.render.ffmpeg, "audio_codec", None)
            original_audio_bitrate = getattr(scene.render.ffmpeg, "audio_bitrate", None)
            original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_sample_rate", None)
            if original_audio_samplerate is None:
                original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_samplerate", None)
            
            # Configure for audio mixdown (MKV container with PCM audio)
            scene.render.filepath = output_path
            scene.render.image_settings.file_format = "FFMPEG"
            scene.render.ffmpeg.format = "MKV"
            scene.render.ffmpeg.audio_codec = "PCM"
            scene.render.ffmpeg.audio_bitrate = 128
            
            # Sample rate
            if hasattr(scene.render.ffmpeg, "audio_sample_rate"):
                scene.render.ffmpeg.audio_sample_rate = sample_rate
            elif hasattr(scene.render.ffmpeg, "audio_samplerate"):
                scene.render.ffmpeg.audio_samplerate = sample_rate
            
            # Frame range
            original_frame_start = scene.frame_start
            original_frame_end = scene.frame_end
            scene.frame_start = frame_start
            scene.frame_end = frame_end
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Use sound.mixdown - much faster than render.render
            try:
                bpy.ops.sound.mixdown(
                    filepath=output_path,
                    container='MKV',
                    codec='PCM',
                    sample_rate=sample_rate,
                    channels=1,  # mono
                    mix_buffer_size=1024,
                    start_frame=frame_start,
                    end_frame=frame_end,
                )
            except Exception as e:
                return False, f"sound.mixdown failed: {e}"
            
            # Verify output
            if not os.path.exists(output_path):
                return False, "Output file was not created"
            
            if os.path.getsize(output_path) == 0:
                return False, "Output file is empty (0 bytes)"
            
            return True, "Success"
            
        finally:
            # Restore strip mute states
            for seq, mute in original_mutes.items():
                if seq:
                    seq.mute = mute
                    
    except Exception as e:
        return False, f"Unexpected error in _mixdown_audio: {e}"
    
    return False, "Unknown error"


def extract_audio_from_strip(
    strip: "Sequence",
    scene: "Scene",
    output_path: str | None = None,
    sample_rate: int = 16000,
    channels: int = 1,
) -> str | None:
    """Extract audio from a VSE strip using sound.mixdown (fast).
    
    Uses Blender's sound.mixdown for fast audio extraction.
    If output_path is not provided, creates a temporary file.

    Args:
        strip: A VSE sequence strip of type 'SOUND' or 'MOVIE'.
        scene: The Blender scene.
        output_path: Optional output WAV file path.
        sample_rate: Target sample rate (default 16000 for Whisper).
        channels: Target channels (default 1/mono).

    Returns:
        Path to the extracted audio file, or None on failure.
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

    seq_editor = scene.sequence_editor
    if not seq_editor:
        return None

    # Mute all other strips except the target
    original_mutes = {}
    for seq in _get_sequences(seq_editor):
        original_mutes[seq] = seq.mute
        seq.mute = (seq != strip)

    try:
        # Use sound.mixdown for fast audio extraction
        success, error = _mixdown_audio(scene, scene.sequence_editor, output_path, sample_rate, [strip])
        
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        
        # Log the error for debugging
        if error:
            print(f"[VSE_Transcribe] Audio extraction failed: {error}")
        
        return None
        
    finally:
        # Restore mute states
        for seq, mute in original_mutes.items():
            if seq:
                seq.mute = mute

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
        Path to the extracted audio file, or None on failure.
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

    seq_editor = scene.sequence_editor
    if not seq_editor:
        return None

    # Store original mute states
    original_mutes = {seq: seq.mute for seq in _get_sequences(seq_editor)}

    # Mute non-target strips
    for seq in _get_sequences(seq_editor):
        seq.mute = seq not in strips

    try:
        # Use sound.mixdown for fast audio extraction
        success, error = _mixdown_audio(scene, scene.sequence_editor, output_path, sample_rate, strips)
        
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        
        if error:
            print(f"[VSE_Transcribe] Audio extraction failed: {error}")
        
        return None
        
    finally:
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
