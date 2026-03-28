"""Actor node: executes tool calls via the ToolPort hexagonal boundary.

Reads ``tool_calls`` from state, invokes each tool through the ToolPort,
and appends ToolMessages back into the conversation so the LLM can observe
the results on the next iteration.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import BaseMessage, ToolMessage

if TYPE_CHECKING:
    from agentic_core.application.ports.tool import ToolPort

logger = logging.getLogger(__name__)


class ActorNode:
    """Executes tools/actions based on tool_calls in the current state.

    When a ``ToolPort`` is provided, each tool call is dispatched through
    the port's ``execute`` method (hexagonal boundary).  Without a port
    the node falls back to a stub that records the call -- useful for
    testing.
    """

    def __init__(self, tool_port: ToolPort | None = None) -> None:
        self._tool_port = tool_port

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        tool_calls: list[Any] = state.get("tool_calls", [])
        messages: list[BaseMessage] = list(state.get("messages", []))
        actions_taken: list[dict[str, Any]] = list(state.get("actions_taken", []))

        if not tool_calls:
            state["actions_taken"] = actions_taken
            return state

        for tc in tool_calls:
            tool_name: str = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
            tool_args: dict[str, Any] = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            tool_id: str = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")

            if self._tool_port is not None:
                try:
                    result = await self._tool_port.execute(tool_name, tool_args)
                    output = result.output or ""
                    success = result.success
                except Exception:
                    logger.exception("Tool execution failed: %s", tool_name)
                    output = f"Error executing tool {tool_name}"
                    success = False
            else:
                # Fallback: no tool port -- stub for tests
                output = f"stub_result({tool_name})"
                success = True

            # Append ToolMessage for the LLM to observe
            messages.append(
                ToolMessage(
                    content=output,
                    tool_call_id=tool_id or tool_name,
                )
            )

            actions_taken.append({
                "tool": tool_name,
                "args": tool_args,
                "output": output,
                "success": success,
            })

        state["messages"] = messages
        state["actions_taken"] = actions_taken
        # Clear tool_calls after execution
        state["tool_calls"] = []

        return state
