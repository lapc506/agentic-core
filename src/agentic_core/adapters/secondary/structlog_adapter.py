from __future__ import annotations

from typing import Any

import structlog

from agentic_core.application.ports.logging import LoggingPort


class StructlogAdapter(LoggingPort):
    """Structured logging via structlog with trace_id correlation."""

    def __init__(self) -> None:
        self._logger = structlog.get_logger()

    def bind_context(self, **kwargs: Any) -> None:
        structlog.contextvars.bind_contextvars(**kwargs)

    def log(self, level: str, event: str, **kwargs: Any) -> None:
        log_fn = getattr(self._logger, level.lower(), self._logger.info)
        log_fn(event, **kwargs)
