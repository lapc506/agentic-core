"""Base class for all agent graph templates.

Graph templates live in the infrastructure layer and MAY depend on LangGraph.
They receive persona configuration and a ToolPort reference so they can
invoke tools through the hexagonal boundary.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:

    from agentic_core.application.ports.tool import ToolPort
    from agentic_core.domain.entities.persona import Persona
    from agentic_core.domain.value_objects.model_config import ModelConfig


class BaseAgentGraph(ABC):
    """Abstract base for every graph template.

    Subclasses must implement ``build_graph`` which returns a compiled
    LangGraph ``CompiledStateGraph`` (or a plain dict fallback when
    LangGraph is not installed).
    """

    def __init__(
        self,
        *,
        persona: Persona | None = None,
        tool_port: ToolPort | None = None,
        model_config: ModelConfig | None = None,
    ) -> None:
        self._persona = persona
        self._tool_port = tool_port
        self._model_config = model_config

    @property
    def persona(self) -> Persona | None:
        return getattr(self, "_persona", None)

    @property
    def tool_port(self) -> ToolPort | None:
        return getattr(self, "_tool_port", None)

    @property
    def model_config(self) -> ModelConfig | None:
        return getattr(self, "_model_config", None)

    @abstractmethod
    def build_graph(self) -> Any:
        """Compile and return the LangGraph state graph.

        Returns a ``CompiledStateGraph`` when LangGraph is available,
        or a plain dict descriptor as a fallback.
        """
        ...
