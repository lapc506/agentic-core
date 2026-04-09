"""Human-in-the-loop confirmation for tool execution."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ConfirmationMode(str, Enum):
    ALWAYS = "always"
    CONDITIONAL = "conditional"
    NEVER = "never"


class ToolHints(str, Enum):
    DESTRUCTIVE = "destructive"
    READ_ONLY = "read_only"
    IDEMPOTENT = "idempotent"
    REQUIRES_AUTH = "requires_auth"


@dataclass
class ConfirmationRequest:
    tool_name: str
    args: dict[str, Any]
    hints: list[str] = field(default_factory=list)
    reason: str = ""
    timeout_seconds: float = 300.0


@dataclass
class ConfirmationResult:
    approved: bool
    modified_args: dict[str, Any] | None = None
    reason: str = ""


class HITLConfirmationService:
    """Manages approval gates for tool execution.

    Tools can be configured to require confirmation:
    - always: every execution needs approval
    - conditional: approval based on input analysis
    - never: auto-approved (default)

    Destructive tools are auto-flagged for confirmation.
    """

    def __init__(self) -> None:
        self._tool_modes: dict[str, ConfirmationMode] = {}
        self._tool_hints: dict[str, list[str]] = {}
        self._conditions: dict[str, Callable[[dict], bool]] = {}
        self._pending: dict[str, asyncio.Future[ConfirmationResult]] = {}

    def configure_tool(
        self,
        tool_name: str,
        mode: ConfirmationMode = ConfirmationMode.NEVER,
        hints: list[str] | None = None,
        condition: Callable[[dict], bool] | None = None,
    ) -> None:
        self._tool_modes[tool_name] = mode
        if hints:
            self._tool_hints[tool_name] = hints
            if ToolHints.DESTRUCTIVE in hints and mode == ConfirmationMode.NEVER:
                self._tool_modes[tool_name] = ConfirmationMode.ALWAYS
        if condition:
            self._conditions[tool_name] = condition

    def requires_confirmation(self, tool_name: str, args: dict[str, Any]) -> bool:
        mode = self._tool_modes.get(tool_name, ConfirmationMode.NEVER)
        if mode == ConfirmationMode.ALWAYS:
            return True
        if mode == ConfirmationMode.CONDITIONAL:
            condition = self._conditions.get(tool_name)
            if condition:
                return condition(args)
        hints = self._tool_hints.get(tool_name, [])
        if ToolHints.DESTRUCTIVE in hints:
            return True
        return False

    async def request_confirmation(
        self,
        request: ConfirmationRequest,
    ) -> ConfirmationResult:
        request_id = f"{request.tool_name}:{id(request)}"
        loop = asyncio.get_event_loop()
        future: asyncio.Future[ConfirmationResult] = loop.create_future()
        self._pending[request_id] = future

        logger.info("HITL confirmation requested: %s(%s)", request.tool_name, request.args)

        try:
            result = await asyncio.wait_for(future, timeout=request.timeout_seconds)
            return result
        except asyncio.TimeoutError:
            logger.warning("HITL confirmation timed out for %s", request.tool_name)
            return ConfirmationResult(approved=False, reason="Timeout")
        finally:
            self._pending.pop(request_id, None)

    def respond(self, request_id: str, approved: bool, reason: str = "") -> bool:
        future = self._pending.get(request_id)
        if not future or future.done():
            return False
        future.set_result(ConfirmationResult(approved=approved, reason=reason))
        return True

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def get_tool_config(self, tool_name: str) -> dict[str, Any]:
        return {
            "mode": self._tool_modes.get(tool_name, ConfirmationMode.NEVER).value,
            "hints": self._tool_hints.get(tool_name, []),
        }
