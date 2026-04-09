"""Tool argument semantic validation -- deep inspection of tool inputs.

Goes beyond JSON-Schema type checks: resolves paths, validates URLs
against the egress allowlist, enforces size limits, and applies
per-tool-type semantic rules.
"""
from __future__ import annotations

import ipaddress
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Result types
# ------------------------------------------------------------------

@dataclass(frozen=True)
class Violation:
    """A single validation failure."""

    field: str
    rule: str
    message: str


@dataclass
class ValidationResult:
    """Outcome of validating a tool invocation's arguments."""

    valid: bool = True
    violations: list[Violation] = field(default_factory=list)
    sanitized_args: dict[str, Any] = field(default_factory=dict)

    def add_violation(self, field: str, rule: str, message: str) -> None:
        self.violations.append(Violation(field=field, rule=rule, message=message))
        self.valid = False


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

@dataclass
class ValidationConfig:
    """Tunable limits for the validator."""

    workspace_root: str = "/workspace"
    string_max_length: int = 100_000
    array_max_items: int = 1_000
    pattern_max_length: int = 500
    egress_allowlist: list[str] = field(
        default_factory=lambda: [
            "https://api.openai.com/*",
            "https://api.anthropic.com/*",
            "https://openrouter.ai/*",
            "https://api.fireworks.ai/*",
            "http://localhost:*",
            "http://127.0.0.1:*",
        ],
    )
    sensitive_file_patterns: list[str] = field(
        default_factory=lambda: [
            ".env",
            ".env.*",
            "*.pem",
            "*.key",
            "id_rsa",
            "id_ed25519",
            "credentials.json",
            "service_account.json",
        ],
    )


# ------------------------------------------------------------------
# Internal IP detection
# ------------------------------------------------------------------

_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_internal_ip(host: str) -> bool:
    """Return True when *host* parses as a private/loopback IP address."""
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(addr in net for net in _PRIVATE_NETS)


# ------------------------------------------------------------------
# Validator
# ------------------------------------------------------------------

class ToolArgValidator:
    """Semantic validation of tool arguments before execution."""

    def __init__(self, config: ValidationConfig | None = None) -> None:
        self._config = config or ValidationConfig()
        self._workspace_real = os.path.realpath(self._config.workspace_root)

    @property
    def config(self) -> ValidationConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> ValidationResult:
        """Validate *args* for the given *tool_name*.

        Returns a :class:`ValidationResult` which is always populated,
        even when the tool type has no specific rules (generic limits
        still apply).
        """
        result = ValidationResult(sanitized_args=dict(args))

        # Generic constraints
        self._check_generic_limits(args, result)

        # Per-tool-type semantic rules
        prefix = tool_name.split("_")[0] if "_" in tool_name else tool_name
        handler = {
            "file": self._validate_file_tool,
            "http": self._validate_http_tool,
            "bash": self._validate_bash_tool,
            "search": self._validate_search_tool,
        }.get(prefix)

        if handler is not None:
            handler(tool_name, args, result)

        return result

    # ------------------------------------------------------------------
    # Generic limits
    # ------------------------------------------------------------------

    def _check_generic_limits(
        self, args: dict[str, Any], result: ValidationResult
    ) -> None:
        for key, val in args.items():
            if isinstance(val, str) and len(val) > self._config.string_max_length:
                result.add_violation(
                    key,
                    "string_max_length",
                    f"String argument '{key}' exceeds max length "
                    f"({len(val)} > {self._config.string_max_length})",
                )
            if isinstance(val, list) and len(val) > self._config.array_max_items:
                result.add_violation(
                    key,
                    "array_max_items",
                    f"Array argument '{key}' exceeds max items "
                    f"({len(val)} > {self._config.array_max_items})",
                )

    # ------------------------------------------------------------------
    # file_* tools
    # ------------------------------------------------------------------

    def _validate_file_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        path_val = args.get("path") or args.get("file_path") or args.get("target")
        if path_val is None:
            return

        resolved = os.path.realpath(os.path.expanduser(str(path_val)))

        # Workspace boundary
        if not (
            resolved == self._workspace_real
            or resolved.startswith(self._workspace_real + os.sep)
        ):
            result.add_violation(
                "path",
                "workspace_boundary",
                f"Path resolves outside workspace: {resolved}",
            )

        # Sensitive file check
        basename = os.path.basename(resolved)
        for pattern in self._config.sensitive_file_patterns:
            if self._glob_match(basename, pattern):
                result.add_violation(
                    "path",
                    "sensitive_file",
                    f"Access to sensitive file: {basename}",
                )
                break

    # ------------------------------------------------------------------
    # http_* tools
    # ------------------------------------------------------------------

    def _validate_http_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        url = args.get("url") or args.get("endpoint")
        if url is None:
            return
        url = str(url)

        # Egress allowlist
        if not self._url_in_allowlist(url):
            result.add_violation(
                "url",
                "egress_allowlist",
                f"URL not in egress allowlist: {url}",
            )

        # Internal IP detection
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if _is_internal_ip(host):
            result.add_violation(
                "url",
                "internal_ip",
                f"URL targets internal IP: {host}",
            )

    # ------------------------------------------------------------------
    # bash tools
    # ------------------------------------------------------------------

    def _validate_bash_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        command = args.get("command") or args.get("cmd")
        if command is None:
            return

        from agentic_core.application.services.command_parser import CommandParser

        parser = CommandParser()
        analysis = parser.analyse(str(command))
        if not analysis.is_safe:
            for msg in analysis.violation_messages:
                result.add_violation("command", "command_parser", msg)

    # ------------------------------------------------------------------
    # search_* tools
    # ------------------------------------------------------------------

    def _validate_search_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        pattern = args.get("pattern") or args.get("query") or args.get("regex")
        if pattern is None:
            return
        if len(str(pattern)) > self._config.pattern_max_length:
            result.add_violation(
                "pattern",
                "pattern_max_length",
                f"Search pattern exceeds max length "
                f"({len(str(pattern))} > {self._config.pattern_max_length})",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _url_in_allowlist(self, url: str) -> bool:
        """Check *url* against the configured egress patterns (fnmatch-style)."""
        import fnmatch

        for pattern in self._config.egress_allowlist:
            if fnmatch.fnmatch(url, pattern):
                return True
        return False

    @staticmethod
    def _glob_match(name: str, pattern: str) -> bool:
        import fnmatch

        return fnmatch.fnmatch(name, pattern)
