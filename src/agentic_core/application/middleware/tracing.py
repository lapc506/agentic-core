from __future__ import annotations

from typing import TYPE_CHECKING

import uuid_utils

from agentic_core.application.middleware.base import (
    Middleware,
    NextHandler,
    RequestContext,
)

if TYPE_CHECKING:
    from agentic_core.application.ports.tracing import TracingPort
    from agentic_core.domain.value_objects.messages import AgentMessage


class TracingMiddleware(Middleware):
    """Injects trace_id and creates spans. Falls back to no-op if tracing_port is None."""

    def __init__(self, tracing_port: TracingPort | None = None) -> None:
        self._tracing = tracing_port

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        # Ensure trace_id exists
        if ctx.trace_id is None:
            ctx.trace_id = str(uuid_utils.uuid7())

        span = None
        if self._tracing is not None:
            span = self._tracing.start_span(
                "handle_message",
                attributes={
                    "session_id": ctx.session_id or "",
                    "persona_id": ctx.persona_id or "",
                },
            )

        try:
            result = await next_(message, ctx)
            return result
        finally:
            if self._tracing is not None and span is not None:
                self._tracing.end_span(span)
