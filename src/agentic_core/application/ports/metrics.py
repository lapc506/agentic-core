from abc import ABC, abstractmethod


class MetricsPort(ABC):
    @abstractmethod
    def increment_counter(self, name: str, labels: dict[str, str], value: float = 1) -> None: ...

    @abstractmethod
    def observe_histogram(self, name: str, labels: dict[str, str], value: float) -> None: ...
