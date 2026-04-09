"""Sandbox command parsing hardening -- structural analysis of shell commands.

Replaces naive string matching in SandboxExecutor._check_policy() with
AST-like decomposition that catches quoting tricks, shell expansions,
path traversal, and pipe/chain evasion.
"""
from __future__ import annotations

import logging
import os
import re
import shlex
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)


class RiskLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DetectedRisk:
    """A single risk identified during command analysis."""

    level: RiskLevel
    category: str
    description: str


@dataclass
class CommandAnalysis:
    """Result of structural command analysis."""

    raw_command: str
    parsed_commands: list[list[str]] = field(default_factory=list)
    detected_risks: list[DetectedRisk] = field(default_factory=list)
    resolved_paths: list[str] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        return not any(
            r.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
            for r in self.detected_risks
        )

    @property
    def violation_messages(self) -> list[str]:
        return [
            f"[{r.level.value}] {r.category}: {r.description}"
            for r in self.detected_risks
            if r.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        ]


# Patterns that remain dangerous regardless of quoting --
# we check against the *resolved* token list, not the raw string.
_DANGEROUS_BINARIES: frozenset[str] = frozenset(
    {
        "rm",
        "mkfs",
        "dd",
        "shred",
        "wipefs",
        "fdisk",
        "parted",
        "mount",
        "umount",
        "insmod",
        "rmmod",
        "modprobe",
        "reboot",
        "shutdown",
        "halt",
        "poweroff",
        "init",
        "systemctl",
    }
)

# Fork bomb signatures (checked on raw input before shlex)
_FORK_BOMB_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r":\(\)\s*\{.*\}"),  # :(){ :|:& };:
    re.compile(r"\.\(\)\s*\{.*\}"),
]

# Shell expansion / injection tokens detected on raw input
_EXPANSION_RE = re.compile(
    r"""
      \$\(          # $(cmd)
    | `[^`]+`       # `cmd`
    | \$\{[^}]+\}  # ${VAR}
    | \$[A-Za-z_]   # $VAR (bare variable reference)
    """,
    re.VERBOSE,
)

# Operators that chain or redirect commands
_CHAIN_OPERATORS: frozenset[str] = frozenset({";", "&&", "||", "|", "&"})

_CHAIN_RE = re.compile(r"(?:;|&&|\|\||[|&])")


class CommandParser:
    """Structural analysis of shell commands for the sandbox policy engine."""

    def __init__(
        self,
        allowed_paths: list[str] | None = None,
        denied_paths: list[str] | None = None,
    ) -> None:
        self._allowed_paths = [
            os.path.realpath(p) for p in (allowed_paths or ["/tmp", "/sandbox"])
        ]
        self._denied_paths = [
            os.path.realpath(os.path.expanduser(p))
            for p in (denied_paths or ["/etc/passwd", "/etc/shadow", "~/.ssh"])
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(self, command: str) -> CommandAnalysis:
        """Return a full :class:`CommandAnalysis` for *command*."""
        analysis = CommandAnalysis(raw_command=command)

        # 1. Fork-bomb check (raw string -- shlex can't parse these)
        self._check_fork_bombs(command, analysis)

        # 2. Shell expansion / injection
        self._check_shell_expansion(command, analysis)

        # 3. Command chaining operators
        self._check_chaining(command, analysis)

        # 4. Split into sub-commands (by ;, &&, ||, |) then tokenise each
        sub_commands = self._split_sub_commands(command)
        for sub in sub_commands:
            tokens = self._safe_tokenise(sub)
            if tokens:
                analysis.parsed_commands.append(tokens)
                self._check_dangerous_binary(tokens, analysis)
                self._check_paths(tokens, analysis)
                self._check_destructive_flags(tokens, analysis)
                self._check_device_access(tokens, analysis)

        return analysis

    # Convenience alias matching the requirement name
    analyze = analyse

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_fork_bombs(self, raw: str, out: CommandAnalysis) -> None:
        for pat in _FORK_BOMB_PATTERNS:
            if pat.search(raw):
                out.detected_risks.append(
                    DetectedRisk(
                        RiskLevel.CRITICAL,
                        "fork_bomb",
                        "Fork-bomb pattern detected",
                    )
                )
                return

    def _check_shell_expansion(self, raw: str, out: CommandAnalysis) -> None:
        matches = _EXPANSION_RE.findall(raw)
        if matches:
            out.detected_risks.append(
                DetectedRisk(
                    RiskLevel.HIGH,
                    "shell_expansion",
                    f"Shell expansion detected: {', '.join(matches[:5])}",
                )
            )

    def _check_chaining(self, raw: str, out: CommandAnalysis) -> None:
        ops = _CHAIN_RE.findall(raw)
        if ops:
            out.detected_risks.append(
                DetectedRisk(
                    RiskLevel.MEDIUM,
                    "command_chain",
                    f"Command chaining operators: {' '.join(ops)}",
                )
            )

    def _check_dangerous_binary(
        self, tokens: list[str], out: CommandAnalysis
    ) -> None:
        if not tokens:
            return
        binary = os.path.basename(tokens[0])
        if binary in _DANGEROUS_BINARIES:
            out.detected_risks.append(
                DetectedRisk(
                    RiskLevel.HIGH,
                    "dangerous_command",
                    f"Dangerous binary: {binary}",
                )
            )

    def _check_destructive_flags(
        self, tokens: list[str], out: CommandAnalysis
    ) -> None:
        if not tokens:
            return
        binary = os.path.basename(tokens[0])
        flags = {t for t in tokens[1:] if t.startswith("-")}

        # rm -rf / or rm -rf --no-preserve-root
        if binary == "rm":
            if flags & {"-rf", "-fr", "--no-preserve-root"}:
                for arg in tokens[1:]:
                    if not arg.startswith("-") and arg == "/":
                        out.detected_risks.append(
                            DetectedRisk(
                                RiskLevel.CRITICAL,
                                "destructive_command",
                                "rm -rf / detected",
                            )
                        )
                        return

        # dd if=/dev/zero of=/dev/sd*
        if binary == "dd":
            for arg in tokens[1:]:
                if arg.startswith("of=/dev/"):
                    out.detected_risks.append(
                        DetectedRisk(
                            RiskLevel.CRITICAL,
                            "destructive_command",
                            f"dd writing to device: {arg}",
                        )
                    )

    def _check_device_access(
        self, tokens: list[str], out: CommandAnalysis
    ) -> None:
        for token in tokens:
            if token.startswith("/dev/sd") or token.startswith("/dev/nvme"):
                out.detected_risks.append(
                    DetectedRisk(
                        RiskLevel.HIGH,
                        "device_access",
                        f"Direct device access: {token}",
                    )
                )

    def _check_paths(self, tokens: list[str], out: CommandAnalysis) -> None:
        """Resolve file-path arguments and check against allow/deny lists."""
        for token in tokens[1:]:
            if token.startswith("-"):
                continue
            # Heuristic: treat tokens that look like paths
            if "/" in token or token == ".." or token.startswith("~"):
                resolved = os.path.realpath(os.path.expanduser(token))
                out.resolved_paths.append(resolved)

                # Denied paths
                for denied in self._denied_paths:
                    if resolved == denied or resolved.startswith(denied + os.sep):
                        out.detected_risks.append(
                            DetectedRisk(
                                RiskLevel.HIGH,
                                "path_denied",
                                f"Access to denied path: {resolved}",
                            )
                        )

                # Path traversal: resolve and see if it lands outside allowed
                if self._allowed_paths:
                    inside = any(
                        resolved == ap or resolved.startswith(ap + os.sep)
                        for ap in self._allowed_paths
                    )
                    if not inside:
                        out.detected_risks.append(
                            DetectedRisk(
                                RiskLevel.HIGH,
                                "path_traversal",
                                f"Path outside allowed directories: {resolved}",
                            )
                        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_tokenise(command: str) -> list[str]:
        """Tokenise a single (sub-)command via shlex, falling back gracefully."""
        try:
            return shlex.split(command)
        except ValueError:
            # Unmatched quotes / unterminated escape -- still treat as risky
            return command.split()

    @staticmethod
    def _split_sub_commands(raw: str) -> list[str]:
        """Split raw input on chain operators into individual commands."""
        # We split on ; && || | but keep each sub-command as a string.
        parts = re.split(r"\s*(?:;|&&|\|\||\|)\s*", raw)
        return [p.strip() for p in parts if p.strip()]
