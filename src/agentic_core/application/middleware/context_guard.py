"""#50: Context window overflow guard. Validates message fits within model limits."""
from __future__ import annotations

import logging

from agentic_core.application.middleware.base import (
    Middleware,
    NextHandler,
    RequestContext,
)
from agentic_core.domain.value_objects.messages import AgentMessage

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONTENT_TOKENS = 128_000


class ContextGuardMiddleware(Middleware):
    """Rejects messages whose content exceeds the configured token limit.
    Prevents context window overflow that causes LLM completion failures."""

    def __init__(self, max_content_tokens: int = DEFAULT_MAX_CONTENT_TOKENS) -> None:
        self._max_tokens = max_content_tokens

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        estimated_tokens = len(message.content) // 4
        if estimated_tokens > self._max_tokens:
            logger.warning(
                "Message content exceeds token limit: ~%d tokens > %d max (session=%s)",
                estimated_tokens, self._max_tokens, message.session_id,
            )
            raise ValueError(
                f"Message too large: ~{estimated_tokens} tokens exceeds {self._max_tokens} limit"
            )
        return await next_(message, ctx)
