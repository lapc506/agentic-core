"""ReAct graph template: Think -> Act -> Observe -> loop.
Default template for 80% of use cases."""
from __future__ import annotations

from typing import Any, TypedDict

from agentic_core.graph_templates.base import BaseAgentGraph


class ReactState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    iterations: int
    max_iterations: int
    done: bool


class ReactGraphTemplate(BaseAgentGraph):
    """ReAct: Reasoning + Acting in a loop until done or max iterations."""

    def __init__(self, max_iterations: int = 25) -> None:
        self._max_iterations = max_iterations

    def build_graph(self) -> Any:
        try:
            from langgraph.graph import StateGraph, END

            graph = StateGraph(ReactState)
            graph.add_node("think", self._think)
            graph.add_node("act", self._act)
            graph.add_node("observe", self._observe)

            graph.set_entry_point("think")
            graph.add_edge("think", "act")
            graph.add_edge("act", "observe")
            graph.add_conditional_edges(
                "observe",
                self._should_continue,
                {"continue": "think", "end": END},
            )
            return graph.compile()
        except ImportError:
            return self._build_simple()

    async def _think(self, state: ReactState) -> ReactState:
        state.setdefault("iterations", 0)
        state["iterations"] = state.get("iterations", 0) + 1
        return state

    async def _act(self, state: ReactState) -> ReactState:
        state.setdefault("tool_calls", [])
        return state

    async def _observe(self, state: ReactState) -> ReactState:
        return state

    def _should_continue(self, state: ReactState) -> str:
        if state.get("done", False):
            return "end"
        if state.get("iterations", 0) >= state.get("max_iterations", self._max_iterations):
            return "end"
        if not state.get("tool_calls"):
            return "end"
        return "continue"

    def _build_simple(self) -> dict[str, Any]:
        return {"type": "react", "max_iterations": self._max_iterations}
