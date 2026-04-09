"""Integration tests for RedisAdapter. Requires Redis at localhost:6399."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import uuid_utils

from agentic_core.adapters.secondary.redis_adapter import RedisAdapter
from agentic_core.domain.value_objects.messages import AgentMessage
from tests.integration.conftest import REDIS_URL, integration


def _msg(session_id: str = "s1", content: str = "hello") -> AgentMessage:
    return AgentMessage(
        id=str(uuid_utils.uuid7()),
        session_id=session_id,
        persona_id="test",
        role="user",
        content=content,
        metadata={},
        timestamp=datetime.now(UTC),
    )


@integration
class TestRedisAdapter:
    @pytest.fixture
    async def adapter(self):
        a = RedisAdapter(REDIS_URL, conversation_ttl=60)
        await a.connect()
        yield a
        # Cleanup
        await a._client.flushdb()
        await a.close()

    async def test_store_and_get_messages(self, adapter: RedisAdapter):
        msg1 = _msg(content="first")
        msg2 = _msg(content="second")
        await adapter.store_message(msg1)
        await adapter.store_message(msg2)

        messages = await adapter.get_messages("s1", limit=10)
        assert len(messages) == 2
        assert messages[0].content == "first"
        assert messages[1].content == "second"

    async def test_get_messages_with_limit(self, adapter: RedisAdapter):
        for i in range(10):
            await adapter.store_message(_msg(content=f"msg_{i}"))

        messages = await adapter.get_messages("s1", limit=3)
        assert len(messages) == 3

    async def test_context_window(self, adapter: RedisAdapter):
        for _i in range(5):
            await adapter.store_message(_msg(content="x" * 100))

        # Each msg ~25 tokens (100 chars / 4), max_tokens=60 should fit ~2
        messages = await adapter.get_context_window("s1", max_tokens=60)
        assert len(messages) <= 3

    async def test_separate_sessions(self, adapter: RedisAdapter):
        await adapter.store_message(_msg(session_id="a", content="session_a"))
        await adapter.store_message(_msg(session_id="b", content="session_b"))

        msgs_a = await adapter.get_messages("a")
        msgs_b = await adapter.get_messages("b")
        assert len(msgs_a) == 1
        assert len(msgs_b) == 1
        assert msgs_a[0].content == "session_a"
