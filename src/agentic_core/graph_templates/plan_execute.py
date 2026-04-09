"""Plan-and-Execute: Plan multi-step -> Execute each -> Replan if needed."""
from __future__ import annotations

from typing import Any, TypedDict

from agentic_core.graph_templates.base import BaseAgentGraph


class PlanExecuteState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    plan: list[str]
    current_step: int
    results: list[dict[str, Any]]
    needs_replan: bool
    done: bool


class PlanExecuteGraphTemplate(BaseAgentGraph):
    def __init__(self, max_replans: int = 3) -> None:
        self._max_replans = max_replans

    def build_graph(self) -> Any:
        try:
            from langgraph.graph import END, StateGraph

            graph = StateGraph(PlanExecuteState)
            graph.add_node("plan", self._plan)
            graph.add_node("execute_step", self._execute_step)
            graph.add_node("replan", self._replan)

            graph.set_entry_point("plan")
            graph.add_edge("plan", "execute_step")
            graph.add_conditional_edges(
                "execute_step",
                self._after_execute,
                {"next_step": "execute_step", "replan": "replan", "end": END},
            )
            graph.add_edge("replan", "execute_step")
            return graph.compile()
        except ImportError:
            return {"type": "plan-and-execute", "max_replans": self._max_replans}

    async def _plan(self, state: PlanExecuteState) -> PlanExecuteState:
        state.setdefault("plan", [])
        state["current_step"] = 0
        state["results"] = []
        return state

    async def _execute_step(self, state: PlanExecuteState) -> PlanExecuteState:
        idx = state.get("current_step", 0)
        plan = state.get("plan", [])
        if idx < len(plan):
            state.setdefault("results", []).append({"step": idx, "output": f"executed: {plan[idx]}"})
        state["current_step"] = idx + 1
        return state

    async def _replan(self, state: PlanExecuteState) -> PlanExecuteState:
        state["needs_replan"] = False
        state["current_step"] = 0
        return state

    def _after_execute(self, state: PlanExecuteState) -> str:
        idx = state.get("current_step", 0)
        plan = state.get("plan", [])
        if state.get("needs_replan", False):
            return "replan"
        if idx >= len(plan):
            return "end"
        return "next_step"
