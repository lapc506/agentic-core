"""HTTP Webhook adapter for receiving events from external systems.

Primary adapter that maps incoming webhook payloads to agent actions
via configurable route templates. Follows POST /hooks/<name> pattern
webhook adapter.

Usage:
    router = WebhookRouter()
    router.add_route(WebhookRoute(
        name="github-push",
        persona_id="devops-agent",
        template="New push to {payload[repository][name]}: {payload[head_commit][message]}",
    ))

    # On incoming POST /hooks/github-push:
    result = await router.handle("github-push", payload={...})
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WebhookRoute(BaseModel):
    name: str
    persona_id: str
    template: str
    secret: str | None = None
    enabled: bool = True
    allowed_sources: list[str] = []


@dataclass
class WebhookResult:
    accepted: bool
    message: str | None = None
    route_name: str | None = None
    error: str | None = None


WebhookCallback = Callable[[str, str, str], Awaitable[None]]


def verify_signature(
    payload_bytes: bytes, signature: str, secret: str,
    algorithm: str = "sha256",
) -> bool:
    """Verify HMAC signature for webhook payloads (GitHub, Stripe pattern)."""
    prefix = f"{algorithm}="
    if signature.startswith(prefix):
        signature = signature[len(prefix):]

    hash_func = getattr(hashlib, algorithm, None)
    if hash_func is None:
        return False

    expected = hmac.new(
        secret.encode(), payload_bytes, hash_func,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def render_template(template: str, payload: dict[str, Any]) -> str:
    """Render a message template with payload values.

    Supports dotted access: {payload[repository][name]}
    Falls back to repr of missing keys.
    """
    try:
        return template.format(payload=payload)
    except (KeyError, IndexError, AttributeError):
        return template


class WebhookRouter:
    """Routes incoming webhook payloads to agent personas."""

    def __init__(self, callback: WebhookCallback | None = None) -> None:
        self._routes: dict[str, WebhookRoute] = {}
        self._callback = callback

    def add_route(self, route: WebhookRoute) -> None:
        self._routes[route.name] = route

    def remove_route(self, name: str) -> None:
        self._routes.pop(name, None)

    def list_routes(self) -> list[WebhookRoute]:
        return list(self._routes.values())

    def get_route(self, name: str) -> WebhookRoute | None:
        return self._routes.get(name)

    async def handle(
        self,
        route_name: str,
        payload: dict[str, Any],
        *,
        payload_bytes: bytes | None = None,
        signature: str | None = None,
        source_ip: str | None = None,
    ) -> WebhookResult:
        route = self._routes.get(route_name)
        if route is None:
            return WebhookResult(
                accepted=False,
                error=f"Unknown route: {route_name!r}",
            )

        if not route.enabled:
            return WebhookResult(
                accepted=False,
                route_name=route_name,
                error="Route is disabled",
            )

        if route.allowed_sources and source_ip and source_ip not in route.allowed_sources:
            return WebhookResult(
                accepted=False,
                route_name=route_name,
                error="Source IP not allowed",
            )

        if route.secret and signature and payload_bytes:
            if not verify_signature(payload_bytes, signature, route.secret):
                return WebhookResult(
                    accepted=False,
                    route_name=route_name,
                    error="Invalid signature",
                )

        message = render_template(route.template, payload)

        if self._callback is not None:
            try:
                await self._callback(route.persona_id, message, route_name)
            except Exception:
                logger.exception("Webhook callback failed for '%s'", route_name)
                return WebhookResult(
                    accepted=False,
                    route_name=route_name,
                    error="Callback failed",
                )

        logger.info("Webhook '%s' accepted -> persona '%s'", route_name, route.persona_id)
        return WebhookResult(
            accepted=True,
            message=message,
            route_name=route_name,
        )
