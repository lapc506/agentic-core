"""LLM-Compiler: Plan as DAG -> Execute tools in parallel -> Join results."""
from __future__ import annotations

from typing import Any, TypedDict

from agentic_core.graph_templates.base import BaseAgentGraph


class LLMCompilerState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    dag: list[dict[str, Any]]
    parallel_results: dict[str, Any]
    joined_output: str
    done: bool


class LLMCompilerGraphTemplate(BaseAgentGraph):
    def build_graph(self) -> Any:
        try:
            from langgraph.graph import END, StateGraph

            graph = StateGraph(LLMCompilerState)
            graph.add_node("plan_dag", self._plan_dag)
            graph.add_node("execute_parallel", self._execute_parallel)
            graph.add_node("join", self._join)

            graph.set_entry_point("plan_dag")
            graph.add_edge("plan_dag", "execute_parallel")
            graph.add_edge("execute_parallel", "join")
            graph.add_edge("join", END)
            return graph.compile()
        except ImportError:
            return {"type": "llm-compiler"}

    async def _plan_dag(self, state: LLMCompilerState) -> LLMCompilerState:
        state.setdefault("dag", [])
        return state

    async def _execute_parallel(self, state: LLMCompilerState) -> LLMCompilerState:
        state["parallel_results"] = {}
        for task in state.get("dag", []):
            task_id = task.get("id", "unknown")
            state["parallel_results"][task_id] = f"result_{task_id}"
        return state

    async def _join(self, state: LLMCompilerState) -> LLMCompilerState:
        results = state.get("parallel_results", {})
        state["joined_output"] = " | ".join(f"{k}={v}" for k, v in results.items())
        state["done"] = True
        return state
