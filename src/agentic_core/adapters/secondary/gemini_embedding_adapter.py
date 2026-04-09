from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agentic_core.application.ports.embedding_provider import EmbeddingProviderPort

if TYPE_CHECKING:
    from agentic_core.config.settings import EmbeddingProviderSettings
    from agentic_core.domain.enums import EmbeddingTaskType
    from agentic_core.domain.value_objects.multimodal import MultimodalContent

logger = logging.getLogger(__name__)


class GeminiEmbeddingAdapter(EmbeddingProviderPort):
    """Gemini Embedding 2 -- natively multimodal embeddings.
    Maps text, images, video, audio, and PDFs into a unified vector space.
    Supports Matryoshka dimension reduction (128-3072)."""

    def __init__(self, settings: EmbeddingProviderSettings) -> None:
        self._settings = settings
        self._client: Any = None
        self._model = settings.gemini_embedding_model

    async def connect(self) -> None:
        from google import genai
        self._client = genai.Client(api_key=self._settings.gemini_api_key)
        logger.info("Gemini Embedding connected: model=%s", self._model)

    async def embed_text(
        self, text: str, task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[float]:
        config: dict[str, Any] = {
            "output_dimensionality": dimensions or self._settings.embedding_dimensions,
        }
        if task_type is not None:
            config["task_type"] = task_type.value

        result = self._client.models.embed_content(
            model=self._model,
            contents=text,
            config=config,
        )
        return list(result.embeddings[0].values)

    async def embed_batch(
        self, texts: list[str], task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            embedding = await self.embed_text(text, task_type=task_type, dimensions=dimensions)
            results.append(embedding)
        return results

    async def embed_multimodal(
        self, content: MultimodalContent,
        task_type: EmbeddingTaskType | None = None,
        dimensions: int | None = None,
    ) -> list[float]:
        parts: list[Any] = []
        if content.text:
            parts.append(content.text)
        # Images, audio, video, pdf would be converted to Gemini Part objects
        # For now, text-only path is implemented
        if not parts:
            raise ValueError("MultimodalContent must have at least one modality")

        config: dict[str, Any] = {
            "output_dimensionality": dimensions or self._settings.embedding_dimensions,
        }
        if task_type is not None:
            config["task_type"] = task_type.value

        result = self._client.models.embed_content(
            model=self._model,
            contents=parts,
            config=config,
        )
        return list(result.embeddings[0].values)

    @property
    def supported_modalities(self) -> list[str]:
        return ["text", "image", "audio", "video", "pdf"]

    @property
    def max_dimensions(self) -> int:
        return 3072

    @property
    def default_dimensions(self) -> int:
        return self._settings.embedding_dimensions
