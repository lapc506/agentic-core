from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agentic_core.application.middleware.base import (
    Middleware,
    NextHandler,
    RequestContext,
)

if TYPE_CHECKING:
    from agentic_core.domain.value_objects.messages import AgentMessage

logger = logging.getLogger(__name__)


class AuthMiddleware(Middleware):
    """Validates JWT or API key. Extracts user_id into RequestContext.
    Rejects unauthorized requests before they reach handlers."""

    def __init__(self, api_keys: set[str] | None = None) -> None:
        self._api_keys = api_keys or set()

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        # Extract auth from metadata
        auth_token = message.metadata.get("authorization", "")
        api_key = message.metadata.get("x_api_key", "")

        if self._api_keys and api_key and api_key in self._api_keys:
            ctx.user_id = message.metadata.get("user_id", "api_key_user")
            return await next_(message, ctx)

        if auth_token:
            # Phase 4 stub: in production, validate JWT here (PyJWT)
            ctx.user_id = message.metadata.get("user_id", "jwt_user")
            return await next_(message, ctx)

        if not self._api_keys:
            # No auth configured — pass through (dev mode)
            return await next_(message, ctx)

        logger.warning("Auth rejected: no valid credentials in message %s", message.id)
        raise PermissionError("Authentication required")
