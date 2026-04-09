"""Orchestrator: GSD + Superpowers + Auto Research meta-orchestration template."""
from __future__ import annotations

from typing import Any, TypedDict

from agentic_core.graph_templates.base import BaseAgentGraph


class OrchestratorState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    phase: str
    terrain: dict[str, Any]
    gaps: list[str]
    approaches: list[dict[str, Any]]
    chosen_approach: int
    spec: str
    roadmap: dict[str, Any]
    execution_result: dict[str, Any]
    skills_to_optimize: list[str]
    done: bool


class OrchestratorGraphTemplate(BaseAgentGraph):
    def build_graph(self) -> Any:
        try:
            from langgraph.graph import END, StateGraph

            graph = StateGraph(OrchestratorState)
            graph.add_node("analyze", self._analyze)
            graph.add_node("brainstorm", self._brainstorm)
            graph.add_node("choose", self._choose)
            graph.add_node("spec", self._generate_spec)
            graph.add_node("plan", self._create_roadmap)
            graph.add_node("approve", self._approve)
            graph.add_node("execute", self._execute)
            graph.add_node("optimize", self._optimize)

            graph.set_entry_point("analyze")
            graph.add_edge("analyze", "brainstorm")
            graph.add_edge("brainstorm", "choose")
            graph.add_edge("choose", "spec")
            graph.add_edge("spec", "plan")
            graph.add_edge("plan", "approve")
            graph.add_edge("approve", "execute")
            graph.add_conditional_edges(
                "execute",
                self._after_execute,
                {"optimize": "optimize", "end": END},
            )
            graph.add_edge("optimize", END)
            return graph.compile()
        except ImportError:
            return {"type": "orchestrator"}

    async def _analyze(self, state: OrchestratorState) -> OrchestratorState:
        state["phase"] = "analyze"
        state.setdefault("terrain", {})
        state.setdefault("gaps", [])
        return state

    async def _brainstorm(self, state: OrchestratorState) -> OrchestratorState:
        state["phase"] = "brainstorm"
        state.setdefault("approaches", [])
        return state

    async def _choose(self, state: OrchestratorState) -> OrchestratorState:
        state["phase"] = "choose"
        state.setdefault("chosen_approach", 0)
        return state

    async def _generate_spec(self, state: OrchestratorState) -> OrchestratorState:
        state["phase"] = "spec"
        state.setdefault("spec", "")
        return state

    async def _create_roadmap(self, state: OrchestratorState) -> OrchestratorState:
        state["phase"] = "plan"
        state.setdefault("roadmap", {})
        return state

    async def _approve(self, state: OrchestratorState) -> OrchestratorState:
        state["phase"] = "approve"
        return state

    async def _execute(self, state: OrchestratorState) -> OrchestratorState:
        state["phase"] = "execute"
        state.setdefault("execution_result", {"success": True})
        return state

    async def _optimize(self, state: OrchestratorState) -> OrchestratorState:
        state["phase"] = "optimize"
        state["done"] = True
        return state

    def _after_execute(self, state: OrchestratorState) -> str:
        if state.get("skills_to_optimize"):
            return "optimize"
        return "end"
