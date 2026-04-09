"""OpenAI text-embedding-3-large adapter. Text-only."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agentic_core.application.ports.embedding_provider import EmbeddingProviderPort

if TYPE_CHECKING:
    from agentic_core.config.settings import EmbeddingProviderSettings
    from agentic_core.domain.enums import EmbeddingTaskType
    from agentic_core.domain.value_objects.multimodal import MultimodalContent

logger = logging.getLogger(__name__)


class OpenAIEmbeddingAdapter(EmbeddingProviderPort):
    """OpenAI text-embedding-3-large. Text only, no multimodal."""

    def __init__(self, settings: EmbeddingProviderSettings) -> None:
        self._settings = settings
        self._client: Any = None
        self._model = settings.openai_embedding_model

    async def connect(self) -> None:
        try:
            import openai
            self._client = openai.AsyncOpenAI(api_key=self._settings.openai_api_key)
            logger.info("OpenAI Embedding connected: model=%s", self._model)
        except ImportError:
            logger.warning("openai package not installed")

    async def embed_text(
        self, text: str, task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[float]:
        if self._client is None:
            raise RuntimeError("OpenAI client not connected")
        kwargs: dict[str, Any] = {"model": self._model, "input": text}
        if dimensions:
            kwargs["dimensions"] = dimensions
        resp = await self._client.embeddings.create(**kwargs)
        return list(resp.data[0].embedding)

    async def embed_batch(
        self, texts: list[str], task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[list[float]]:
        if self._client is None:
            raise RuntimeError("OpenAI client not connected")
        kwargs: dict[str, Any] = {"model": self._model, "input": texts}
        if dimensions:
            kwargs["dimensions"] = dimensions
        resp = await self._client.embeddings.create(**kwargs)
        return [list(d.embedding) for d in resp.data]

    async def embed_multimodal(
        self, content: MultimodalContent,
        task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[float]:
        raise NotImplementedError("OpenAI embeddings are text-only")

    @property
    def supported_modalities(self) -> list[str]:
        return ["text"]

    @property
    def max_dimensions(self) -> int:
        return 3072

    @property
    def default_dimensions(self) -> int:
        return self._settings.embedding_dimensions
