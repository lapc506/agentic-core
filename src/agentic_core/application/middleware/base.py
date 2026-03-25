from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agentic_core.domain.value_objects.messages import AgentMessage


@dataclass
class RequestContext:
    trace_id: str | None = None
    session_id: str | None = None
    persona_id: str | None = None
    user_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extra: dict[str, Any] = field(default_factory=dict)


NextHandler = Callable[[AgentMessage, RequestContext], Awaitable[AgentMessage]]


class Middleware(ABC):
    @abstractmethod
    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage: ...


class MiddlewareChain:
    def __init__(self, middlewares: list[Middleware], handler: NextHandler) -> None:
        self._chain = self._build(middlewares, handler)

    def _build(self, middlewares: list[Middleware], handler: NextHandler) -> NextHandler:
        current = handler
        for mw in reversed(middlewares):
            current = self._wrap(mw, current)
        return current

    @staticmethod
    def _wrap(mw: Middleware, next_: NextHandler) -> NextHandler:
        async def wrapped(message: AgentMessage, ctx: RequestContext) -> AgentMessage:
            return await mw.process(message, ctx, next_)
        return wrapped

    async def __call__(self, message: AgentMessage, ctx: RequestContext) -> AgentMessage:
        return await self._chain(message, ctx)
