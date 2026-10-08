"""External API transcription engine for VSE_Transcribe.

Provides transcription via external HTTP API (OpenAI Whisper API, custom endpoints, etc.).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import EngineConfig, EngineNotAvailableError, TranscriptionEngine
from VSE_Transcrib.models.transcript import Transcript, TranscriptSegment, TranscriptWord


@dataclass
class ExternalAPIConfig(EngineConfig):
    """Configuration for ExternalAPIEngine."""

    endpoint: str = ""
    api_key: str = ""
    model: str = "whisper-1"
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 1.0  # seconds
    headers: Optional[Dict[str, str]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.headers is None:
            self.headers = {}
        if self.extra is None:
            self.extra = {}


class ExternalAPIEngine(TranscriptionEngine):
    """Transcription engine using an external HTTP API."""

    name = "external_api"

    def __init__(self):
        self._requests = None

    def _get_requests(self):
        """Lazy import requests with retry adapter."""
        if self._requests is None:
            try:
                import requests
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry
                
                # Create session with retry strategy
                session = requests.Session()
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=1.0,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                self._requests = session
            except ImportError as e:
                raise EngineNotAvailableError("requests library not installed. Install with: pip install requests") from e
        return self._requests

    def _validate_config(self, config: EngineConfig) -> None:
        """Validate engine configuration."""
        if not isinstance(config, ExternalAPIConfig):
            raise TypeError(f"Expected ExternalAPIConfig, got {type(config).__name__}")

        if not config.endpoint:
            raise ValueError("endpoint is required and must be a non-empty string")
        if not config.api_key:
            raise ValueError("api_key is required and must be a non-empty string")
        if not isinstance(config.timeout, (int, float)) or config.timeout <= 0:
            raise ValueError("timeout must be a positive number")
        if not isinstance(config.max_retries, int) or config.max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if not isinstance(config.retry_backoff, (int, float)) or config.retry_backoff < 0:
            raise ValueError("retry_backoff must be a non-negative number")

    def _check_dependencies(self) -> bool:
        """Check if requests library is available."""
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False

    def transcribe(self, audio_path: str, config: EngineConfig) -> Transcript:
        """Transcribe audio via external API with retry logic."""
        if not isinstance(config, ExternalAPIConfig):
            raise TypeError(f"Expected ExternalAPIConfig, got {type(config).__name__}")

        self._validate_config(config)

        if not self._check_dependencies():
            raise EngineNotAvailableError(
                "requests library is not installed. Install with: pip install requests"
            )

        return self._transcribe_via_api(audio_path, config)

    def _transcribe_via_api(
        self, audio_path: str, config: ExternalAPIConfig
    ) -> Transcript:
        """Send audio to API and convert response to Transcript with retries."""
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {config.api_key}",
        }
        if config.headers:
            headers.update(config.headers)

        # Get session with retry adapter
        session = self._get_requests()

        last_exception = None
        for attempt in range(config.max_retries + 1):
            try:
                # Prepare files for multipart upload
                with open(audio_path, "rb") as audio_file:
                    files = {
                        "file": (audio_path, audio_file, "audio/wav"),
                        "model": (None, config.model),
                    }

                    if config.language:
                        files["language"] = (None, config.language)

                    response = session.post(
                        config.endpoint,
                        headers=headers,
                        files=files,
                        timeout=config.timeout,
                    )

                response.raise_for_status()
                result = response.json()

                return self._convert_api_result(result, config)

            except Exception as e:
                last_exception = e
                if attempt < config.max_retries:
                    wait_time = config.retry_backoff * (2 ** attempt)  # Exponential backoff
                    time.sleep(wait_time)
                else:
                    break

        # All retries exhausted
        if last_exception:
            raise EngineNotAvailableError(f"API request failed after {config.max_retries + 1} attempts: {last_exception}")
        raise EngineNotAvailableError("API request failed for unknown reason")

    def _convert_api_result(
        self, result: Dict[str, Any], config: ExternalAPIConfig
    ) -> Transcript:
        """Convert API JSON response to Transcript.

        Expected response format (OpenAI-compatible):
        {
            "text": "full transcript text",
            "language": "en",
            "duration": 10.5,
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Hello world",
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.95},
                        ...
                    ]
                },
                ...
            ]
        }
        """
        transcript_segments: List[TranscriptSegment] = []

        segments = result.get("segments", [])
        if not segments and "text" in result:
            # Simple response without segments - create single segment
            duration = result.get("duration", 0.0)
            transcript_segments.append(TranscriptSegment(
                start=0.0,
                end=duration,
                text=result["text"].strip(),
                words=[],
            ))
        else:
            for segment in segments:
                words: List[TranscriptWord] = []
                if "words" in segment:
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

        language = result.get("language", config.language or "unknown")
        duration = result.get("duration", 0.0)
        if not duration and transcript_segments:
            duration = transcript_segments[-1].end

        return Transcript(
            language=language,
            duration=duration,
            segments=transcript_segments,
            metadata={
                "engine": self.name,
                "model": config.model,
                "endpoint": config.endpoint,
                "raw_response": result,
            },
        )


# Auto-register this engine
from .base import register_engine
register_engine("external_api", ExternalAPIEngine)