from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from agentic_core.application.ports.embedding_store import SearchResult
from agentic_core.domain.enums import EmbeddingTaskType
from agentic_core.domain.value_objects.multimodal import MultimodalContent
from agentic_core.rag.pipeline import Document, RAGPipeline, UnsupportedModalityError


def _mock_provider(modalities: list[str] | None = None) -> AsyncMock:
    provider = AsyncMock()
    provider.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
    provider.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    provider.embed_multimodal = AsyncMock(return_value=[0.7, 0.8, 0.9])
    provider.supported_modalities = modalities or ["text", "image"]
    provider.default_dimensions = 768
    return provider


def _mock_store() -> AsyncMock:
    store = AsyncMock()
    store.store = AsyncMock()
    store.search = AsyncMock(return_value=[
        SearchResult(score=0.95, metadata={"source": "doc1"}, text="hello world"),
    ])
    return store


async def test_ingest_simple():
    provider = _mock_provider()
    store = _mock_store()
    pipeline = RAGPipeline(provider, store, chunk_size=1000)

    docs = [Document(text="Hello world"), Document(text="Goodbye world")]
    count = await pipeline.ingest(docs)

    assert count == 2
    assert provider.embed_batch.await_count == 1
    assert store.store.await_count == 2


async def test_ingest_with_chunking():
    provider = _mock_provider()
    # Return enough embeddings for chunked text
    provider.embed_batch = AsyncMock(return_value=[[0.1] * 3] * 4)
    store = _mock_store()
    pipeline = RAGPipeline(provider, store, chunk_size=10, chunk_overlap=2)

    docs = [Document(text="A" * 25)]
    count = await pipeline.ingest(docs)

    # 25 chars, chunk_size=10, overlap=2: chunks at [0:10], [8:18], [16:26→25], [24:34→25]
    assert count == 4
    assert store.store.await_count == 4


async def test_ingest_empty():
    provider = _mock_provider()
    store = _mock_store()
    pipeline = RAGPipeline(provider, store)

    count = await pipeline.ingest([])
    assert count == 0


async def test_retrieve():
    provider = _mock_provider()
    store = _mock_store()
    pipeline = RAGPipeline(provider, store)

    results = await pipeline.retrieve("test query", top_k=3)

    provider.embed_text.assert_awaited_once()
    store.search.assert_awaited_once()
    assert len(results) == 1
    assert results[0].score == 0.95


async def test_retrieve_multimodal():
    provider = _mock_provider(modalities=["text", "image"])
    store = _mock_store()
    pipeline = RAGPipeline(provider, store)

    content = MultimodalContent(text="find similar")
    results = await pipeline.retrieve_multimodal(content)

    provider.embed_multimodal.assert_awaited_once()
    assert len(results) == 1


async def test_retrieve_multimodal_unsupported():
    provider = _mock_provider(modalities=["text"])  # No image support
    store = _mock_store()
    pipeline = RAGPipeline(provider, store)

    with pytest.raises(UnsupportedModalityError):
        await pipeline.retrieve_multimodal(MultimodalContent(text="hi"))
