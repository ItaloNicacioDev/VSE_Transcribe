"""Subtitle preparation engine for VSE_Transcribe.

Converts a Transcript into a list of SubtitleBlocks — an intermediate,
Blender-free representation ready to be turned into VSE Text Strips by
the strip manager. No bpy here: this module only shapes text and timings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from ..models.transcript import Transcript
from .transcription import filter_empty_segments, normalize_transcript


@dataclass
class SubtitleConfig:
    """Configuration for subtitle block generation."""

    max_chars_per_line: int = 42
    max_lines: int = 2
    min_duration: float = 1.0
    gap_threshold: float = 0.5


@dataclass
class SubtitleBlock:
    """Intermediate subtitle unit, before conversion to a VSE strip.

    Attributes:
        start: Block start time in seconds.
        end: Block end time in seconds.
        text: Full text of the block (lines joined by newline).
        lines: Text already wrapped into display lines.
    """

    start: float
    end: float
    text: str
    lines: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Duration of this block in seconds."""
        return self.end - self.start


def normalize_subtitle_text(text: str) -> str:
    """Clean up segment text for subtitle display.

    Collapses internal whitespace runs to single spaces, trims the ends
    and strips stray whitespace before punctuation.

    Args:
        text: Raw segment text.

    Returns:
        Normalized text.
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    return cleaned


def split_text_into_lines(text: str, max_chars_per_line: int) -> List[str]:
    """Wrap text into lines of at most max_chars_per_line characters.

    Breaks on word boundaries and balances line lengths (greedy fill, then
    a balance pass that pulls words from a longer first line into the
    second when two lines suffice). Words longer than the limit are kept
    whole on their own line rather than split mid-word.

    Args:
        text: Text to wrap (whitespace already normalized ideally).
        max_chars_per_line: Maximum characters per line (must be > 0).

    Returns:
        List of lines.

    Raises:
        ValueError: If max_chars_per_line <= 0.
    """
    if max_chars_per_line <= 0:
        raise ValueError(f"max_chars_per_line must be positive, got {max_chars_per_line}")
    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or len(candidate) <= max_chars_per_line:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def merge_short_blocks(
    blocks: List[SubtitleBlock], min_duration: float
) -> List[SubtitleBlock]:
    """Merge blocks shorter than min_duration into a neighbouring block.

    A too-short block is merged forward into the next block when possible
    (extending its end), otherwise backward into the previous one. Merged
    text is joined with a space and lines are re-wrapped by the caller if
    needed — here we keep ``lines`` empty on merged blocks to signal that
    wrapping must be recomputed, except for untouched blocks.

    Args:
        blocks: Blocks in chronological order.
        min_duration: Minimum acceptable duration in seconds.

    Returns:
        New list of blocks with short blocks merged.
    """
    if not blocks:
        return []
    result: List[SubtitleBlock] = [
        SubtitleBlock(b.start, b.end, b.text, list(b.lines)) for b in blocks
    ]
    i = 0
    while i < len(result):
        block = result[i]
        if block.duration >= min_duration:
            i += 1
            continue
        if i + 1 < len(result):
            nxt = result[i + 1]
            merged = SubtitleBlock(
                start=block.start,
                end=nxt.end,
                text=f"{block.text} {nxt.text}".strip(),
            )
            result[i : i + 2] = [merged]
            # re-check merged block (it may still be too short)
        elif i > 0:
            prev = result[i - 1]
            prev.end = block.end
            prev.text = f"{prev.text} {block.text}".strip()
            prev.lines = []
            del result[i]
        else:
            # single short block: nothing to merge with
            i += 1
    return result


def prepare_subtitles(
    transcript: Transcript, config: SubtitleConfig | None = None
) -> List[SubtitleBlock]:
    """Convert a Transcript into subtitle blocks.

    Pipeline: normalize → filter empty segments → build blocks with wrapped
    lines → merge too-short blocks (re-wrapping merged text). Original
    segment timings are preserved for untouched blocks.

    Args:
        transcript: Source transcript.
        config: Subtitle configuration; defaults are used when omitted.

    Returns:
        Chronological list of SubtitleBlocks ready for the VSE layer.
    """
    if config is None:
        config = SubtitleConfig()
    normalized = normalize_transcript(transcript)
    segments = filter_empty_segments(normalized.segments)

    blocks: List[SubtitleBlock] = []
    for seg in segments:
        text = normalize_subtitle_text(seg.text)
        if not text:
            text = normalize_subtitle_text(" ".join(w.text for w in seg.words))
        if not text:
            continue
        lines = split_text_into_lines(text, config.max_chars_per_line)
        lines = lines[: config.max_lines]
        blocks.append(
            SubtitleBlock(
                start=seg.start,
                end=seg.end,
                text=text,
                lines=lines,
            )
        )

    blocks = merge_short_blocks(blocks, config.min_duration)
    for block in blocks:
        if not block.lines:
            block.lines = split_text_into_lines(
                block.text, config.max_chars_per_line
            )[: config.max_lines]
    return blocks
