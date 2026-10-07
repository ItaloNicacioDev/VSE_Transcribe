"""Local Whisper/faster-whisper engine for VSE_Transcribe.

Provides local transcription using OpenAI's Whisper model via faster-whisper (recommended)
or the original whisper library as fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import EngineConfig, EngineNotAvailableError, TranscriptionEngine
from VSE_Transcrib.models.transcript import Transcript, TranscriptSegment, TranscriptWord


# Valid configuration values
VALID_MODEL_SIZES = ("tiny", "base", "small", "medium", "large", "large-v2", "large-v3")
VALID_DEVICES = ("cpu", "cuda", "auto")
VALID_COMPUTE_TYPES = ("int8", "int8_float16", "float16", "float32")


@dataclass
class LocalWhisperConfig(EngineConfig):
    """Configuration for LocalWhisperEngine."""

    model_size: str = "base"
    device: str = "auto"
    word_timestamps: bool = False
    compute_type: str = "float16"

    def __post_init__(self):
        super().__post_init__()
        if self.extra is None:
            self.extra = {}


class LocalWhisperEngine(TranscriptionEngine):
    """Local transcription engine using Whisper/faster-whisper."""

    name = "local_whisper"

    def _validate_config(self, config: EngineConfig) -> None:
        """Validate engine configuration."""
        if not isinstance(config, LocalWhisperConfig):
            raise TypeError(f"Expected LocalWhisperConfig, got {type(config).__name__}")
        if config.model_size not in VALID_MODEL_SIZES:
            raise ValueError(
                f"model_size must be one of {VALID_MODEL_SIZES}, got '{config.model_size}'"
            )
        if config.device not in VALID_DEVICES:
            raise ValueError(
                f"device must be one of {VALID_DEVICES}, got '{config.device}'"
            )
        if config.compute_type not in VALID_COMPUTE_TYPES:
            raise ValueError(
                f"compute_type must be one of {VALID_COMPUTE_TYPES}, got '{config.compute_type}'"
            )

    def _check_dependencies(self) -> bool:
        """Check if faster-whisper or whisper is available."""
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            pass
        try:
            import whisper  # noqa: F401
            return True
        except ImportError:
            pass
        return False

    def transcribe(self, audio_path: str, config: EngineConfig) -> Transcript:
        """Transcribe audio using faster-whisper (preferred) or whisper."""
        if not isinstance(config, LocalWhisperConfig):
            raise TypeError(f"Expected LocalWhisperConfig, got {type(config).__name__}")
        self._validate_config(config)

        if not self._check_dependencies():
            raise EngineNotAvailableError(
                "Neither faster-whisper nor whisper is installed. "
                "Install with: pip install faster-whisper"
            )

        # Try faster-whisper first (faster, lower memory)
        try:
            return self._transcribe_faster_whisper(audio_path, config)
        except ImportError:
            pass

        # Fallback to original whisper
        try:
            return self._transcribe_whisper(audio_path, config)
        except ImportError:
            pass

        raise EngineNotAvailableError(
            "Neither faster-whisper nor whisper is available at runtime."
        )

    def _transcribe_faster_whisper(
        self, audio_path: str, config: LocalWhisperConfig
    ) -> Transcript:
        """Transcribe using faster-whisper."""
        from faster_whisper import WhisperModel

        # Resolve device
        device = config.device
        if device == "auto":
            device = "cuda" if self._has_cuda() else "cpu"

        # Create model
        model = WhisperModel(
            config.model_size,
            device=device,
            compute_type=config.compute_type,
        )

        # Run transcription
        segments, info = model.transcribe(
            audio_path,
            language=config.language,
            word_timestamps=config.word_timestamps,
        )

        # Convert to our Transcript format
        return self._convert_faster_whisper_result(segments, info, config)

    def _transcribe_whisper(self, audio_path: str, config: LocalWhisperConfig) -> Transcript:
        """Transcribe using original whisper library."""
        import whisper

        # Resolve device
        device = config.device
        if device == "auto":
            device = "cuda" if self._has_cuda() else "cpu"

        # Load model
        model = whisper.load_model(config.model_size, device=device)

        # Run transcription
        result = model.transcribe(
            audio_path,
            language=config.language,
            word_timestamps=config.word_timestamps,
        )

        # Convert to our Transcript format
        return self._convert_whisper_result(result, config)

    def _has_cuda(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _convert_faster_whisper_result(
        self,
        segments,
        info,
        config: LocalWhisperConfig
    ) -> Transcript:
        """Convert faster-whisper output to Transcript."""
        transcript_segments: List[TranscriptSegment] = []

        for segment in segments:
            words: List[TranscriptWord] = []
            if config.word_timestamps and segment.words:
                for word in segment.words:
                    words.append(TranscriptWord(
                        text=word.word,
                        start=word.start,
                        end=word.end,
                        confidence=word.probability,
                    ))

            transcript_segments.append(TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
                words=words,
            ))

        return Transcript(
            language=info.language or config.language or "unknown",
            duration=sum(s.duration for s in transcript_segments) if transcript_segments else 0.0,
            segments=transcript_segments,
            metadata={
                "engine": self.name,
                "model_size": config.model_size,
                "device": config.device,
                "compute_type": config.compute_type,
                "word_timestamps": config.word_timestamps,
                "language_probability": info.language_probability,
            },
        )

    def _convert_whisper_result(self, result: Dict[str, Any], config: LocalWhisperConfig) -> Transcript:
        """Convert original whisper output to Transcript."""
        transcript_segments: List[TranscriptSegment] = []

        for segment in result.get("segments", []):
            words: List[TranscriptWord] = []
            if config.word_timestamps and "words" in segment:
                for word in segment["words"]:
                    words.append(TranscriptWord(
                        text=word.get("word", ""),
                        start=word.get("start", 0.0),
                        end=word.get("end", 0.0),
                        confidence=word.get("probability"),
                    ))

            transcript_segments.append(TranscriptSegment(
                start=segment["start"],
                end=segment["end"],
                text=segment["text"].strip(),
                words=words,
            ))

        duration = transcript_segments[-1].end if transcript_segments else 0.0

        return Transcript(
            language=result.get("language", config.language or "unknown"),
            duration=duration,
            segments=transcript_segments,
            metadata={
                "engine": self.name,
                "model_size": config.model_size,
                "device": config.device,
                "word_timestamps": config.word_timestamps,
            },
        )


# Auto-register this engine
from .base import register_engine
register_engine("local_whisper", LocalWhisperEngine)