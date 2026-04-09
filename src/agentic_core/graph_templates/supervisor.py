"""Supervisor: Routes messages to specialized sub-agent personas."""
from __future__ import annotations

from typing import Any, TypedDict

from agentic_core.graph_templates.base import BaseAgentGraph


class SupervisorState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    routed_to: str | None
    delegate_results: dict[str, Any]
    final_response: str
    done: bool


class SupervisorGraphTemplate(BaseAgentGraph):
    def __init__(self, delegate_names: list[str] | None = None) -> None:
        self._delegates = delegate_names or []

    def build_graph(self) -> Any:
        try:
            from langgraph.graph import END, StateGraph

            graph = StateGraph(SupervisorState)
            graph.add_node("route", self._route)
            graph.add_node("delegate", self._delegate)
            graph.add_node("synthesize", self._synthesize)

            graph.set_entry_point("route")
            graph.add_edge("route", "delegate")
            graph.add_conditional_edges(
                "delegate",
                self._after_delegate,
                {"more": "route", "done": "synthesize"},
            )
            graph.add_edge("synthesize", END)
            return graph.compile()
        except ImportError:
            return {"type": "supervisor", "delegates": self._delegates}

    async def _route(self, state: SupervisorState) -> SupervisorState:
        state.setdefault("delegate_results", {})
        if self._delegates:
            pending = [d for d in self._delegates if d not in state.get("delegate_results", {})]
            state["routed_to"] = pending[0] if pending else None
        return state

    async def _delegate(self, state: SupervisorState) -> SupervisorState:
        target = state.get("routed_to")
        if target:
            state.setdefault("delegate_results", {})[target] = f"result_from_{target}"
        return state

    async def _synthesize(self, state: SupervisorState) -> SupervisorState:
        results = state.get("delegate_results", {})
        state["final_response"] = " + ".join(f"{k}: {v}" for k, v in results.items())
        state["done"] = True
        return state

    def _after_delegate(self, state: SupervisorState) -> str:
        pending = [d for d in self._delegates if d not in state.get("delegate_results", {})]
        return "more" if pending else "done"
