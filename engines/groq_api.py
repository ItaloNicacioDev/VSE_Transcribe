"""Groq Whisper API engine for VSE_Transcribe.

Uses Groq's OpenAI-compatible endpoint. Only the Python standard library is
used (no `requests` needed inside Blender's Python).

Long audio (> ~24 MB, the upload limit) is split into WAV chunks and the
timestamps are merged back together.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import wave
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .base import EngineConfig, EngineNotAvailableError, TranscriptionEngine
from VSE_Transcrib.models.transcript import Transcript, TranscriptSegment, TranscriptWord

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MAX_UPLOAD_BYTES = 24 * 1024 * 1024  # Groq free tier limit is 25 MB

VALID_GROQ_MODELS = ("whisper-large-v3-turbo", "whisper-large-v3")

_LANG_NAMES = {
    "portuguese": "pt", "english": "en", "spanish": "es", "french": "fr",
    "german": "de", "italian": "it", "japanese": "ja", "korean": "ko",
    "chinese": "zh", "russian": "ru", "dutch": "nl", "polish": "pl",
    "turkish": "tr", "arabic": "ar", "hindi": "hi", "ukrainian": "uk",
}


@dataclass
class GroqConfig(EngineConfig):
    """Configuration for GroqEngine."""

    api_key: str = ""
    model: str = "whisper-large-v3-turbo"
    word_timestamps: bool = False
    timeout: float = 300.0
    max_retries: int = 3
    retry_backoff: float = 2.0

    def __post_init__(self):
        super().__post_init__()


class GroqEngine(TranscriptionEngine):
    """Transcription through the Groq cloud Whisper API."""

    name = "groq_api"

    def _validate_config(self, config: EngineConfig) -> None:
        if not isinstance(config, GroqConfig):
            raise TypeError(f"Expected GroqConfig, got {type(config).__name__}")
        if not config.api_key:
            raise ValueError("Groq API key is empty (set it in Add-on Preferences or GROQ_API_KEY)")
        if config.model not in VALID_GROQ_MODELS:
            raise ValueError(f"model must be one of {VALID_GROQ_MODELS}, got '{config.model}'")

    # ------------------------------------------------------------------
    def transcribe(
        self,
        audio_path: str,
        config: EngineConfig,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Transcript:
        self._validate_config(config)
        if not os.path.exists(audio_path):
            raise FileNotFoundError(audio_path)

        chunks = self._prepare_chunks(audio_path)
        segments: List[TranscriptSegment] = []
        language = ""
        duration = 0.0
        total = len(chunks)

        try:
            for i, (path, offset, _is_temp) in enumerate(chunks):
                if progress_callback:
                    progress_callback(i / total, f"Groq {i + 1}/{total}")
                result = self._request(path, config)
                language = language or str(result.get("language") or "")
                duration = max(duration, offset + float(result.get("duration") or 0.0))
                segments.extend(self._parse_segments(result, offset))
            if progress_callback:
                progress_callback(1.0, "")
        finally:
            for path, _offset, is_temp in chunks:
                if is_temp:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

        if segments and duration < segments[-1].end:
            duration = segments[-1].end

        code = config.language or _LANG_NAMES.get(language.lower(), language) or "unknown"
        return Transcript(
            language=code,
            duration=duration,
            segments=segments,
            metadata={"engine": self.name, "model": config.model, "chunks": total},
        )

    # ------------------------------------------------------------------
    def _prepare_chunks(self, audio_path: str) -> List[Tuple[str, float, bool]]:
        """Return [(path, offset_seconds, is_temp_file)]."""
        if os.path.getsize(audio_path) <= MAX_UPLOAD_BYTES:
            return [(audio_path, 0.0, False)]

        try:
            wf = wave.open(audio_path, "rb")
        except Exception as e:
            raise EngineNotAvailableError(
                f"Audio is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB and is not a plain WAV "
                f"file, so it cannot be split for Groq ({e})."
            )

        chunks: List[Tuple[str, float, bool]] = []
        with wf:
            rate = wf.getframerate()
            bytes_per_sec = rate * wf.getnchannels() * wf.getsampwidth()
            chunk_seconds = max(30, int(MAX_UPLOAD_BYTES * 0.9 / bytes_per_sec))
            frames_per_chunk = rate * chunk_seconds
            index = 0
            while True:
                data = wf.readframes(frames_per_chunk)
                if not data:
                    break
                fd, path = tempfile.mkstemp(suffix=".wav", prefix="vse_groq_chunk_")
                os.close(fd)
                with wave.open(path, "wb") as out:
                    out.setnchannels(wf.getnchannels())
                    out.setsampwidth(wf.getsampwidth())
                    out.setframerate(rate)
                    out.writeframes(data)
                chunks.append((path, float(index * chunk_seconds), True))
                index += 1
        return chunks

    def _request(self, path: str, config: GroqConfig) -> dict:
        with open(path, "rb") as f:
            payload = f.read()

        # Best-effort filename so the server detects the container correctly
        if payload[:4] == b"RIFF":
            filename = "audio.wav"
        elif payload[:4] == b"\x1a\x45\xdf\xa3":  # Matroska/WebM (render fallback output)
            filename = "audio.webm"
        else:
            filename = os.path.basename(path) or "audio.wav"

        fields = [
            ("model", config.model),
            ("response_format", "verbose_json"),
            ("temperature", "0"),
            ("timestamp_granularities[]", "segment"),
        ]
        if config.word_timestamps:
            fields.append(("timestamp_granularities[]", "word"))
        if config.language:
            fields.append(("language", config.language))

        boundary = "----VSETranscribe" + uuid.uuid4().hex
        body = bytearray()
        for name, value in fields:
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
            body += str(value).encode("utf-8") + b"\r\n"
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        body += b"Content-Type: application/octet-stream\r\n\r\n"
        body += payload + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        body = bytes(body)

        last_error = "unknown error"
        for attempt in range(config.max_retries + 1):
            req = urllib.request.Request(
                GROQ_URL,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Accept": "application/json",
                    # Default Python UA is blocked by Cloudflare in front of the API
                    "User-Agent": "VSE_Transcribe/0.1 (Blender add-on)",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=config.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                text = e.read().decode("utf-8", "replace")[:500]
                last_error = f"HTTP {e.code}: {text}"
                if e.code in (429, 500, 502, 503, 504) and attempt < config.max_retries:
                    try:
                        wait = float(e.headers.get("retry-after") or 0)
                    except ValueError:
                        wait = 0.0
                    time.sleep(min(max(wait, config.retry_backoff * (2 ** attempt)), 30.0))
                    continue
                raise EngineNotAvailableError(f"Groq API error ({last_error})")
            except urllib.error.URLError as e:
                last_error = f"network error: {e.reason}"
                if attempt < config.max_retries:
                    time.sleep(config.retry_backoff * (2 ** attempt))
                    continue
                raise EngineNotAvailableError(f"Could not reach Groq ({last_error})")

        raise EngineNotAvailableError(f"Groq API failed: {last_error}")

    @staticmethod
    def _parse_segments(result: dict, offset: float) -> List[TranscriptSegment]:
        raw_segments = result.get("segments") or []
        parsed = []
        for s in raw_segments:
            text = (s.get("text") or "").strip()
            if not text:
                continue
            parsed.append(
                TranscriptSegment(
                    start=float(s["start"]) + offset,
                    end=float(s["end"]) + offset,
                    text=text,
                    words=[],
                )
            )

        if not parsed and (result.get("text") or "").strip():
            parsed.append(
                TranscriptSegment(
                    start=offset,
                    end=offset + float(result.get("duration") or 0.0),
                    text=result["text"].strip(),
                    words=[],
                )
            )

        for w in result.get("words") or []:
            if not parsed:
                break
            ws = float(w.get("start", 0.0)) + offset
            target = next((s for s in parsed if s.start - 0.05 <= ws < s.end + 0.05), parsed[-1])
            target.words.append(
                TranscriptWord(
                    text=str(w.get("word", "")),
                    start=ws,
                    end=float(w.get("end", ws - offset)) + offset,
                    confidence=None,
                )
            )
        return parsed


# Auto-register this engine
from .base import register_engine  # noqa: E402

try:
    register_engine("groq_api", GroqEngine)
except ValueError:
    pass  # already registered (addon reload)