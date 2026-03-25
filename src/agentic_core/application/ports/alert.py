from abc import ABC, abstractmethod
from typing import Any


class AlertPort(ABC):
    @abstractmethod
    async def fire(self, severity: str, summary: str, details: dict[str, Any]) -> None: ...
