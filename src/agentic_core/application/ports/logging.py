from abc import ABC, abstractmethod
from typing import Any


class LoggingPort(ABC):
    @abstractmethod
    def bind_context(self, **kwargs: Any) -> None: ...

    @abstractmethod
    def log(self, level: str, event: str, **kwargs: Any) -> None: ...
