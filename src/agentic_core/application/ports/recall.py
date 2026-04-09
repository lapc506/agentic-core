from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import datetime


class RecallMatch(BaseModel, frozen=True):
    """A single cross-session search hit."""

    session_id: str
    content: str
    relevance_score: float
    timestamp: datetime


class RecallPort(ABC):
    """Abstract port for cross-session full-text search."""

    @abstractmethod
    async def search_sessions(
        self,
        query: str,
        persona_id: str | None = None,
        limit: int = 10,
    ) -> list[RecallMatch]: ...

    @abstractmethod
    async def store_message(
        self,
        session_id: str,
        persona_id: str,
        content: str,
        timestamp: datetime,
    ) -> None: ...
