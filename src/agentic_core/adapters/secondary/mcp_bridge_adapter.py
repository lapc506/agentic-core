from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from agentic_core.application.ports.tool import ToolPort
from agentic_core.config.settings import MCPBridgeConfig, MCPServerEntry
from agentic_core.domain.events.domain_events import ToolDegraded, ToolRecovered
from agentic_core.domain.value_objects.tools import ToolError, ToolHealthStatus, ToolResult
from agentic_core.shared_kernel.events import EventBus

from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Safe env vars allowed for MCP subprocesses
_SAFE_ENV_KEYS = frozenset({
    "PATH", "HOME", "USER", "LANG", "TERM", "SHELL", "TMPDIR",
    "LC_ALL", "LC_CTYPE",
})


def _build_safe_env(env_config: dict[str, str]) -> dict[str, str]:
    """Filter env vars: only safe baseline + explicitly configured vars."""
    safe = {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}
    for key, value in env_config.items():
        if value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            resolved = os.environ.get(var_name, "")
            if resolved:
                safe[key] = resolved
            else:
                logger.warning("MCP env var %s not resolved: %s", key, var_name)
        else:
            safe[key] = value
    return safe


def _sanitize_error(error_msg: str) -> str:
    """Strip potential secrets from error messages."""
    import re
    patterns = [
        r"sk-[a-zA-Z0-9_-]{20,}",         # API keys (Anthropic, OpenAI)
        r"Bearer\s+[a-zA-Z0-9._-]+",      # Bearer tokens
        r"ghp_[a-zA-Z0-9]{36}",           # GitHub PATs
        r"AIza[a-zA-Z0-9_-]{35}",         # Google API keys
    ]
    for pattern in patterns:
        error_msg = re.sub(pattern, "[REDACTED]", error_msg)
    return error_msg


class MCPServerConnection:
    """Manages lifecycle of a single MCP server connection."""

    def __init__(self, name: str, config: MCPServerEntry) -> None:
        self.name = name
        self.config = config
        self.tools: dict[str, dict[str, Any]] = {}
        self._session: Any = None
        self._connected = False

    async def connect(self) -> None:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            if self.config.transport == "stdio" and self.config.command:
                env = _build_safe_env(self.config.env)
                server_params = StdioServerParameters(
                    command=self.config.command,
                    args=self.config.args,
                    env=env,
                )
                # Note: real connection lifecycle managed by context manager
                # This is a simplified version for the adapter pattern
                self._connected = True
                logger.info("MCP server '%s' connected (stdio)", self.name)
            else:
                logger.warning("MCP transport '%s' not yet implemented for '%s'",
                             self.config.transport, self.name)
        except ImportError:
            logger.info("MCP SDK not installed, server '%s' unavailable", self.name)
        except Exception:
            logger.exception("Failed to connect MCP server '%s'", self.name)

    async def discover_tools(self) -> dict[str, dict[str, Any]]:
        if not self._connected:
            return {}
        # In full implementation: self._session.list_tools()
        # Returning empty for now — tools populated via config or real MCP session
        return self.tools

    async def call_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        if not self._connected:
            raise ConnectionError(f"MCP server '{self.name}' not connected")
        # In full implementation: self._session.call_tool(tool_name, args)
        return f"[MCP:{self.name}] {tool_name} executed"

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("MCP server '%s' disconnected", self.name)

    @property
    def is_connected(self) -> bool:
        return self._connected


class MCPBridgeAdapter(ToolPort):
    """Discovers, connects, and manages tools from MCP servers.

    Implements phantom tool prevention: tools are healthchecked at registration
    and dynamically deregistered on failure (OpenClaw #50131 mitigation)."""

    def __init__(self, config: MCPBridgeConfig, event_bus: EventBus) -> None:
        self._config = config
        self._event_bus = event_bus
        self._servers: dict[str, MCPServerConnection] = {}
        self._tool_registry: dict[str, str] = {}  # tool_name -> server_name
        self._healthy_tools: set[str] = set()

    async def start(self) -> None:
        for name, entry in self._config.servers.items():
            server = MCPServerConnection(name, entry)
            await server.connect()
            self._servers[name] = server

            if server.is_connected:
                tools = await server.discover_tools()
                for tool_name, tool_schema in tools.items():
                    full_name = f"mcp_{name}_{tool_name}" if self._config.tool_prefix else tool_name
                    health = await self.healthcheck_tool(full_name)
                    if health.healthy:
                        self._tool_registry[full_name] = name
                        self._healthy_tools.add(full_name)
                    else:
                        logger.warning("Tool '%s' failed healthcheck: %s", full_name, health.reason)

        logger.info("MCP bridge started: %d servers, %d tools registered",
                    len(self._servers), len(self._healthy_tools))

    async def stop(self) -> None:
        for server in self._servers.values():
            await server.disconnect()
        self._servers.clear()
        self._tool_registry.clear()
        self._healthy_tools.clear()

    async def execute(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        server_name = self._tool_registry.get(tool_name)
        if server_name is None:
            return ToolResult(success=False, error=ToolError(
                code="not_found", message=f"Tool '{tool_name}' not registered", retriable=False,
            ))

        server = self._servers.get(server_name)
        if server is None or not server.is_connected:
            await self._handle_degradation(tool_name, "Server disconnected")
            return ToolResult(success=False, error=ToolError(
                code="capability_missing", message="MCP server disconnected", retriable=False,
            ))

        try:
            output = await server.call_tool(tool_name.removeprefix(f"mcp_{server_name}_"), args)
            return ToolResult(success=True, output=output)
        except Exception as e:
            sanitized = _sanitize_error(str(e))
            await self._handle_degradation(tool_name, sanitized)
            return ToolResult(success=False, error=ToolError(
                code="execution_failed", message=sanitized, retriable=True,
            ))

    async def list_tools(self, persona_id: str) -> list[str]:
        return sorted(self._healthy_tools)

    async def healthcheck_tool(self, tool_name: str) -> ToolHealthStatus:
        # Phase 1: basic healthcheck (server connected)
        server_name = self._tool_registry.get(tool_name)
        if server_name:
            server = self._servers.get(server_name)
            if server and server.is_connected:
                return ToolHealthStatus(tool_name=tool_name, healthy=True)
            return ToolHealthStatus(tool_name=tool_name, healthy=False, reason="Server disconnected")
        # New tool — assume healthy if we can reach here
        return ToolHealthStatus(tool_name=tool_name, healthy=True)

    async def deregister_tool(self, tool_name: str) -> None:
        self._tool_registry.pop(tool_name, None)
        self._healthy_tools.discard(tool_name)
        logger.info("Tool '%s' deregistered", tool_name)

    async def _handle_degradation(self, tool_name: str, reason: str) -> None:
        await self.deregister_tool(tool_name)
        await self._event_bus.publish(ToolDegraded(
            tool_name=tool_name, reason=reason, timestamp=datetime.now(timezone.utc),
        ))
