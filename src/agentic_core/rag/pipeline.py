from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agentic_core.domain.enums import EmbeddingTaskType

if TYPE_CHECKING:
    from agentic_core.application.ports.embedding_provider import EmbeddingProviderPort
    from agentic_core.application.ports.embedding_store import EmbeddingStorePort, SearchResult
    from agentic_core.domain.value_objects.multimodal import MultimodalContent

logger = logging.getLogger(__name__)


class UnsupportedModalityError(Exception):
    pass


@dataclass
class Document:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    image: bytes | None = None


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class RAGPipeline:
    """Modular pipeline: ingest -> chunk -> embed -> store -> retrieve -> rerank.
    Provider-agnostic: works with any EmbeddingProviderPort + EmbeddingStorePort."""

    def __init__(
        self,
        embedding_provider: EmbeddingProviderPort,
        embedding_store: EmbeddingStorePort,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> None:
        self._provider = embedding_provider
        self._store = embedding_store
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def ingest(
        self,
        documents: list[Document],
        task_type: EmbeddingTaskType = EmbeddingTaskType.RETRIEVAL_DOCUMENT,
    ) -> int:
        chunks = self._chunk(documents)
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        embeddings = await self._provider.embed_batch(texts, task_type=task_type)

        for chunk, embedding in zip(chunks, embeddings, strict=False):
            meta = {**chunk.metadata, "text": chunk.text}
            await self._store.store(embedding, metadata=meta)

        logger.info("Ingested %d chunks from %d documents", len(chunks), len(documents))
        return len(chunks)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        task_type: EmbeddingTaskType = EmbeddingTaskType.RETRIEVAL_QUERY,
    ) -> list[SearchResult]:
        query_embedding = await self._provider.embed_text(query, task_type=task_type)
        return await self._store.search(query_embedding, top_k=top_k)

    async def retrieve_multimodal(
        self,
        content: MultimodalContent,
        top_k: int = 5,
    ) -> list[SearchResult]:
        if "image" not in self._provider.supported_modalities:
            raise UnsupportedModalityError("Provider does not support multimodal search")
        query_embedding = await self._provider.embed_multimodal(content)
        return await self._store.search(query_embedding, top_k=top_k)

    def _chunk(self, documents: list[Document]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for doc in documents:
            text = doc.text
            if len(text) <= self._chunk_size:
                chunks.append(Chunk(text=text, metadata=doc.metadata))
            else:
                start = 0
                while start < len(text):
                    end = start + self._chunk_size
                    chunk_text = text[start:end]
                    chunks.append(Chunk(text=chunk_text, metadata=doc.metadata))
                    start = end - self._chunk_overlap
                    if start >= len(text):
                        break
        return chunks
