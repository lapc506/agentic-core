from __future__ import annotations

import json
import logging
from typing import Any

from agentic_core.application.ports.embedding_store import EmbeddingStorePort, SearchResult

logger = logging.getLogger(__name__)


class PgVectorAdapter(EmbeddingStorePort):
    """pgvector-backed vector storage and similarity search."""

    def __init__(self, dsn: str, table_name: str = "agent_embeddings") -> None:
        self._dsn = dsn
        self._table = table_name
        self._pool: Any = None
        self._dimensions: int | None = None

    async def connect(self) -> None:
        import asyncpg
        self._pool = await asyncpg.create_pool(self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("pgvector connected: %s", self._dsn.split("@")[-1])

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()

    async def ensure_dimensions(self, dimensions: int) -> None:
        self._dimensions = dimensions
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id SERIAL PRIMARY KEY,
                    embedding vector({dimensions}),
                    metadata JSONB NOT NULL DEFAULT '{{}}',
                    text_content TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._table}_embedding
                ON {self._table} USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)

    async def store(self, embedding: list[float], metadata: dict[str, Any]) -> None:
        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
        text_content = metadata.pop("text", None)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""INSERT INTO {self._table} (embedding, metadata, text_content)
                    VALUES ($1::vector, $2, $3)""",
                vec_str, json.dumps(metadata), text_content,
            )

    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""SELECT metadata, text_content,
                           1 - (embedding <=> $1::vector) AS score
                    FROM {self._table}
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2""",
                vec_str, top_k,
            )
        return [
            SearchResult(
                score=float(row["score"]),
                metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
                text=row["text_content"],
            )
            for row in rows
        ]
