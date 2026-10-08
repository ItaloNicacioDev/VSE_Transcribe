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


def _validate_strip_has_audio(strip: "Sequence") -> tuple[bool, str]:
    """Validate that a strip has audio data available."""
    if strip.type == "SOUND":
        if not strip.sound:
            return False, f"SOUND strip '{strip.name}' has no sound data"
        if not strip.sound.filepath:
            return False, f"SOUND strip '{strip.name}' has no filepath"
        # Check if file exists
        filepath = bpy.path.abspath(strip.sound.filepath)
        if not os.path.exists(filepath):
            return False, f"SOUND strip '{strip.name}' file not found: {filepath}"
        return True, ""
    elif strip.type == "MOVIE":
        # Check if movie strip has audio elements
        try:
            has_audio = False
            for element in strip.elements:
                if element.sound:
                    has_audio = True
                    break
            if not has_audio:
                return False, f"MOVIE strip '{strip.name}' has no audio track"
        except Exception:
            # If we can't check, we'll try anyway but warn
            pass
        return True, ""
    return False, f"Strip '{strip.name}' type '{strip.type}' not supported for audio extraction"


def _get_ffmpeg_container_codec():
    """Get the correct FFmpeg container/codec for current Blender version.
    
    Blender 5.2+: container='MKV', audio_codec='PCM'
    Older: container='MKV', audio_codec='PCM'
    Note: 'MATROSKA' is NOT a valid enum value in Blender - use 'MKV'
    """
    # Both old and new Blender versions use 'MKV' for Matroska container
    # 'MATROSKA' was never a valid enum value in bpy
    # Try to detect if MKV is available, fallback to MPEG4
    return "MKV", "PCM"


def _test_ffmpeg_format(scene, container: str) -> bool:
    """Test if a container format is valid in current Blender version."""
    try:
        original = scene.render.ffmpeg.format
        scene.render.ffmpeg.format = container
        scene.render.ffmpeg.format = original
        return True
    except Exception:
        return False


def _get_available_ffmpeg_format(scene) -> str:
    """Get an available FFmpeg container format."""
    # Test formats in order of preference
    for fmt in ("MKV", "MPEG4", "AVI", "QUICKTIME", "WEBM"):
        if _test_ffmpeg_format(scene, fmt):
            return fmt
    return "MKV"  # Default fallback


def _get_available_audio_codec(scene, container: str) -> str:
    """Get an available audio codec for the given container."""
    # Test codecs in order of preference for lossless PCM
    for codec in ("PCM", "AAC", "MP3", "VORBIS", "FLAC"):
        try:
            original_format = scene.render.ffmpeg.format
            original_codec = scene.render.ffmpeg.audio_codec
            scene.render.ffmpeg.format = container
            scene.render.ffmpeg.audio_codec = codec
            scene.render.ffmpeg.format = original_format
            scene.render.ffmpeg.audio_codec = original_codec
            return codec
        except Exception:
            continue
    return "PCM"  # Default fallback


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
        
        # Validate each strip has audio data
        for s in audio_strips:
            valid, msg = _validate_strip_has_audio(s)
            if not valid:
                return False, msg
        
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
            # Get available container/codec for this Blender version
            container = _get_available_ffmpeg_format(scene)
            audio_codec = _get_available_audio_codec(scene, container)
            
            print(f"[VSE_Transcribe] Using container={container}, audio_codec={audio_codec}")
            
            # Configure render settings for audio mixdown
            original_filepath = scene.render.filepath
            original_format = scene.render.image_settings.file_format
            original_ffmpeg_format = getattr(scene.render.ffmpeg, "format", None)
            original_audio_codec = getattr(scene.render.ffmpeg, "audio_codec", None)
            original_audio_bitrate = getattr(scene.render.ffmpeg, "audio_bitrate", None)
            original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_sample_rate", None)
            if original_audio_samplerate is None:
                original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_samplerate", None)
            
            # Configure for audio mixdown
            scene.render.filepath = output_path
            scene.render.image_settings.file_format = "FFMPEG"
            scene.render.ffmpeg.format = container
            scene.render.ffmpeg.audio_codec = audio_codec
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
            # Note: Don't pass container/codec to mixdown - let it use scene render settings
            try:
                bpy.ops.sound.mixdown(
                    filepath=output_path,
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


def _render_audio_fallback(
    scene: "Scene",
    seq_editor,
    output_path: str,
    sample_rate: int,
    strips: list["Sequence"],
) -> tuple[bool, str]:
    """Fallback audio extraction using render.render(animation=True).
    
    Configures for audio-only output. Returns (success: bool, error_message: str)
    """
    try:
        # Mute non-target strips
        original_mutes = {}
        for seq in _get_sequences(seq_editor):
            original_mutes[seq] = seq.mute
            seq.mute = seq not in strips
        
        try:
            # Determine frame range
            frame_start = min(int(s.frame_final_start) for s in strips)
            frame_end = max(int(s.frame_final_end) for s in strips)
            
            if frame_start >= frame_end:
                return False, f"Invalid frame range: {frame_start} >= {frame_end}"
            
            # Get available container/codec
            container = _get_available_ffmpeg_format(scene)
            audio_codec = _get_available_audio_codec(scene, container)
            
            print(f"[VSE_Transcribe] Fallback: Using container={container}, audio_codec={audio_codec}")
            
            # Configure render settings
            original_filepath = scene.render.filepath
            original_format = scene.render.image_settings.file_format
            original_ffmpeg_format = getattr(scene.render.ffmpeg, "format", None)
            original_audio_codec = getattr(scene.render.ffmpeg, "audio_codec", None)
            original_audio_bitrate = getattr(scene.render.ffmpeg, "audio_bitrate", None)
            original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_sample_rate", None)
            if original_audio_samplerate is None:
                original_audio_samplerate = getattr(scene.render.ffmpeg, "audio_samplerate", None)
            
            original_frame_start = scene.frame_start
            original_frame_end = scene.frame_end
            
            # Configure for audio-only render
            scene.render.filepath = output_path
            scene.render.image_settings.file_format = "FFMPEG"
            scene.render.ffmpeg.format = container
            scene.render.ffmpeg.audio_codec = audio_codec
            scene.render.ffmpeg.audio_bitrate = 128
            
            if hasattr(scene.render.ffmpeg, "audio_sample_rate"):
                scene.render.ffmpeg.audio_sample_rate = sample_rate
            elif hasattr(scene.render.ffmpeg, "audio_samplerate"):
                scene.render.ffmpeg.audio_samplerate = sample_rate
            
            # Disable video rendering - only audio
            scene.render.use_file_extension = False
            scene.render.film_transparent = True
            scene.render.resolution_x = 16  # Minimal
            scene.render.resolution_y = 16  # Minimal
            scene.render.resolution_percentage = 100
            
            scene.frame_start = frame_start
            scene.frame_end = frame_end
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Render animation (audio only since no video strips selected/muted)
            bpy.ops.render.render(animation=True, write_still=False)
            
            # Verify output
            if not os.path.exists(output_path):
                return False, "Output file was not created by render"
            
            if os.path.getsize(output_path) == 0:
                return False, "Output file is empty (0 bytes)"
            
            return True, "Success (fallback render)"
            
        finally:
            # Restore strip mute states
            for seq, mute in original_mutes.items():
                if seq:
                    seq.mute = mute
                   
    except Exception as e:
        return False, f"Render fallback failed: {e}"
    
    return False, "Unknown error in render fallback"


def extract_audio_from_strip(
    strip: "Sequence",
    scene: "Scene",
    output_path: str | None = None,
    sample_rate: int = 16000,
    channels: int = 1,
) -> str | None:
    """Extract audio from a VSE strip using sound.mixdown (fast) with render fallback.
    
    Uses Blender's sound.mixdown for fast audio extraction.
    Falls back to render.render(animation=True) if mixdown fails.
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
        # Try sound.mixdown first (fast)
        print(f"[VSE_Transcribe] Attempting sound.mixdown for strip '{strip.name}'...")
        success, error = _mixdown_audio(scene, scene.sequence_editor, output_path, sample_rate, [strip])
        
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[VSE_Transcribe] sound.mixdown succeeded: {output_path}")
            return output_path
        
        # Log the error
        print(f"[VSE_Transcribe] sound.mixdown failed: {error}. Trying render fallback...")
        
        # Try render fallback
        success, error = _render_audio_fallback(scene, scene.sequence_editor, output_path, sample_rate, [strip])
        
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[VSE_Transcribe] Render fallback succeeded: {output_path}")
            return output_path
        
        print(f"[VSE_Transcribe] All extraction methods failed: {error}")
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

    os.makedards(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    seq_editor = scene.sequence_editor
    if not seq_editor:
        return None

    # Store original mute states
    original_mutes = {seq: seq.mute for seq in _get_sequences(seq_editor)}

    # Mute non-target strips
    for seq in _get_sequences(seq_editor):
        seq.mute = seq not in strips

    try:
        # Try sound.mixdown first (fast)
        print(f"[VSE_Transcribe] Attempting sound.mixdown for {len(strips)} strips...")
        success, error = _mixdown_audio(scene, scene.sequence_editor, output_path, sample_rate, strips)
        
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[VSE_Transcribe] sound.mixdown succeeded: {output_path}")
            return output_path
        
        # Log the error
        print(f"[VSE_Transcribe] sound.mixdown failed: {error}. Trying render fallback...")
        
        # Try render fallback
        success, error = _render_audio_fallback(scene, scene.sequence_editor, output_path, sample_rate, strips)
        
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[VSE_Transcribe] Render fallback succeeded: {output_path}")
            return output_path
        
        print(f"[VSE_Transcribe] All extraction methods failed: {error}")
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
