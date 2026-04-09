from __future__ import annotations

from agentic_core.application.ports.tool import ToolPort


class ListToolsQuery:
    pass


class ListToolsHandler:
    def __init__(self, tool_port: ToolPort) -> None:
        self._tool_port = tool_port

    async def execute(self, query: ListToolsQuery) -> list[dict]:
        tool_names = await self._tool_port.list_tools(persona_id="")
        results = []
        for name in tool_names:
            status = await self._tool_port.healthcheck_tool(name)
            results.append(
                {
                    "name": name,
                    "description": "",
                    "healthy": status.healthy,
                }
            )
        return results
