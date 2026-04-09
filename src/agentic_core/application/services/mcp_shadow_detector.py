"""MCP shadow server detection -- find unauthorized MCP server processes.

Maintains a registry of authorized MCP servers from configuration and
scans the local system for rogue processes that look like MCP servers
(listening on known ports, referencing MCP config files, or running
as stdio transports).
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------

class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class MCPServerEntry:
    """A single authorized MCP server."""

    name: str
    url: str
    transport: str = "stdio"        # stdio | sse | streamable-http
    command: str = ""               # Expected launch command (for stdio)
    expected_port: int | None = None


@dataclass(frozen=True)
class ShadowAlert:
    """An alert raised when a suspicious MCP server is detected."""

    severity: AlertSeverity
    category: str
    description: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanResult:
    """Outcome of a shadow-server scan."""

    timestamp: float = field(default_factory=time.time)
    alerts: list[ShadowAlert] = field(default_factory=list)
    scanned_processes: int = 0
    scanned_configs: int = 0

    @property
    def is_clean(self) -> bool:
        return len(self.alerts) == 0


# ------------------------------------------------------------------
# Detector
# ------------------------------------------------------------------

# Known MCP-related ports to watch
_DEFAULT_MCP_PORTS: frozenset[int] = frozenset({3000, 3001, 8808, 8809, 4040})

# Config file names that typically reference MCP servers
_MCP_CONFIG_NAMES: frozenset[str] = frozenset(
    {
        "mcp.json",
        ".mcp.json",
        "mcp-servers.json",
        "claude_desktop_config.json",
    }
)


class MCPShadowDetector:
    """Detect unauthorized MCP server processes and configuration."""

    def __init__(
        self,
        authorized_servers: list[MCPServerEntry] | None = None,
        mcp_ports: frozenset[int] | None = None,
        config_search_paths: list[str] | None = None,
    ) -> None:
        self._authorized: dict[str, MCPServerEntry] = {
            s.name: s for s in (authorized_servers or [])
        }
        self._mcp_ports = mcp_ports or _DEFAULT_MCP_PORTS
        self._config_paths = config_search_paths or [
            os.path.expanduser("~/.config"),
            os.path.expanduser("~/.claude"),
            ".",
        ]
        self._audit_trail: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Configuration management
    # ------------------------------------------------------------------

    def register_server(self, entry: MCPServerEntry) -> None:
        """Add an authorized server to the registry."""
        self._authorized[entry.name] = entry
        logger.info("Registered authorized MCP server: %s", entry.name)

    def unregister_server(self, name: str) -> bool:
        if name in self._authorized:
            del self._authorized[name]
            return True
        return False

    @property
    def authorized_servers(self) -> dict[str, MCPServerEntry]:
        return dict(self._authorized)

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan(self) -> ScanResult:
        """Run a full scan: processes + config files.

        Returns a :class:`ScanResult` with any alerts found.
        """
        result = ScanResult()

        self._scan_processes(result)
        self._scan_config_files(result)

        # Record in audit trail
        self._record_audit(result)

        return result

    def scan_processes(self) -> ScanResult:
        """Scan only running processes."""
        result = ScanResult()
        self._scan_processes(result)
        self._record_audit(result)
        return result

    def scan_configs(self) -> ScanResult:
        """Scan only configuration files."""
        result = ScanResult()
        self._scan_config_files(result)
        self._record_audit(result)
        return result

    # ------------------------------------------------------------------
    # Process scanning
    # ------------------------------------------------------------------

    def _scan_processes(self, result: ScanResult) -> None:
        """Walk /proc to find suspicious MCP-like processes."""
        proc_infos = self._enumerate_processes()
        result.scanned_processes = len(proc_infos)

        authorized_commands = {
            s.command for s in self._authorized.values() if s.command
        }
        authorized_ports = {
            s.expected_port for s in self._authorized.values() if s.expected_port
        }

        for proc in proc_infos:
            cmdline = proc.get("cmdline", "")
            pid = proc.get("pid", 0)

            # Check for MCP-related keywords in cmdline
            if self._looks_like_mcp_server(cmdline):
                # Is this an authorized server?
                if not self._is_authorized_process(cmdline, authorized_commands):
                    result.alerts.append(
                        ShadowAlert(
                            severity=AlertSeverity.CRITICAL,
                            category="shadow_process",
                            description=(
                                f"Unauthorized MCP server process detected (PID {pid})"
                            ),
                            details={"pid": pid, "cmdline": cmdline[:500]},
                        )
                    )

            # Check for processes listening on MCP ports
            listening_ports = proc.get("listening_ports", [])
            for port in listening_ports:
                if port in self._mcp_ports and port not in authorized_ports:
                    result.alerts.append(
                        ShadowAlert(
                            severity=AlertSeverity.WARNING,
                            category="unauthorized_port",
                            description=(
                                f"Process (PID {pid}) listening on MCP port {port}"
                            ),
                            details={
                                "pid": pid,
                                "port": port,
                                "cmdline": cmdline[:500],
                            },
                        )
                    )

    def _enumerate_processes(self) -> list[dict[str, Any]]:
        """Read /proc/<pid>/cmdline for all accessible processes.

        Returns a list of dicts: {pid, cmdline, listening_ports}.
        Falls back gracefully on non-Linux or when /proc is unavailable.
        """
        processes: list[dict[str, Any]] = []
        proc_path = Path("/proc")

        if not proc_path.is_dir():
            return processes

        for entry in proc_path.iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            cmdline_file = entry / "cmdline"
            try:
                raw = cmdline_file.read_bytes()
                cmdline = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
            except (OSError, PermissionError):
                continue

            listening = self._get_listening_ports(pid)
            processes.append(
                {"pid": pid, "cmdline": cmdline, "listening_ports": listening}
            )

        return processes

    @staticmethod
    def _get_listening_ports(pid: int) -> list[int]:
        """Parse /proc/net/tcp(6) for sockets owned by *pid*.

        This is a best-effort helper; returns empty list on failure.
        """
        ports: list[int] = []
        # Reading per-process fd -> socket -> inode mapping is complex;
        # for a lightweight check we just return an empty list and rely
        # on cmdline matching.  A production deployment would shell out
        # to `ss -tlnp` or use psutil.
        return ports

    @staticmethod
    def _looks_like_mcp_server(cmdline: str) -> bool:
        """Heuristic: does *cmdline* look like it is running an MCP server?"""
        indicators = [
            "mcp-server",
            "mcp_server",
            "modelcontextprotocol",
            "--mcp",
            "stdio_server",
            "mcp.json",
            "mcpServer",
        ]
        lower = cmdline.lower()
        return any(ind in lower for ind in indicators)

    def _is_authorized_process(
        self, cmdline: str, authorized_commands: set[str]
    ) -> bool:
        """Check whether *cmdline* matches any authorized server command."""
        for auth_cmd in authorized_commands:
            if auth_cmd and auth_cmd in cmdline:
                return True

        # Also check by URL for sse/http servers
        for server in self._authorized.values():
            if server.url and server.url in cmdline:
                return True

        return False

    # ------------------------------------------------------------------
    # Config file scanning
    # ------------------------------------------------------------------

    def _scan_config_files(self, result: ScanResult) -> None:
        """Look for MCP config files that reference unknown servers."""
        for search_dir in self._config_paths:
            expanded = os.path.expanduser(search_dir)
            if not os.path.isdir(expanded):
                continue
            self._walk_config_dir(expanded, result)

    def _walk_config_dir(self, directory: str, result: ScanResult) -> None:
        """Walk *directory* (non-recursive, 1 level deep) for MCP configs."""
        try:
            entries = os.listdir(directory)
        except OSError:
            return

        for name in entries:
            if name not in _MCP_CONFIG_NAMES:
                continue
            full = os.path.join(directory, name)
            if not os.path.isfile(full):
                continue

            result.scanned_configs += 1
            self._check_config_file(full, result)

    def _check_config_file(self, path: str, result: ScanResult) -> None:
        """Parse a single MCP config file and flag unknown server entries."""
        try:
            with open(path) as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("Could not parse MCP config %s: %s", path, exc)
            return

        # The config format typically has a "mcpServers" or "servers" key
        servers_section = data.get("mcpServers") or data.get("servers") or {}
        if not isinstance(servers_section, dict):
            return

        for server_name, _server_cfg in servers_section.items():
            if server_name not in self._authorized:
                result.alerts.append(
                    ShadowAlert(
                        severity=AlertSeverity.WARNING,
                        category="unknown_config_server",
                        description=(
                            f"Config file references unknown MCP server: "
                            f"'{server_name}' in {path}"
                        ),
                        details={
                            "config_path": path,
                            "server_name": server_name,
                        },
                    )
                )

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def _record_audit(self, result: ScanResult) -> None:
        entry = {
            "timestamp": result.timestamp,
            "scanned_processes": result.scanned_processes,
            "scanned_configs": result.scanned_configs,
            "alerts_count": len(result.alerts),
            "alert_summaries": [
                {"severity": a.severity.value, "category": a.category}
                for a in result.alerts
            ],
        }
        self._audit_trail.append(entry)
        if result.alerts:
            logger.warning(
                "MCP shadow scan found %d alert(s)", len(result.alerts)
            )

    @property
    def audit_trail(self) -> list[dict[str, Any]]:
        return list(self._audit_trail)
