from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import jwt

from agentic_core.application.middleware.base import (
    Middleware,
    NextHandler,
    RequestContext,
)

if TYPE_CHECKING:
    from agentic_core.domain.value_objects.messages import AgentMessage

logger = logging.getLogger(__name__)

# Default secret; override via AGENTIC_JWT_SECRET env var in production.
_DEFAULT_JWT_SECRET = "change-me-in-production"


class AuthMiddleware(Middleware):
    """Validates JWT or API key. Extracts user_id into RequestContext.
    Rejects unauthorized requests before they reach handlers."""

    def __init__(
        self,
        api_keys: set[str] | None = None,
        jwt_secret: str | None = None,
        jwt_algorithm: str = "HS256",
    ) -> None:
        self._api_keys = api_keys or set()
        self._jwt_secret = jwt_secret or os.environ.get(
            "AGENTIC_JWT_SECRET", _DEFAULT_JWT_SECRET,
        )
        self._jwt_algorithm = jwt_algorithm
        self._auth_bypass = os.environ.get("AGENTIC_AUTH_BYPASS", "").lower() == "true"

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        # Development bypass -- only when explicitly opted-in via env var
        if self._auth_bypass:
            ctx.user_id = message.metadata.get("user_id", "bypass_user")
            return await next_(message, ctx)

        # Extract auth from metadata
        auth_token = message.metadata.get("authorization", "")
        api_key = message.metadata.get("x_api_key", "")

        if self._api_keys and api_key and api_key in self._api_keys:
            ctx.user_id = message.metadata.get("user_id", "api_key_user")
            return await next_(message, ctx)

        if auth_token:
            token = auth_token.removeprefix("Bearer ").strip()
            ctx.user_id = self._validate_jwt(token)
            return await next_(message, ctx)

        if not self._api_keys:
            # No auth configured — pass through (dev mode)
            return await next_(message, ctx)

        logger.warning("Auth rejected: no valid credentials in message %s", message.id)
        raise PermissionError("Authentication required")

    def _validate_jwt(self, token: str) -> str:
        """Decode and validate a JWT token. Returns the user_id claim."""
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm],
                options={"require": ["exp", "user_id"]},
            )
        except jwt.ExpiredSignatureError:
            raise PermissionError("Token expired")
        except jwt.InvalidTokenError as exc:
            raise PermissionError(f"Invalid token: {exc}")

        user_id: str | None = payload.get("user_id")
        if not user_id:
            raise PermissionError("Token missing user_id claim")
        return user_id
