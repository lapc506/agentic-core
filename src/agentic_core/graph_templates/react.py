"""ReAct graph template: Think -> Act -> Observe -> loop.

Default template for 80% of use cases.  When LangGraph is available the
template compiles a real ``StateGraph``; otherwise it returns a plain-dict
fallback so that unit tests and environments without LangGraph still work.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypedDict

from agentic_core.graph_templates.base import BaseAgentGraph

if TYPE_CHECKING:

    from agentic_core.application.ports.tool import ToolPort
    from agentic_core.domain.entities.persona import Persona
    from agentic_core.domain.value_objects.model_config import ModelConfig

logger = logging.getLogger(__name__)


class ReactState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    actions_taken: list[dict[str, Any]]
    thought: str
    iterations: int
    max_iterations: int
    done: bool


class ReactGraphTemplate(BaseAgentGraph):
    """ReAct: Reasoning + Acting in a loop until done or max iterations.

    Parameters
    ----------
    max_iterations:
        Safety cap on the think-act-observe loop.
    persona, tool_port, model_config:
        Forwarded to ``BaseAgentGraph`` for hexagonal-architecture wiring.
    """

    def __init__(
        self,
        max_iterations: int = 25,
        *,
        persona: Persona | None = None,
        tool_port: ToolPort | None = None,
        model_config: ModelConfig | None = None,
    ) -> None:
        super().__init__(persona=persona, tool_port=tool_port, model_config=model_config)
        self._max_iterations = max_iterations

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self) -> Any:
        """Compile the ReAct loop as a LangGraph StateGraph.

        Falls back to a simple dict descriptor if LangGraph is missing.
        """
        try:
            from langgraph.graph import END, StateGraph

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

    # ------------------------------------------------------------------
    # Node implementations
    # ------------------------------------------------------------------

    async def _think(self, state: ReactState) -> ReactState:
        """Reasoning step: invoke the LLM (or increment counter in tests)."""
        from agentic_core.graph_templates.nodes.planner import PlannerNode

        model = self._get_model()
        system_prompt = self._get_system_prompt()
        planner = PlannerNode(model=model, system_prompt=system_prompt)
        result = await planner(state)  # type: ignore[arg-type]
        return result  # type: ignore[return-value]

    async def _act(self, state: ReactState) -> ReactState:
        """Action step: execute any tool calls produced by the think step."""
        from agentic_core.graph_templates.nodes.actor import ActorNode

        actor = ActorNode(tool_port=self._tool_port)
        result = await actor(state)  # type: ignore[arg-type]
        return result  # type: ignore[return-value]

    async def _observe(self, state: ReactState) -> ReactState:
        """Observation step: post-process results before routing decision.

        Currently a pass-through; subclasses can override to add
        reflection, summarisation, or guardrails.
        """
        return state

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _should_continue(self, state: ReactState) -> str:
        """Decide whether to loop back to *think* or terminate."""
        if state.get("done", False):
            return "end"
        if state.get("iterations", 0) >= state.get(
            "max_iterations", self._max_iterations
        ):
            return "end"
        if not state.get("tool_calls"):
            return "end"
        return "continue"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_model(self) -> Any | None:
        """Resolve an LLM from model_config if available."""
        mc = self._model_config or (self._persona.model_config if self._persona else None)
        if mc is None:
            return None

        try:
            if mc.provider == "anthropic":
                from langchain_anthropic import ChatAnthropic

                return ChatAnthropic(
                    model=mc.model,
                    temperature=mc.temperature,
                    max_tokens=mc.max_tokens,
                )
            # Extensible: add more providers here
        except ImportError:
            logger.warning(
                "LLM provider %s not available (missing langchain adapter)", mc.provider
            )
        return None

    def _get_system_prompt(self) -> str:
        """Build a system prompt from the persona configuration."""
        if self._persona is None:
            return ""
        parts = []
        if self._persona.role:
            parts.append(f"Role: {self._persona.role}")
        if self._persona.description:
            parts.append(self._persona.description)
        return "\n".join(parts)

    def _build_simple(self) -> dict[str, Any]:
        """Plain-dict fallback when LangGraph is not installed."""
        return {"type": "react", "max_iterations": self._max_iterations}
