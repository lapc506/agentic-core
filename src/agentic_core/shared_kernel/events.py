from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DomainEvent(BaseModel, frozen=True):
    timestamp: datetime
    trace_id: str | None = None


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[
            type[DomainEvent], list[Callable[[DomainEvent], Awaitable[None]]]
        ] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], Awaitable[None]],
    ) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            try:
                await handler(event)
            except Exception:
                logger.exception("Handler failed for %s", type(event).__name__)
