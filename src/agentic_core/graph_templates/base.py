from abc import ABC, abstractmethod
from typing import Any


class BaseAgentGraph(ABC):
    @abstractmethod
    def build_graph(self) -> Any:
        ...
