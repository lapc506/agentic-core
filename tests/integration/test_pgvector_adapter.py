"""Integration tests for PgVectorAdapter. Requires PostgreSQL+pgvector at localhost:5499."""
from __future__ import annotations

import pytest

from agentic_core.adapters.secondary.pgvector_adapter import PgVectorAdapter
from tests.integration.conftest import POSTGRES_DSN, integration


@integration
class TestPgVectorAdapter:
    @pytest.fixture
    async def adapter(self):
        a = PgVectorAdapter(POSTGRES_DSN, table_name="test_embeddings")
        await a.connect()
        await a.ensure_dimensions(3)
        async with a._pool.acquire() as conn:
            await conn.execute("DELETE FROM test_embeddings")
        yield a
        await a.close()

    async def test_store_and_search(self, adapter: PgVectorAdapter):
        await adapter.store([1.0, 0.0, 0.0], {"source": "doc1", "text": "hello world"})
        await adapter.store([0.0, 1.0, 0.0], {"source": "doc2", "text": "goodbye world"})
        await adapter.store([0.9, 0.1, 0.0], {"source": "doc3", "text": "hi there"})

        results = await adapter.search([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0].score > results[1].score
        assert results[0].metadata["source"] == "doc1"

    async def test_search_empty(self, adapter: PgVectorAdapter):
        results = await adapter.search([1.0, 0.0, 0.0], top_k=5)
        assert results == []

    async def test_text_content_stored(self, adapter: PgVectorAdapter):
        await adapter.store([0.5, 0.5, 0.0], {"text": "stored text", "tag": "test"})
        results = await adapter.search([0.5, 0.5, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0].text == "stored text"
