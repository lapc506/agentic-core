from abc import ABC, abstractmethod
from typing import Any


class TracingPort(ABC):
    @abstractmethod
    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Any: ...

    @abstractmethod
    def end_span(self, span: Any) -> None: ...
