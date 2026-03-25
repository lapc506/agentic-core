from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class SearchResult(BaseModel, frozen=True):
    score: float
    metadata: dict[str, Any]
    text: str | None = None


class EmbeddingStorePort(ABC):
    @abstractmethod
    async def store(self, embedding: list[float], metadata: dict[str, Any]) -> None: ...

    @abstractmethod
    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]: ...

    @abstractmethod
    async def ensure_dimensions(self, dimensions: int) -> None: ...
