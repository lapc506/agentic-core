from abc import ABC, abstractmethod
from typing import Any


class GraphStorePort(ABC):
    @abstractmethod
    async def store_entity(self, entity: dict[str, Any], relations: list[dict[str, Any]]) -> None: ...

    @abstractmethod
    async def query(self, cypher: str) -> list[dict[str, Any]]: ...
