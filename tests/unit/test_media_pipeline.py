from __future__ import annotations

import pytest

from agentic_core.application.services.media_pipeline import (
    MediaConfig,
    MediaInput,
    MediaPipeline,
    MediaResult,
    MediaType,
    _MB,
)


# --- MediaType enum ---


def test_media_type_image_value() -> None:
    assert MediaType.IMAGE.value == "image"


def test_media_type_audio_value() -> None:
    assert MediaType.AUDIO.value == "audio"


def test_media_type_video_value() -> None:
    assert MediaType.VIDEO.value == "video"


def test_media_type_members() -> None:
    assert set(MediaType) == {MediaType.IMAGE, MediaType.AUDIO, MediaType.VIDEO}


# --- MediaConfig defaults ---


def test_media_config_default_max_bytes() -> None:
    config = MediaConfig()
    assert config.max_bytes[MediaType.IMAGE] == 10 * _MB
    assert config.max_bytes[MediaType.AUDIO] == 25 * _MB
    assert config.max_bytes[MediaType.VIDEO] == 100 * _MB


def test_media_config_default_allowed_formats() -> None:
    config = MediaConfig()
    assert "jpg" in config.allowed_formats[MediaType.IMAGE]
    assert "png" in config.allowed_formats[MediaType.IMAGE]
    assert "mp3" in config.allowed_formats[MediaType.AUDIO]
    assert "mp4" in config.allowed_formats[MediaType.VIDEO]


def test_media_config_default_models() -> None:
    config = MediaConfig()
    assert config.default_model[MediaType.IMAGE] == "gpt-4o"
    assert config.default_model[MediaType.AUDIO] == "whisper-1"
    assert config.default_model[MediaType.VIDEO] == "gemini-1.5-pro"


# --- MediaInput / MediaResult construction ---


def test_media_input_construction() -> None:
    inp = MediaInput(
        media_type=MediaType.IMAGE,
        file_path="/tmp/photo.jpg",
        mime_type="image/jpeg",
        size_bytes=1024,
    )
    assert inp.media_type == MediaType.IMAGE
    assert inp.file_path == "/tmp/photo.jpg"
    assert inp.mime_type == "image/jpeg"
    assert inp.size_bytes == 1024


def test_media_input_is_frozen() -> None:
    inp = MediaInput(
        media_type=MediaType.AUDIO,
        file_path="/tmp/clip.mp3",
        mime_type="audio/mp3",
        size_bytes=500,
    )
    with pytest.raises(Exception):
        inp.file_path = "/other"  # type: ignore[misc]


def test_media_result_construction() -> None:
    result = MediaResult(
        success=True,
        media_type=MediaType.VIDEO,
        content="Summary text",
    )
    assert result.success is True
    assert result.media_type == MediaType.VIDEO
    assert result.content == "Summary text"
    assert result.error is None


def test_media_result_with_error() -> None:
    result = MediaResult(
        success=False,
        media_type=MediaType.IMAGE,
        content="",
        error="File too large",
    )
    assert result.success is False
    assert result.error == "File too large"


# --- Validation ---


def test_validate_valid_input_returns_none() -> None:
    pipeline = MediaPipeline()
    inp = MediaInput(
        media_type=MediaType.IMAGE,
        file_path="/tmp/photo.png",
        mime_type="image/png",
        size_bytes=1024,
    )
    assert pipeline.validate(inp) is None


def test_validate_file_too_large() -> None:
    pipeline = MediaPipeline()
    inp = MediaInput(
        media_type=MediaType.IMAGE,
        file_path="/tmp/huge.png",
        mime_type="image/png",
        size_bytes=11 * _MB,
    )
    result = pipeline.validate(inp)
    assert result is not None
    assert result.success is False
    assert "exceeds limit" in (result.error or "")


def test_validate_invalid_format() -> None:
    pipeline = MediaPipeline()
    inp = MediaInput(
        media_type=MediaType.IMAGE,
        file_path="/tmp/file.bmp",
        mime_type="image/bmp",
        size_bytes=1024,
    )
    result = pipeline.validate(inp)
    assert result is not None
    assert result.success is False
    assert "not allowed" in (result.error or "")


def test_validate_audio_too_large() -> None:
    pipeline = MediaPipeline()
    inp = MediaInput(
        media_type=MediaType.AUDIO,
        file_path="/tmp/huge.mp3",
        mime_type="audio/mp3",
        size_bytes=26 * _MB,
    )
    result = pipeline.validate(inp)
    assert result is not None
    assert result.success is False


# --- Process (async) ---


@pytest.mark.asyncio
async def test_process_image() -> None:
    pipeline = MediaPipeline()
    inp = MediaInput(
        media_type=MediaType.IMAGE,
        file_path="/tmp/photo.jpg",
        mime_type="image/jpg",
        size_bytes=1024,
    )
    result = await pipeline.process(inp)
    assert result.success is True
    assert result.media_type == MediaType.IMAGE
    assert "placeholder" in result.content.lower()


@pytest.mark.asyncio
async def test_process_audio() -> None:
    pipeline = MediaPipeline()
    inp = MediaInput(
        media_type=MediaType.AUDIO,
        file_path="/tmp/clip.mp3",
        mime_type="audio/mp3",
        size_bytes=2048,
    )
    result = await pipeline.process(inp)
    assert result.success is True
    assert result.media_type == MediaType.AUDIO
    assert "placeholder" in result.content.lower()


@pytest.mark.asyncio
async def test_process_video() -> None:
    pipeline = MediaPipeline()
    inp = MediaInput(
        media_type=MediaType.VIDEO,
        file_path="/tmp/clip.mp4",
        mime_type="video/mp4",
        size_bytes=4096,
    )
    result = await pipeline.process(inp)
    assert result.success is True
    assert result.media_type == MediaType.VIDEO
    assert "placeholder" in result.content.lower()


@pytest.mark.asyncio
async def test_process_rejects_invalid_input() -> None:
    pipeline = MediaPipeline()
    inp = MediaInput(
        media_type=MediaType.IMAGE,
        file_path="/tmp/huge.png",
        mime_type="image/png",
        size_bytes=11 * _MB,
    )
    result = await pipeline.process(inp)
    assert result.success is False
    assert result.error is not None
