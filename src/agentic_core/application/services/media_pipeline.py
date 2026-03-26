from __future__ import annotations

import logging
from enum import Enum

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MediaType(str, Enum):
    """Supported media types for the processing pipeline."""

    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


_MB = 1024 * 1024

_DEFAULT_MAX_BYTES: dict[MediaType, int] = {
    MediaType.IMAGE: 10 * _MB,
    MediaType.AUDIO: 25 * _MB,
    MediaType.VIDEO: 100 * _MB,
}

_DEFAULT_ALLOWED_FORMATS: dict[MediaType, frozenset[str]] = {
    MediaType.IMAGE: frozenset({"jpg", "jpeg", "png", "gif", "webp"}),
    MediaType.AUDIO: frozenset({"mp3", "wav", "ogg", "m4a", "webm"}),
    MediaType.VIDEO: frozenset({"mp4", "webm", "mov"}),
}

_DEFAULT_MODELS: dict[MediaType, str] = {
    MediaType.IMAGE: "gpt-4o",
    MediaType.AUDIO: "whisper-1",
    MediaType.VIDEO: "gemini-1.5-pro",
}


class MediaConfig(BaseModel):
    """Configuration for the media processing pipeline."""

    max_bytes: dict[MediaType, int] = dict(_DEFAULT_MAX_BYTES)
    allowed_formats: dict[MediaType, frozenset[str]] = dict(_DEFAULT_ALLOWED_FORMATS)
    default_model: dict[MediaType, str] = dict(_DEFAULT_MODELS)


class MediaInput(BaseModel, frozen=True):
    """Validated input for a media processing request."""

    media_type: MediaType
    file_path: str
    mime_type: str
    size_bytes: int


class MediaResult(BaseModel, frozen=True):
    """Result of a media processing operation."""

    success: bool
    media_type: MediaType
    content: str
    error: str | None = None


class MediaPipeline:
    """Process media content: image description, audio transcription, video summarization.

    Routes to the appropriate handler based on media type.
    Validates byte limits and format constraints before processing.
    """

    def __init__(self, config: MediaConfig | None = None) -> None:
        self._config = config or MediaConfig()

    def validate(self, media_input: MediaInput) -> MediaResult | None:
        """Validate size and format constraints.

        Returns an error ``MediaResult`` when validation fails, or ``None``
        when the input is valid.
        """
        max_bytes = self._config.max_bytes.get(media_input.media_type, 0)
        if media_input.size_bytes > max_bytes:
            return MediaResult(
                success=False,
                media_type=media_input.media_type,
                content="",
                error=(
                    f"File size {media_input.size_bytes} bytes exceeds "
                    f"limit of {max_bytes} bytes for {media_input.media_type.value}"
                ),
            )

        allowed = self._config.allowed_formats.get(
            media_input.media_type, frozenset(),
        )
        extension = media_input.mime_type.rsplit("/", 1)[-1].lower()
        if extension not in allowed:
            return MediaResult(
                success=False,
                media_type=media_input.media_type,
                content="",
                error=(
                    f"Format '{extension}' is not allowed for "
                    f"{media_input.media_type.value}. "
                    f"Allowed: {sorted(allowed)}"
                ),
            )

        return None

    async def process(self, media_input: MediaInput) -> MediaResult:
        """Validate and process a media input, dispatching to the correct handler."""
        validation_error = self.validate(media_input)
        if validation_error is not None:
            return validation_error

        handler = {
            MediaType.IMAGE: self._process_image,
            MediaType.AUDIO: self._process_audio,
            MediaType.VIDEO: self._process_video,
        }.get(media_input.media_type)

        if handler is None:
            return MediaResult(
                success=False,
                media_type=media_input.media_type,
                content="",
                error=f"No handler for media type: {media_input.media_type.value}",
            )

        return await handler(media_input)

    async def _process_image(self, media_input: MediaInput) -> MediaResult:
        """Process an image file (placeholder for real model integration)."""
        model = self._config.default_model.get(MediaType.IMAGE, "unknown")
        logger.info(
            "Processing image %s with model %s", media_input.file_path, model,
        )
        return MediaResult(
            success=True,
            media_type=MediaType.IMAGE,
            content=f"[Image description placeholder for {media_input.file_path}]",
        )

    async def _process_audio(self, media_input: MediaInput) -> MediaResult:
        """Process an audio file (placeholder for real model integration)."""
        model = self._config.default_model.get(MediaType.AUDIO, "unknown")
        logger.info(
            "Processing audio %s with model %s", media_input.file_path, model,
        )
        return MediaResult(
            success=True,
            media_type=MediaType.AUDIO,
            content=f"[Audio transcription placeholder for {media_input.file_path}]",
        )

    async def _process_video(self, media_input: MediaInput) -> MediaResult:
        """Process a video file (placeholder for real model integration)."""
        model = self._config.default_model.get(MediaType.VIDEO, "unknown")
        logger.info(
            "Processing video %s with model %s", media_input.file_path, model,
        )
        return MediaResult(
            success=True,
            media_type=MediaType.VIDEO,
            content=f"[Video summary placeholder for {media_input.file_path}]",
        )
