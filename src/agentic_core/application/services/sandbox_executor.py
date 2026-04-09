"""Sandbox executor -- real process isolation for tool execution."""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class SandboxBackend(StrEnum):
    LOCAL = "local"  # No isolation (development only)
    DOCKER = "docker"  # Docker container
    PODMAN = "podman"  # Podman container (rootless)


class SandboxPermission(StrEnum):
    READ_FILESYSTEM = "read_filesystem"
    WRITE_FILESYSTEM = "write_filesystem"
    NETWORK_EGRESS = "network_egress"
    EXECUTE_SHELL = "execute_shell"
    READ_ENV = "read_env"


@dataclass
class SandboxPolicy:
    """Security policy for a sandbox instance."""

    allowed_paths: list[str] = field(default_factory=lambda: ["/tmp", "/sandbox"])
    denied_paths: list[str] = field(
        default_factory=lambda: ["/etc/passwd", "/etc/shadow", "~/.ssh"],
    )
    allowed_egress: list[str] = field(default_factory=list)  # Empty = deny all
    permissions: set[SandboxPermission] = field(
        default_factory=lambda: {SandboxPermission.READ_FILESYSTEM},
    )
    max_execution_seconds: int = 300
    max_memory_mb: int = 512
    read_only_root: bool = True
    drop_capabilities: bool = True


@dataclass
class SandboxResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    policy_violations: list[str] = field(default_factory=list)


class SandboxExecutor:
    """Executes commands in isolated sandbox environments."""

    def __init__(
        self,
        backend: SandboxBackend = SandboxBackend.LOCAL,
        default_policy: SandboxPolicy | None = None,
    ) -> None:
        self._backend = backend
        self._default_policy = default_policy or SandboxPolicy()
        self._audit_log: list[dict[str, Any]] = []

    async def execute(
        self,
        command: str,
        policy: SandboxPolicy | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute a command within the sandbox."""
        policy = policy or self._default_policy

        # Pre-execution policy check
        violations = self._check_policy(command, policy)
        if violations:
            self._log_audit("denied", command, violations)
            return SandboxResult(exit_code=1, policy_violations=violations)

        self._log_audit("allowed", command, [])

        if self._backend == SandboxBackend.LOCAL:
            return await self._execute_local(command, policy, env)
        elif self._backend in (SandboxBackend.DOCKER, SandboxBackend.PODMAN):
            return await self._execute_container(command, policy, env)

        return SandboxResult(exit_code=1, stderr=f"Unknown backend: {self._backend}")

    async def _execute_local(
        self,
        command: str,
        policy: SandboxPolicy,
        env: dict[str, str] | None,
    ) -> SandboxResult:
        """Execute locally with basic restrictions (development only).

        NOTE: This uses subprocess for sandboxed command execution.
        This is intentional -- the sandbox executor IS the isolation layer.
        """
        try:
            proc_env = dict(os.environ)
            if env:
                proc_env.update(env)
            if SandboxPermission.READ_ENV not in policy.permissions:
                # Strip sensitive env vars
                for key in list(proc_env.keys()):
                    if any(
                        s in key.upper()
                        for s in ["KEY", "SECRET", "TOKEN", "PASSWORD"]
                    ):
                        del proc_env[key]

            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=proc_env,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=policy.max_execution_seconds,
                )
                return SandboxResult(
                    stdout=stdout.decode()[-5000:],
                    stderr=stderr.decode()[-2000:],
                    exit_code=proc.returncode or 0,
                )
            except TimeoutError:
                proc.kill()
                return SandboxResult(
                    exit_code=-1,
                    timed_out=True,
                    stderr="Execution timed out",
                )
        except Exception as e:
            return SandboxResult(exit_code=1, stderr=str(e))

    async def _execute_container(
        self,
        command: str,
        policy: SandboxPolicy,
        env: dict[str, str] | None,
    ) -> SandboxResult:
        """Execute in a Docker/Podman container with full isolation.

        NOTE: This uses subprocess to invoke docker/podman CLI.
        This is intentional -- the container runtime IS the isolation boundary.
        """
        runtime = "podman" if self._backend == SandboxBackend.PODMAN else "docker"

        args = [runtime, "run", "--rm"]

        # Security flags
        if policy.read_only_root:
            args.append("--read-only")
        if policy.drop_capabilities:
            args.extend(["--cap-drop", "ALL"])

        # Memory limit
        args.extend(["--memory", f"{policy.max_memory_mb}m"])

        # Network
        if SandboxPermission.NETWORK_EGRESS not in policy.permissions:
            args.extend(["--network", "none"])

        # Mount allowed paths as tmpfs
        args.extend(["--tmpfs", "/tmp:rw,size=100m"])

        # Env vars
        if env:
            for k, v in env.items():
                args.extend(["-e", f"{k}={v}"])

        # Image and command
        args.extend(["python:3.12-slim", "sh", "-c", command])

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=policy.max_execution_seconds,
            )
            return SandboxResult(
                stdout=stdout.decode()[-5000:],
                stderr=stderr.decode()[-2000:],
                exit_code=proc.returncode or 0,
            )
        except TimeoutError:
            return SandboxResult(exit_code=-1, timed_out=True)
        except FileNotFoundError:
            return SandboxResult(exit_code=1, stderr=f"{runtime} not found")

    def _check_policy(self, command: str, policy: SandboxPolicy) -> list[str]:
        """Pre-execution policy checks using structural command analysis."""
        from agentic_core.application.services.command_parser import CommandParser

        violations: list[str] = []

        # Check shell permission first (cheap gate)
        if SandboxPermission.EXECUTE_SHELL not in policy.permissions:
            violations.append("Shell execution not permitted")

        # Structural analysis via CommandParser
        parser = CommandParser(
            allowed_paths=list(policy.allowed_paths),
            denied_paths=list(policy.denied_paths),
        )
        analysis = parser.analyse(command)
        violations.extend(analysis.violation_messages)

        return violations

    def _log_audit(
        self,
        decision: str,
        command: str,
        violations: list[str],
    ) -> None:
        """Log security audit trail entry."""
        import time

        self._audit_log.append(
            {
                "timestamp": time.time(),
                "decision": decision,
                "command": command[:200],
                "violations": violations,
                "backend": self._backend.value,
            }
        )

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return self._audit_log

    @property
    def backend(self) -> SandboxBackend:
        return self._backend
