from abc import ABC, abstractmethod
from typing import Any

from agentic_core.domain.value_objects.tools import ToolHealthStatus, ToolResult


class ToolInfo(ABC):
    name: str
    description: str
    source: str


class ToolPort(ABC):
    """Execute tools by name.

    DESIGN NOTE (phantom tool mitigation): Tools MUST be validated at
    registration time via healthcheck_tool. Tools that fail are never registered."""

    @abstractmethod
    async def execute(self, tool_name: str, args: dict[str, Any]) -> ToolResult: ...

    @abstractmethod
    async def list_tools(self, persona_id: str) -> list[str]: ...

    @abstractmethod
    async def healthcheck_tool(self, tool_name: str) -> ToolHealthStatus: ...

    @abstractmethod
    async def deregister_tool(self, tool_name: str) -> None: ...
