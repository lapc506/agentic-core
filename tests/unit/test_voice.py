from __future__ import annotations

from agentic_core.application.services.voice import (
    STTProvider,
    TTSProvider,
    VoiceConfig,
    VoiceService,
)

# ── Provider enums ───────────────────────────────────────────────


def test_tts_provider_values() -> None:
    assert TTSProvider.EDGE.value == "edge"
    assert TTSProvider.ELEVENLABS.value == "elevenlabs"
    assert TTSProvider.OPENAI.value == "openai"


def test_stt_provider_values() -> None:
    assert STTProvider.LOCAL_WHISPER.value == "local_whisper"
    assert STTProvider.OPENAI_WHISPER.value == "openai_whisper"
    assert STTProvider.DEEPGRAM.value == "deepgram"


# ── VoiceConfig ──────────────────────────────────────────────────


def test_voice_config_defaults() -> None:
    cfg = VoiceConfig()
    assert cfg.tts_provider == TTSProvider.EDGE
    assert cfg.tts_voice == "en-US-AriaNeural"
    assert cfg.stt_provider == STTProvider.LOCAL_WHISPER
    assert cfg.stt_model == "base"
    assert cfg.auto_tts is False
    assert cfg.max_recording_seconds == 60


def test_voice_config_custom() -> None:
    cfg = VoiceConfig(
        tts_provider=TTSProvider.ELEVENLABS,
        tts_voice="custom-voice",
        stt_provider=STTProvider.DEEPGRAM,
        stt_model="nova-2",
        auto_tts=True,
        max_recording_seconds=120,
    )
    assert cfg.tts_provider == TTSProvider.ELEVENLABS
    assert cfg.tts_voice == "custom-voice"
    assert cfg.stt_provider == STTProvider.DEEPGRAM
    assert cfg.stt_model == "nova-2"
    assert cfg.auto_tts is True
    assert cfg.max_recording_seconds == 120


# ── VoiceService placeholder ─────────────────────────────────────


def test_synthesize_returns_empty_bytes() -> None:
    service = VoiceService()
    result = service.synthesize("Hello, world!")
    assert isinstance(result, bytes)
    assert result == b""


def test_transcribe_returns_empty_string() -> None:
    service = VoiceService()
    result = service.transcribe(b"\x00\x01\x02", mime_type="audio/wav")
    assert isinstance(result, str)
    assert result == ""


def test_transcribe_default_mime_type() -> None:
    service = VoiceService()
    result = service.transcribe(b"\x00")
    assert result == ""


def test_is_configured_default() -> None:
    service = VoiceService()
    assert service.is_configured() is True


def test_is_configured_empty_voice() -> None:
    cfg = VoiceConfig(tts_voice="")
    service = VoiceService(config=cfg)
    assert service.is_configured() is False


def test_is_configured_empty_model() -> None:
    cfg = VoiceConfig(stt_model="")
    service = VoiceService(config=cfg)
    assert service.is_configured() is False


def test_service_exposes_config() -> None:
    cfg = VoiceConfig(tts_provider=TTSProvider.OPENAI)
    service = VoiceService(config=cfg)
    assert service.config.tts_provider == TTSProvider.OPENAI
