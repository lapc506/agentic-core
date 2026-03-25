from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class GraphOrchestrationPort(ABC):
    @abstractmethod
    async def compile_graph(self, graph: Any, checkpoint_id: str | None = None) -> Any: ...

    @abstractmethod
    def stream_execution(self, compiled: Any, input_data: dict[str, Any]) -> AsyncIterator[Any]: ...
