from abc import ABC, abstractmethod
from typing import Any


class CostTrackingPort(ABC):
    @abstractmethod
    async def record_generation(
        self, model: str, input_tokens: int, output_tokens: int, metadata: dict[str, Any],
    ) -> None: ...
