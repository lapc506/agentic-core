"""Reflexion: Act -> Self-critique -> Retry with feedback. Wraps any base template."""
from __future__ import annotations

from typing import Any, TypedDict

from agentic_core.graph_templates.base import BaseAgentGraph


class ReflexionState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    action_output: str
    critique: str
    quality_ok: bool
    attempts: int
    max_attempts: int


class ReflexionGraphTemplate(BaseAgentGraph):
    def __init__(self, max_attempts: int = 3) -> None:
        self._max_attempts = max_attempts

    def build_graph(self) -> Any:
        try:
            from langgraph.graph import END, StateGraph

            graph = StateGraph(ReflexionState)
            graph.add_node("act", self._act)
            graph.add_node("critique", self._critique)
            graph.add_node("retry", self._retry)

            graph.set_entry_point("act")
            graph.add_edge("act", "critique")
            graph.add_conditional_edges(
                "critique",
                self._should_retry,
                {"retry": "retry", "accept": END},
            )
            graph.add_edge("retry", "act")
            return graph.compile()
        except ImportError:
            return {"type": "reflexion", "max_attempts": self._max_attempts}

    async def _act(self, state: ReflexionState) -> ReflexionState:
        state["attempts"] = state.get("attempts", 0) + 1
        state.setdefault("action_output", "")
        return state

    async def _critique(self, state: ReflexionState) -> ReflexionState:
        state.setdefault("critique", "")
        state.setdefault("quality_ok", True)
        return state

    async def _retry(self, state: ReflexionState) -> ReflexionState:
        return state

    def _should_retry(self, state: ReflexionState) -> str:
        if state.get("quality_ok", True):
            return "accept"
        if state.get("attempts", 0) >= state.get("max_attempts", self._max_attempts):
            return "accept"
        return "retry"
