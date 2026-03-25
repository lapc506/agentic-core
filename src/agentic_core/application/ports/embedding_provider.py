from abc import ABC, abstractmethod

from agentic_core.domain.enums import EmbeddingTaskType
from agentic_core.domain.value_objects.multimodal import MultimodalContent


class EmbeddingProviderPort(ABC):
    @abstractmethod
    async def embed_text(
        self, text: str, task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[float]: ...

    @abstractmethod
    async def embed_batch(
        self, texts: list[str], task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[list[float]]: ...

    @abstractmethod
    async def embed_multimodal(
        self, content: MultimodalContent,
        task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[float]: ...

    @property
    @abstractmethod
    def supported_modalities(self) -> list[str]: ...

    @property
    @abstractmethod
    def max_dimensions(self) -> int: ...

    @property
    @abstractmethod
    def default_dimensions(self) -> int: ...
