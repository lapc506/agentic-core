from __future__ import annotations

import logging
from enum import StrEnum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TTSProvider(StrEnum):
    """Supported text-to-speech providers."""

    EDGE = "edge"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"


class STTProvider(StrEnum):
    """Supported speech-to-text providers."""

    LOCAL_WHISPER = "local_whisper"
    OPENAI_WHISPER = "openai_whisper"
    DEEPGRAM = "deepgram"


class VoiceConfig(BaseModel):
    """Voice integration configuration, embeddable in persona YAML."""

    tts_provider: TTSProvider = TTSProvider.EDGE
    tts_voice: str = Field(default="en-US-AriaNeural")
    stt_provider: STTProvider = STTProvider.LOCAL_WHISPER
    stt_model: str = Field(default="base")
    auto_tts: bool = Field(default=False)
    max_recording_seconds: int = Field(default=60, ge=1, le=300)


class VoiceService:
    """Placeholder voice service providing TTS synthesis and STT transcription.

    Concrete provider adapters (Edge TTS, Whisper, ElevenLabs, etc.) will be
    injected once the adapter layer is implemented.  Until then every method
    returns safe defaults so the rest of the system can reference and configure
    voice capabilities without hard dependencies.
    """

    def __init__(self, config: VoiceConfig | None = None) -> None:
        self._config = config or VoiceConfig()

    @property
    def config(self) -> VoiceConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(self, text: str) -> bytes:
        """Convert *text* to audio bytes using the configured TTS provider.

        Returns empty bytes until a real provider adapter is wired.
        """
        logger.info(
            "TTS synthesize (placeholder): provider=%s, voice=%s, text_len=%d",
            self._config.tts_provider.value,
            self._config.tts_voice,
            len(text),
        )
        return b""

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """Transcribe *audio_bytes* to text using the configured STT provider.

        Returns an empty string until a real provider adapter is wired.
        """
        logger.info(
            "STT transcribe (placeholder): provider=%s, model=%s, audio_len=%d, mime=%s",
            self._config.stt_provider.value,
            self._config.stt_model,
            len(audio_bytes),
            mime_type,
        )
        return ""

    def is_configured(self) -> bool:
        """Return whether the voice service has a usable configuration.

        Currently checks that both provider fields and a voice/model are set.
        """
        return bool(self._config.tts_voice) and bool(self._config.stt_model)
