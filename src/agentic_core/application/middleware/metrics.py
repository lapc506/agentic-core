from __future__ import annotations

import time
from typing import TYPE_CHECKING

from agentic_core.application.middleware.base import (
    Middleware,
    NextHandler,
    RequestContext,
)

if TYPE_CHECKING:
    from agentic_core.application.ports.metrics import MetricsPort
    from agentic_core.domain.value_objects.messages import AgentMessage


class MetricsMiddleware(Middleware):
    """Records request duration, counts, and status via MetricsPort."""

    def __init__(self, metrics_port: MetricsPort | None = None) -> None:
        self._metrics = metrics_port

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        if self._metrics is None:
            return await next_(message, ctx)

        labels = {
            "persona_id": ctx.persona_id or message.persona_id,
            "transport": ctx.extra.get("transport", "unknown"),
        }

        start = time.monotonic()
        try:
            result = await next_(message, ctx)
            self._metrics.increment_counter(
                "agent_requests_total", {**labels, "status": "success"},
            )
            return result
        except Exception:
            self._metrics.increment_counter(
                "agent_requests_total", {**labels, "status": "error"},
            )
            self._metrics.increment_counter("agent_errors_total", labels)
            raise
        finally:
            duration = time.monotonic() - start
            self._metrics.observe_histogram(
                "agent_request_duration_seconds", labels, duration,
            )
