"""Local sentence-transformers embedding adapter. Offline, text-only."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agentic_core.application.ports.embedding_provider import EmbeddingProviderPort

if TYPE_CHECKING:
    from agentic_core.config.settings import EmbeddingProviderSettings
    from agentic_core.domain.enums import EmbeddingTaskType
    from agentic_core.domain.value_objects.multimodal import MultimodalContent

logger = logging.getLogger(__name__)


class LocalEmbeddingAdapter(EmbeddingProviderPort):
    """sentence-transformers local model. Offline, text-only, no API key needed."""

    def __init__(self, settings: EmbeddingProviderSettings) -> None:
        self._settings = settings
        self._model: Any = None
        self._model_name = settings.local_model_name

    async def connect(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            logger.info("Local embedding model loaded: %s", self._model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed")

    async def embed_text(
        self, text: str, task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[float]:
        if self._model is None:
            raise RuntimeError("Local model not loaded")
        embedding = self._model.encode(text, normalize_embeddings=True)
        result = embedding.tolist()
        if dimensions and dimensions < len(result):
            result = result[:dimensions]
        return result

    async def embed_batch(
        self, texts: list[str], task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[list[float]]:
        if self._model is None:
            raise RuntimeError("Local model not loaded")
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        results = [e.tolist() for e in embeddings]
        if dimensions:
            results = [r[:dimensions] for r in results]
        return results

    async def embed_multimodal(
        self, content: MultimodalContent,
        task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[float]:
        raise NotImplementedError("Local embeddings are text-only")

    @property
    def supported_modalities(self) -> list[str]:
        return ["text"]

    @property
    def max_dimensions(self) -> int:
        return 384  # all-MiniLM-L6-v2 default

    @property
    def default_dimensions(self) -> int:
        return self._settings.embedding_dimensions
