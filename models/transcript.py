"""Structured transcript data model for VSE_Transcribe.

Central data contract of the addon: the structured representation of transcription results.
Every transcription engine (local Whisper, external API) produces this same structure.
The subtitle/VSE integration layer consumes it without knowing which engine generated it.

Architecture: Engine → Transcript → Subtitle Engine → VSE

No Blender-specific logic here. Models are pure Python dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TranscriptWord:
    """A single transcribed word with precise timing.

    Only present when the engine provides word-level timestamps (e.g., Whisper with word_timestamps=True).
    """

    text: str
    start: float
    end: float
    confidence: Optional[float] = None


@dataclass
class TranscriptSegment:
    """A continuous segment of speech — the smallest unit for subtitle generation.

    Each segment maps directly to a potential subtitle Text Strip in the VSE.
    """

    start: float
    end: float
    text: str
    words: List[TranscriptWord] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Duration of this segment in seconds."""
        return self.end - self.start


@dataclass
class Transcript:
    """Complete transcription result for a media file.

    The single data structure that flows from any Engine → Subtitle Engine → VSE.
    Every engine implementation must produce this structure.
    """

    language: str
    duration: float
    segments: List[TranscriptSegment] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """Return True if the transcript has no segments."""
        return len(self.segments) == 0

    @property
    def total_words(self) -> int:
        """Return the total number of words across all segments."""
        return sum(len(s.words) for s in self.segments)
