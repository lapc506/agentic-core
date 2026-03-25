from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from agentic_core.application.ports.memory import MemoryPort
from agentic_core.domain.value_objects.messages import AgentMessage

logger = logging.getLogger(__name__)

# Conversation TTL: 24 hours by default
DEFAULT_CONVERSATION_TTL = 86400


class RedisAdapter(MemoryPort):
    """Redis-backed conversation memory. Uses sorted sets keyed by session_id.
    Messages scored by timestamp for ordered retrieval."""

    def __init__(self, redis_url: str, conversation_ttl: int = DEFAULT_CONVERSATION_TTL) -> None:
        self._redis_url = redis_url
        self._ttl = conversation_ttl
        self._client: Any = None

    async def connect(self) -> None:
        import redis.asyncio as aioredis
        self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        logger.info("Redis connected: %s", self._redis_url)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            logger.info("Redis connection closed")

    def _key(self, session_id: str) -> str:
        return f"agentic:conv:{session_id}"

    async def store_message(self, message: AgentMessage) -> None:
        key = self._key(message.session_id)
        score = message.timestamp.timestamp()
        value = message.model_dump_json()
        await self._client.zadd(key, {value: score})
        await self._client.expire(key, self._ttl)

    async def get_messages(self, session_id: str, limit: int = 50) -> list[AgentMessage]:
        key = self._key(session_id)
        raw_messages = await self._client.zrevrange(key, 0, limit - 1)
        messages = [AgentMessage.model_validate_json(raw) for raw in reversed(raw_messages)]
        return messages

    async def get_context_window(self, session_id: str, max_tokens: int) -> list[AgentMessage]:
        messages = await self.get_messages(session_id, limit=200)
        result: list[AgentMessage] = []
        token_count = 0
        for msg in reversed(messages):
            estimated_tokens = len(msg.content) // 4
            if token_count + estimated_tokens > max_tokens:
                break
            result.insert(0, msg)
            token_count += estimated_tokens
        return result
