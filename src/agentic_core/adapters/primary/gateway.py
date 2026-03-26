"""Platform gateway adapters for Telegram, Discord, Slack, WhatsApp, Signal.

Primary adapters that normalise inbound messages from messaging platforms
into a unified callback pattern, matching WebSocket/gRPC/CLI conventions.

Usage:
    adapter = GatewayAdapter(
        configs=[GatewayConfig(platform=GatewayPlatform.TELEGRAM, token="...")],
        callback=my_handler,
    )
    await adapter.start()
    response = await adapter.handle_inbound(msg)
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GatewayPlatform(Enum):
    """Supported messaging platforms."""

    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    SIGNAL = "signal"


class GatewayConfig(BaseModel):
    """Configuration for a single platform gateway."""

    platform: GatewayPlatform
    token: str | None = None
    webhook_url: str | None = None
    enabled: bool = True


class InboundMessage(BaseModel, frozen=True):
    """Immutable inbound message from a messaging platform."""

    platform: GatewayPlatform
    channel_id: str
    user_id: str
    content: str
    media_url: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutboundMessage(BaseModel, frozen=True):
    """Immutable outbound message to a messaging platform."""

    platform: GatewayPlatform
    channel_id: str
    content: str
    reply_to: str | None = None


GatewayCallback = Callable[[InboundMessage], Awaitable[OutboundMessage | None]]


class GatewayAdapter:
    """Unified adapter that manages gateway connections for messaging platforms."""

    def __init__(
        self,
        configs: list[GatewayConfig],
        callback: GatewayCallback | None = None,
    ) -> None:
        self._configs = {cfg.platform: cfg for cfg in configs}
        self._callback = callback
        self._running = False

    async def start(self) -> None:
        """Start the gateway adapter and connect enabled platforms."""
        self._running = True
        for platform, cfg in self._configs.items():
            if cfg.enabled:
                logger.info(
                    "Gateway started for %s (webhook=%s)",
                    platform.value,
                    cfg.webhook_url or "polling",
                )

    async def stop(self) -> None:
        """Stop the gateway adapter and disconnect all platforms."""
        self._running = False
        logger.info("Gateway adapter stopped")

    @property
    def is_running(self) -> bool:
        """Return whether the adapter is currently running."""
        return self._running

    async def send(self, msg: OutboundMessage) -> bool:
        """Send an outbound message to the target platform (placeholder).

        Returns True if the platform is configured and enabled, False otherwise.
        """
        cfg = self._configs.get(msg.platform)
        if cfg is None or not cfg.enabled:
            logger.warning(
                "Cannot send to %s: not configured or disabled", msg.platform.value,
            )
            return False

        logger.info(
            "Outbound [%s] -> channel=%s: %s",
            msg.platform.value,
            msg.channel_id,
            msg.content[:80],
        )
        return True

    async def handle_inbound(self, msg: InboundMessage) -> OutboundMessage | None:
        """Process an inbound message through the registered callback."""
        cfg = self._configs.get(msg.platform)
        if cfg is None or not cfg.enabled:
            logger.warning(
                "Inbound from %s ignored: not configured or disabled",
                msg.platform.value,
            )
            return None

        if self._callback is None:
            logger.debug("No callback registered, dropping inbound from %s", msg.platform.value)
            return None

        try:
            return await self._callback(msg)
        except Exception:
            logger.exception(
                "Callback failed for inbound from %s channel=%s",
                msg.platform.value,
                msg.channel_id,
            )
            return None

    def active_platforms(self) -> list[GatewayPlatform]:
        """List platforms that are configured and enabled."""
        return [
            platform
            for platform, cfg in self._configs.items()
            if cfg.enabled
        ]


class GatewayRegistry:
    """Singleton-like registry for platform gateway adapters."""

    _instance: ClassVar[GatewayRegistry | None] = None

    def __init__(self) -> None:
        self._adapters: dict[GatewayPlatform, GatewayAdapter] = {}

    @classmethod
    def get_instance(cls) -> GatewayRegistry:
        """Return the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    def register(self, platform: GatewayPlatform, adapter: GatewayAdapter) -> None:
        """Register an adapter for a platform."""
        self._adapters[platform] = adapter
        logger.info("Registered gateway adapter for %s", platform.value)

    def get(self, platform: GatewayPlatform) -> GatewayAdapter | None:
        """Get the adapter for a platform."""
        return self._adapters.get(platform)

    def list_all(self) -> dict[GatewayPlatform, GatewayAdapter]:
        """List all registered adapters."""
        return dict(self._adapters)
