from __future__ import annotations

import json
import logging
from typing import Any

from agentic_core.application.ports.session import SessionPort
from agentic_core.domain.entities.session import Session
from agentic_core.domain.enums import SessionState

logger = logging.getLogger(__name__)


class PostgresAdapter(SessionPort):
    """PostgreSQL-backed session persistence using asyncpg."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Any = None

    async def connect(self) -> None:
        import asyncpg
        self._pool = await asyncpg.create_pool(self._dsn)
        await self._ensure_tables()
        logger.info("PostgreSQL connected: %s", self._dsn.split("@")[-1])

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            logger.info("PostgreSQL connection closed")

    async def _ensure_tables(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    id TEXT PRIMARY KEY,
                    persona_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'active',
                    checkpoint_id TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB NOT NULL DEFAULT '{}'
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_checkpoints (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES agent_sessions(id),
                    data BYTEA NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

    async def create(self, session: Session) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO agent_sessions (id, persona_id, user_id, state, checkpoint_id, created_at, updated_at, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                session.id, session.persona_id, session.user_id,
                session.state.value, session.checkpoint_id,
                session.created_at, session.updated_at,
                json.dumps(session.metadata),
            )

    async def get(self, session_id: str) -> Session | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_sessions WHERE id = $1", session_id
            )
            if row is None:
                return None
            return Session(
                id=row["id"],
                persona_id=row["persona_id"],
                user_id=row["user_id"],
                state=SessionState(row["state"]),
                checkpoint_id=row["checkpoint_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
            )

    async def update(self, session: Session) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """UPDATE agent_sessions SET state=$2, checkpoint_id=$3, updated_at=$4, metadata=$5
                   WHERE id=$1""",
                session.id, session.state.value, session.checkpoint_id,
                session.updated_at, json.dumps(session.metadata),
            )

    async def store_checkpoint(self, session_id: str, checkpoint_data: bytes) -> str:
        import uuid_utils
        checkpoint_id = str(uuid_utils.uuid7())
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO agent_checkpoints (id, session_id, data) VALUES ($1, $2, $3)""",
                checkpoint_id, session_id, checkpoint_data,
            )
            await conn.execute(
                "UPDATE agent_sessions SET checkpoint_id=$2 WHERE id=$1",
                session_id, checkpoint_id,
            )
        return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> bytes:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM agent_checkpoints WHERE id = $1", checkpoint_id
            )
            if row is None:
                raise ValueError(f"Checkpoint {checkpoint_id} not found")
            return bytes(row["data"])
