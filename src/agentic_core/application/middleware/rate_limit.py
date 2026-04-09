from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from agentic_core.application.middleware.base import (
    Middleware,
    NextHandler,
    RequestContext,
)

if TYPE_CHECKING:
    from agentic_core.domain.value_objects.messages import AgentMessage

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    pass


class RateLimitMiddleware(Middleware):
    """Token bucket rate limiter per user/session. In-memory for Phase 4.
    Phase 2+ can back this with Redis for distributed rate limiting."""

    def __init__(self, requests_per_minute: int = 60) -> None:
        self._rpm = requests_per_minute
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        key = ctx.user_id or ctx.session_id or "anonymous"
        now = time.monotonic()

        # Evict old entries (older than 60s)
        bucket = self._buckets[key]
        self._buckets[key] = [t for t in bucket if now - t < 60.0]

        if len(self._buckets[key]) >= self._rpm:
            logger.warning("Rate limit exceeded for %s (%d rpm)", key, self._rpm)
            raise RateLimitExceeded(f"Rate limit exceeded: {self._rpm} requests/minute")

        self._buckets[key].append(now)
        return await next_(message, ctx)
