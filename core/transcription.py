"""Transcript processing utilities for VSE_Transcribe.

Pure-Python operations over the models defined in models/transcript.py:
validation, normalization, merging and splitting. No bpy, no duplication
of the data models — this module imports them and operates on them.
"""

from __future__ import annotations

import copy
from typing import List

from ..models.transcript import Transcript, TranscriptSegment, TranscriptWord


def validate_transcript(transcript: Transcript) -> List[str]:
    """Validate a Transcript structurally and return a list of problems found.

    A transcript with an empty problem list is considered valid. Checks:
    - language is a non-empty string
    - duration is a non-negative number
    - every segment has end >= start and both >= 0
    - every word (when present) has end >= start and fits within its segment

    Args:
        transcript: The Transcript to validate.

    Returns:
        List of human-readable problem descriptions; empty when valid.
    """
    problems: List[str] = []
    if not isinstance(transcript.language, str) or not transcript.language:
        problems.append("language must be a non-empty string")
    if not isinstance(transcript.duration, (int, float)) or isinstance(
        transcript.duration, bool
    ):
        problems.append("duration must be a number")
    elif transcript.duration < 0:
        problems.append(f"duration must be non-negative, got {transcript.duration}")

    for i, seg in enumerate(transcript.segments):
        problems.extend(_validate_segment(seg, f"segments[{i}]"))
    return problems


def _validate_segment(seg: TranscriptSegment, path: str) -> List[str]:
    """Validate one segment and its words, prefixing problems with path."""
    problems: List[str] = []
    if seg.start < 0:
        problems.append(f"{path}: start must be non-negative, got {seg.start}")
    if seg.end < seg.start:
        problems.append(f"{path}: end ({seg.end}) < start ({seg.start})")
    if not isinstance(seg.text, str):
        problems.append(f"{path}: text must be a string")
        return problems
    for j, word in enumerate(seg.words):
        wp = f"{path}.words[{j}]"
        if word.start < 0:
            problems.append(f"{wp}: start must be non-negative, got {word.start}")
        if word.end < word.start:
            problems.append(f"{wp}: end ({word.end}) < start ({word.start})")
        if word.start < seg.start or word.end > seg.end:
            problems.append(
                f"{wp}: word timing [{word.start}, {word.end}] outside segment "
                f"[{seg.start}, {seg.end}]"
            )
    return problems


def normalize_transcript(transcript: Transcript) -> Transcript:
    """Return a normalized copy of the transcript.

    Normalization:
    - segments sorted by start time (stable for equal starts)
    - text trimmed of surrounding whitespace; all-whitespace text becomes ""
    - words within each segment sorted by start time
    - the input transcript is not modified

    Args:
        transcript: The Transcript to normalize.

    Returns:
        A new, normalized Transcript.
    """
    normalized = copy.deepcopy(transcript)
    normalized.segments.sort(key=lambda s: (s.start, s.end))
    for seg in normalized.segments:
        seg.text = seg.text.strip()
        seg.words.sort(key=lambda w: (w.start, w.end))
    return normalized


def merge_segments(
    segments: List[TranscriptSegment], max_gap: float
) -> List[TranscriptSegment]:
    """Merge adjacent segments whose gap is <= max_gap seconds.

    Segments are merged in list order (normalize/sort first if order is not
    guaranteed). Merged segment text is joined with a single space; words
    are concatenated. The input segments are not modified.

    Args:
        segments: Segments to merge (assumed in chronological order).
        max_gap: Maximum silence between segments to still merge them.

    Returns:
        A new list of merged TranscriptSegments.
    """
    if not segments:
        return []
    merged: List[TranscriptSegment] = [copy.deepcopy(segments[0])]
    for seg in segments[1:]:
        last = merged[-1]
        if seg.start - last.end <= max_gap:
            last.end = max(last.end, seg.end)
            last.text = " ".join(t for t in (last.text, seg.text) if t)
            last.words.extend(copy.deepcopy(seg.words))
        else:
            merged.append(copy.deepcopy(seg))
    return merged


def filter_empty_segments(
    segments: List[TranscriptSegment],
) -> List[TranscriptSegment]:
    """Drop segments that carry no usable content.

    A segment is considered empty when its text is whitespace-only/empty
    AND it has no words.

    Args:
        segments: Segments to filter.

    Returns:
        A new list containing only non-empty segments.
    """
    return [s for s in segments if s.text.strip() or s.words]


def split_segment_by_words(
    segment: TranscriptSegment, max_words: int
) -> List[TranscriptSegment]:
    """Split a segment into sub-segments of at most max_words words each.

    Timings are derived from the words themselves: each sub-segment spans
    from its first word's start to its last word's end. Segments without
    words, or with max_words <= 0, are returned unchanged (single-element
    list containing a copy).

    Args:
        segment: The segment to split.
        max_words: Maximum number of words per resulting sub-segment.

    Returns:
        List of new TranscriptSegments (input is not modified).
    """
    if max_words <= 0 or not segment.words or len(segment.words) <= max_words:
        return [copy.deepcopy(segment)]
    chunks: List[TranscriptSegment] = []
    words = segment.words
    for i in range(0, len(words), max_words):
        window = [copy.deepcopy(w) for w in words[i : i + max_words]]
        chunk = TranscriptSegment(
            start=window[0].start,
            end=window[-1].end,
            text=" ".join(w.text for w in window),
            words=window,
        )
        chunks.append(chunk)
    return chunks
