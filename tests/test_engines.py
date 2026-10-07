"""Tests for VSE_Transcribe engines.

Tests verify:
- Import without bpy
- Config validation
- Transcribe with mocks returns valid Transcript
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from VSE_Transcrib.engines.local_whisper import LocalWhisperConfig, LocalWhisperEngine
from VSE_Transcrib.engines.external_api import ExternalAPIConfig, ExternalAPIEngine
from VSE_Transcrib.models.transcript import Transcript, TranscriptSegment, TranscriptWord


class TestLocalWhisperEngine:
    """Tests for LocalWhisperEngine."""

    def test_import_without_bpy(self):
        """Engine should import without bpy dependency."""
        from engines import local_whisper
        assert local_whisper.LocalWhisperEngine is not None

    def test_config_valid_model_size(self):
        """Valid model sizes should pass validation."""
        engine = LocalWhisperEngine()
        for size in ("tiny", "base", "small", "medium", "large", "large-v2", "large-v3"):
            config = LocalWhisperConfig(model_size=size)
            engine._validate_config(config)  # Should not raise

    def test_config_invalid_model_size(self):
        """Invalid model size should raise ValueError."""
        engine = LocalWhisperEngine()
        config = LocalWhisperConfig(model_size="invalid")
        with pytest.raises(ValueError, match="model_size must be one of"):
            engine._validate_config(config)

    def test_config_valid_device(self):
        """Valid devices should pass validation."""
        engine = LocalWhisperEngine()
        for device in ("cpu", "cuda", "auto"):
            config = LocalWhisperConfig(device=device)
            engine._validate_config(config)  # Should not raise

    def test_config_invalid_device(self):
        """Invalid device should raise ValueError."""
        engine = LocalWhisperEngine()
        config = LocalWhisperConfig(device="invalid")
        with pytest.raises(ValueError, match="device must be one of"):
            engine._validate_config(config)

    def test_config_valid_compute_type(self):
        """Valid compute types should pass validation."""
        engine = LocalWhisperEngine()
        for ct in ("int8", "int8_float16", "float16", "float32"):
            config = LocalWhisperConfig(compute_type=ct)
            engine._validate_config(config)  # Should not raise

    def test_config_invalid_compute_type(self):
        """Invalid compute type should raise ValueError."""
        engine = LocalWhisperEngine()
        config = LocalWhisperConfig(compute_type="invalid")
        with pytest.raises(ValueError, match="compute_type must be one of"):
            engine._validate_config(config)

    def test_wrong_config_type_raises(self):
        """Passing wrong config type should raise TypeError."""
        engine = LocalWhisperEngine()
        from engines.base import EngineConfig
        config = EngineConfig()
        with pytest.raises(TypeError, match="Expected LocalWhisperConfig"):
            engine._validate_config(config)

    def test_transcribe_wrong_config_type_raises(self):
        """transcribe with wrong config type should raise TypeError."""
        engine = LocalWhisperEngine()
        from engines.base import EngineConfig
        config = EngineConfig()
        with pytest.raises(TypeError, match="Expected LocalWhisperConfig"):
            engine.transcribe("/fake/path.wav", config)

    @patch("engines.local_whisper.LocalWhisperEngine._check_dependencies", return_value=True)
    @patch("engines.local_whisper.LocalWhisperEngine._transcribe_faster_whisper")
    def test_transcribe_calls_faster_whisper_first(self, mock_transcribe, mock_deps):
        """Should try faster-whisper first."""
        engine = LocalWhisperEngine()
        mock_result = Transcript(
            language="en",
            duration=5.0,
            segments=[TranscriptSegment(start=0.0, end=5.0, text="test")],
        )
        mock_transcribe.return_value = mock_result

        config = LocalWhisperConfig(model_size="base")
        result = engine.transcribe("/fake/path.wav", config)

        assert isinstance(result, Transcript)
        mock_transcribe.assert_called_once()

    @patch("engines.local_whisper.LocalWhisperEngine._check_dependencies", return_value=False)
    def test_transcribe_no_deps_raises(self, mock_deps):
        """Should raise EngineNotAvailableError when no deps."""
        engine = LocalWhisperEngine()
        config = LocalWhisperConfig(model_size="base")
        from engines.base import EngineNotAvailableError
        with pytest.raises(EngineNotAvailableError, match="faster-whisper nor whisper"):
            engine.transcribe("/fake/path.wav", config)


class TestExternalAPIEngine:
    """Tests for ExternalAPIEngine."""

    def test_import_without_bpy(self):
        """Engine should import without bpy dependency."""
        from engines import external_api
        assert external_api.ExternalAPIEngine is not None

    def test_config_valid_endpoint_and_key(self):
        """Valid endpoint and api_key should pass validation."""
        engine = ExternalAPIEngine()
        config = ExternalAPIConfig(
            endpoint="https://api.example.com/v1/audio/transcriptions",
            api_key="test-key-123",
        )
        engine._validate_config(config)  # Should not raise

    def test_config_missing_endpoint(self):
        """Missing endpoint should raise ValueError."""
        engine = ExternalAPIEngine()
        config = ExternalAPIConfig(endpoint="", api_key="key")
        with pytest.raises(ValueError, match="endpoint is required"):
            engine._validate_config(config)

    def test_config_missing_api_key(self):
        """Missing api_key should raise ValueError."""
        engine = ExternalAPIEngine()
        config = ExternalAPIConfig(endpoint="https://api.example.com", api_key="")
        with pytest.raises(ValueError, match="api_key is required"):
            engine._validate_config(config)

    def test_config_invalid_timeout(self):
        """Invalid timeout should raise ValueError."""
        engine = ExternalAPIEngine()
        config = ExternalAPIConfig(
            endpoint="https://api.example.com",
            api_key="key",
            timeout=-1,
        )
        with pytest.raises(ValueError, match="timeout must be a positive number"):
            engine._validate_config(config)

    def test_wrong_config_type_raises(self):
        """Passing wrong config type should raise TypeError."""
        engine = ExternalAPIEngine()
        from engines.base import EngineConfig
        config = EngineConfig()
        with pytest.raises(TypeError, match="Expected ExternalAPIConfig"):
            engine._validate_config(config)

    def test_transcribe_wrong_config_type_raises(self):
        """transcribe with wrong config type should raise TypeError."""
        engine = ExternalAPIEngine()
        from engines.base import EngineConfig
        config = EngineConfig()
        with pytest.raises(TypeError, match="Expected ExternalAPIConfig"):
            engine.transcribe("/fake/path.wav", config)

    @patch("engines.external_api.requests.post")
    @patch("builtins.open", new_callable=MagicMock)
    def test_transcribe_mock_returns_valid_transcript(self, mock_open, mock_post):
        """Transcribe with mocked API should return valid Transcript."""
        engine = ExternalAPIEngine()

        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "text": "Hello world",
            "language": "en",
            "duration": 2.0,
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "Hello world",
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 1.0, "probability": 0.95},
                        {"word": "world", "start": 1.0, "end": 2.0, "probability": 0.9},
                    ],
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Mock file open
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        config = ExternalAPIConfig(
            endpoint="https://api.example.com/v1/audio/transcriptions",
            api_key="test-key",
        )
        result = engine.transcribe("/fake/path.wav", config)

        assert isinstance(result, Transcript)
        assert result.language == "en"
        assert result.duration == 2.0
        assert len(result.segments) == 1
        assert result.segments[0].text == "Hello world"
        assert len(result.segments[0].words) == 2

    @patch("engines.external_api.ExternalAPIEngine._check_dependencies", return_value=False)
    def test_transcribe_no_requests_raises(self, mock_deps):
        """Should raise EngineNotAvailableError when requests not installed."""
        engine = ExternalAPIEngine()
        config = ExternalAPIConfig(
            endpoint="https://api.example.com",
            api_key="key",
        )
        from engines.base import EngineNotAvailableError
        with pytest.raises(EngineNotAvailableError, match="requests library"):
            engine.transcribe("/fake/path.wav", config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])