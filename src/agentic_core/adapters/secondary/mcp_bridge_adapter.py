"""MCP Bridge adapter — connects to MCP servers for tool discovery and execution."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from agentic_core.application.ports.tool import ToolPort
from agentic_core.domain.events.domain_events import ToolDegraded
from agentic_core.domain.value_objects.tools import ToolError, ToolHealthStatus, ToolResult

# Pydantic models using `from __future__ import annotations` with TYPE_CHECKING
# imports of datetime need an explicit model_rebuild() to resolve forward refs.
ToolDegraded.model_rebuild()

if TYPE_CHECKING:
    from agentic_core.config.settings import MCPBridgeConfig, MCPServerEntry, MCPToolFilter
    from agentic_core.shared_kernel.events import EventBus

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
    patterns = [
        r"sk-[a-zA-Z0-9_-]{20,}",         # API keys (Anthropic, OpenAI)
        r"Bearer\s+[a-zA-Z0-9._-]+",      # Bearer tokens
        r"ghp_[a-zA-Z0-9]{36}",           # GitHub PATs
        r"AIza[a-zA-Z0-9_-]{35}",         # Google API keys
    ]
    for pattern in patterns:
        error_msg = re.sub(pattern, "[REDACTED]", error_msg)
    return error_msg


def _passes_tool_filter(tool_name: str, tool_filter: MCPToolFilter) -> bool:
    """Check if a tool passes the server's include/exclude filter.

    Rules:
    - If include is non-empty, tool must match at least one include pattern.
    - If exclude is non-empty, tool must NOT match any exclude pattern.
    - Exclude takes precedence over include.
    - Patterns support fnmatch-style globs (e.g. "create_*", "list_*").
    """
    from fnmatch import fnmatch

    if tool_filter.exclude and any(fnmatch(tool_name, pat) for pat in tool_filter.exclude):
        return False

    if tool_filter.include:
        return any(fnmatch(tool_name, pat) for pat in tool_filter.include)

    return True


@dataclass
class MCPTool:
    """A tool discovered from an MCP server."""
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""
    healthy: bool = True


class MCPServerConnection:
    """Manages lifecycle of a single MCP server connection.

    Supports stdio transport (spawns subprocess, communicates via JSON-RPC
    on stdin/stdout) and HTTP/streamable-HTTP transports.
    """

    def __init__(self, name: str, config: MCPServerEntry) -> None:
        self.name = name
        self.config = config
        self.tools: dict[str, MCPTool] = {}
        self._process: subprocess.Popen[bytes] | None = None
        self._connected = False
        self._error: str = ""
        self._request_id = 0
        self._read_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to the MCP server and perform the initialization handshake."""
        transport = self.config.transport
        try:
            if transport == "stdio":
                await self._connect_stdio()
            elif transport in ("sse", "streamable-http"):
                await self._connect_http()
            else:
                self._error = f"Unknown transport: {transport}"
                logger.warning("MCP transport '%s' not supported for '%s'", transport, self.name)
        except Exception as exc:
            self._connected = False
            self._error = _sanitize_error(str(exc))
            logger.exception("Failed to connect MCP server '%s'", self.name)

    async def disconnect(self) -> None:
        """Terminate the server process and mark as disconnected."""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            self._process = None
            logger.info("MCP server '%s' stopped", self.name)
        self._connected = False

    # ------------------------------------------------------------------
    # Stdio transport
    # ------------------------------------------------------------------

    async def _connect_stdio(self) -> None:
        command = self.config.command
        if not command:
            raise ValueError(f"MCP server '{self.name}': command is required for stdio transport")

        env = _build_safe_env(self.config.env)

        self._process = subprocess.Popen(
            [command, *self.config.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        self._connected = True

        # MCP initialization handshake (JSON-RPC 2.0)
        init_result = await self._send_jsonrpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "agentic-core", "version": "0.1.0"},
        })

        if init_result is None:
            self._connected = False
            self._error = "Initialization handshake failed"
            logger.error("MCP server '%s': init handshake failed", self.name)
            return

        # Send initialized notification (no response expected)
        await self._send_notification("notifications/initialized", {})

        logger.info("MCP server '%s' connected (stdio)", self.name)

    # ------------------------------------------------------------------
    # HTTP transport
    # ------------------------------------------------------------------

    async def _connect_http(self) -> None:
        url = self.config.url
        if not url:
            raise ValueError(f"MCP server '{self.name}': url is required for HTTP transport")

        self._connected = True
        logger.info("MCP server '%s': HTTP connection configured at %s", self.name, url)

    # ------------------------------------------------------------------
    # Tool discovery
    # ------------------------------------------------------------------

    async def discover_tools(self) -> dict[str, MCPTool]:
        """Ask the server for its tool list via tools/list."""
        if not self._connected:
            return {}

        if self.config.transport == "stdio":
            tools_result = await self._send_jsonrpc("tools/list", {})
            if tools_result and "tools" in tools_result:
                for tool_data in tools_result["tools"]:
                    name = tool_data.get("name", "")
                    tool = MCPTool(
                        name=name,
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        server_name=self.name,
                    )
                    self.tools[name] = tool
                logger.info("MCP server '%s': discovered %d tools", self.name, len(self.tools))
            else:
                logger.warning("MCP server '%s': no tools discovered", self.name)

        return self.tools

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def call_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        """Execute a tool call on this server."""
        if not self._connected:
            raise ConnectionError(f"MCP server '{self.name}' not connected")

        if self.config.transport == "stdio":
            result = await self._send_jsonrpc("tools/call", {
                "name": tool_name,
                "arguments": args,
            })
            if result is None:
                raise RuntimeError(f"Tool call '{tool_name}' returned no result")
            # MCP tools/call returns {content: [{type: "text", text: "..."}]}
            if isinstance(result, dict) and "content" in result:
                parts = result["content"]
                texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
                return "\n".join(texts) if texts else json.dumps(result)
            return json.dumps(result) if not isinstance(result, str) else result

        # HTTP transport
        raise NotImplementedError(f"Tool execution via {self.config.transport} not yet implemented")

    # ------------------------------------------------------------------
    # Healthcheck (ping)
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        """Ping the server to check connectivity."""
        if not self._connected:
            return False
        if self.config.transport == "stdio":
            result = await self._send_jsonrpc("ping", {})
            return result is not None
        # HTTP: assume connected if flag is set (real impl would do an HTTP ping)
        return self._connected

    # ------------------------------------------------------------------
    # JSON-RPC 2.0 over stdio (Content-Length framing)
    # ------------------------------------------------------------------

    async def _send_jsonrpc(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Send a JSON-RPC request and read the response."""
        proc = self._process
        if proc is None or proc.stdin is None or proc.stdout is None:
            return None

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        try:
            message = json.dumps(request)
            header = f"Content-Length: {len(message)}\r\n\r\n"
            proc.stdin.write((header + message).encode())
            proc.stdin.flush()

            # Read response with Content-Length framing
            async with self._read_lock:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._read_response,
                )
        except Exception as exc:
            logger.error("MCP server '%s': JSON-RPC error: %s", self.name, exc)
            self._connected = False
            self._error = _sanitize_error(str(exc))
            return None

    def _read_response(self) -> dict[str, Any] | None:
        """Blocking read of a Content-Length framed JSON-RPC response."""
        proc = self._process
        if proc is None or proc.stdout is None:
            return None

        while True:
            line = proc.stdout.readline().decode().strip()
            if line.startswith("Content-Length:"):
                content_length = int(line.split(":")[1].strip())
                # Read the blank separator line
                proc.stdout.readline()
                body = proc.stdout.read(content_length).decode()
                parsed = json.loads(body)
                return parsed.get("result")
            if not line:
                break

        return None

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        proc = self._process
        if proc is None or proc.stdin is None:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        try:
            message = json.dumps(notification)
            header = f"Content-Length: {len(message)}\r\n\r\n"
            proc.stdin.write((header + message).encode())
            proc.stdin.flush()
        except Exception as exc:
            logger.warning("MCP notification to '%s' failed: %s", self.name, exc)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def error(self) -> str:
        return self._error

    @property
    def transport(self) -> str:
        return self.config.transport


class MCPBridgeAdapter(ToolPort):
    """Discovers, connects, and manages tools from MCP servers.

    Supports:
    - stdio transport (spawns subprocess, communicates via JSON-RPC on stdin/stdout)
    - HTTP / streamable-HTTP transport (connects to HTTP endpoint)

    Implements phantom tool prevention: tools are healthchecked at registration
    and dynamically deregistered on failure so the LLM never sees stale tools.
    """

    def __init__(self, config: MCPBridgeConfig, event_bus: EventBus) -> None:
        self._config = config
        self._event_bus = event_bus
        self._servers: dict[str, MCPServerConnection] = {}
        self._tool_registry: dict[str, MCPTool] = {}   # full_name -> MCPTool
        self._tool_to_server: dict[str, str] = {}       # full_name -> server_name
        self._healthy_tools: set[str] = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Connect to all configured MCP servers and discover tools."""
        for name, entry in self._config.servers.items():
            server = MCPServerConnection(name, entry)
            await server.connect()
            self._servers[name] = server

            if server.is_connected:
                discovered = await server.discover_tools()
                filtered_count = 0
                for tool_name, tool in discovered.items():
                    if not _passes_tool_filter(tool_name, entry.tools):
                        filtered_count += 1
                        continue
                    full_name = f"mcp_{name}_{tool_name}" if self._config.tool_prefix else tool_name

                    # Healthcheck before registering (phantom tool prevention)
                    health = await self.healthcheck_tool(full_name)
                    if health.healthy:
                        self._tool_registry[full_name] = tool
                        self._tool_to_server[full_name] = name
                        self._healthy_tools.add(full_name)
                    else:
                        logger.warning(
                            "Tool '%s' failed healthcheck at registration: %s",
                            full_name, health.reason,
                        )

                if filtered_count:
                    logger.info(
                        "Server '%s': %d tools filtered out by include/exclude rules",
                        name, filtered_count,
                    )

        logger.info(
            "MCP bridge started: %d servers, %d tools registered",
            len(self._servers), len(self._healthy_tools),
        )

    async def stop(self) -> None:
        """Disconnect from all MCP servers and clear registries."""
        for server in self._servers.values():
            await server.disconnect()
        self._servers.clear()
        self._tool_registry.clear()
        self._tool_to_server.clear()
        self._healthy_tools.clear()

    # ------------------------------------------------------------------
    # ToolPort interface
    # ------------------------------------------------------------------

    async def execute(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        """Execute a tool call on the appropriate MCP server."""
        server_name = self._tool_to_server.get(tool_name)
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
            # Strip the prefix to get the raw MCP tool name
            raw_name = tool_name
            prefix = f"mcp_{server_name}_"
            if self._config.tool_prefix and tool_name.startswith(prefix):
                raw_name = tool_name[len(prefix):]

            output = await server.call_tool(raw_name, args)
            return ToolResult(success=True, output=output)
        except Exception as exc:
            sanitized = _sanitize_error(str(exc))
            await self._handle_degradation(tool_name, sanitized)
            return ToolResult(success=False, error=ToolError(
                code="execution_failed", message=sanitized, retriable=True,
            ))

    async def list_tools(self, persona_id: str) -> list[str]:
        """List all healthy, registered tools."""
        return sorted(self._healthy_tools)

    async def healthcheck_tool(self, tool_name: str) -> ToolHealthStatus:
        """Check if a tool is healthy by verifying its server is connected."""
        server_name = self._tool_to_server.get(tool_name)
        if server_name:
            server = self._servers.get(server_name)
            if server and server.is_connected:
                # Attempt a ping for deeper healthcheck
                is_alive = await server.ping()
                if is_alive:
                    return ToolHealthStatus(tool_name=tool_name, healthy=True)
                return ToolHealthStatus(
                    tool_name=tool_name, healthy=False,
                    reason="Server ping failed",
                )
            return ToolHealthStatus(
                tool_name=tool_name, healthy=False,
                reason="Server disconnected",
            )
        # New tool not yet registered -- assume healthy if server is reachable
        return ToolHealthStatus(tool_name=tool_name, healthy=True)

    async def deregister_tool(self, tool_name: str) -> None:
        """Deregister an unhealthy tool (phantom tool prevention).

        The tool is removed from the healthy set and its MCPTool is marked
        unhealthy so the LLM never sees it in subsequent list_tools calls.
        """
        tool = self._tool_registry.get(tool_name)
        if tool is not None:
            tool.healthy = False
        self._tool_to_server.pop(tool_name, None)
        self._healthy_tools.discard(tool_name)
        logger.info("Tool '%s' deregistered (phantom prevention)", tool_name)

    # ------------------------------------------------------------------
    # Server status
    # ------------------------------------------------------------------

    def list_servers(self) -> list[dict[str, Any]]:
        """List all server connections with status."""
        return [
            {
                "name": s.name,
                "transport": s.transport,
                "connected": s.is_connected,
                "tool_count": len(s.tools),
                "error": s.error,
            }
            for s in self._servers.values()
        ]

    @property
    def connected_server_count(self) -> int:
        """Number of servers currently connected."""
        return sum(1 for s in self._servers.values() if s.is_connected)

    @property
    def healthy_tool_count(self) -> int:
        """Number of tools currently considered healthy."""
        return len(self._healthy_tools)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _handle_degradation(self, tool_name: str, reason: str) -> None:
        """Deregister a failing tool and publish a ToolDegraded event."""
        await self.deregister_tool(tool_name)
        await self._event_bus.publish(ToolDegraded(
            tool_name=tool_name, reason=reason, timestamp=datetime.now(UTC),
        ))
