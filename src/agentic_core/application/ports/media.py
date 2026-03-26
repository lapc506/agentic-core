from __future__ import annotations

from abc import ABC, abstractmethod


class MediaPort(ABC):
    """Abstract port for media processing operations."""

    @abstractmethod
    async def describe_image(self, file_path: str, mime_type: str) -> str: ...

    @abstractmethod
    async def transcribe_audio(self, file_path: str, mime_type: str) -> str: ...

    @abstractmethod
    async def summarize_video(self, file_path: str, mime_type: str) -> str: ...
