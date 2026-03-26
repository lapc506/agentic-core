"""Integration tests for PostgresAdapter. Requires PostgreSQL at localhost:5499."""
from __future__ import annotations

import pytest

from agentic_core.adapters.secondary.postgres_adapter import PostgresAdapter
from agentic_core.domain.entities.session import Session
from agentic_core.domain.enums import SessionState
from tests.integration.conftest import POSTGRES_DSN, integration


@integration
class TestPostgresAdapter:
    @pytest.fixture
    async def adapter(self):
        a = PostgresAdapter(POSTGRES_DSN)
        await a.connect()
        # Clean tables
        async with a._pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_checkpoints")
            await conn.execute("DELETE FROM agent_sessions")
        yield a
        await a.close()

    async def test_create_and_get_session(self, adapter: PostgresAdapter):
        session = Session.create("test_s1", "support", "u1")
        await adapter.create(session)

        loaded = await adapter.get("test_s1")
        assert loaded is not None
        assert loaded.id == "test_s1"
        assert loaded.persona_id == "support"
        assert loaded.state == SessionState.ACTIVE

    async def test_update_session(self, adapter: PostgresAdapter):
        session = Session.create("test_s2", "support", "u1")
        await adapter.create(session)

        session.transition_to(SessionState.PAUSED)
        await adapter.update(session)

        loaded = await adapter.get("test_s2")
        assert loaded is not None
        assert loaded.state == SessionState.PAUSED

    async def test_get_nonexistent(self, adapter: PostgresAdapter):
        loaded = await adapter.get("nonexistent")
        assert loaded is None

    async def test_checkpoint_store_and_load(self, adapter: PostgresAdapter):
        session = Session.create("test_s3", "support", "u1")
        await adapter.create(session)

        data = b"checkpoint_binary_data_here"
        ckpt_id = await adapter.store_checkpoint("test_s3", data)
        assert ckpt_id is not None

        loaded = await adapter.load_checkpoint(ckpt_id)
        assert loaded == data

    async def test_checkpoint_not_found(self, adapter: PostgresAdapter):
        with pytest.raises(ValueError, match="not found"):
            await adapter.load_checkpoint("nonexistent_ckpt")
