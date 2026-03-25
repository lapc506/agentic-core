from __future__ import annotations

from pydantic import BaseModel


class MultimodalContent(BaseModel, frozen=True):
    text: str | None = None
    images: list[bytes] = []
    audio: bytes | None = None
    video: bytes | None = None
    pdf: bytes | None = None
