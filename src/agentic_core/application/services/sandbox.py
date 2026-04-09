"""Execution environments: Docker, SSH, remote sandboxed execution (#64)."""
from __future__ import annotations

import logging
import time
from enum import StrEnum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SandboxBackend(StrEnum):
    """Supported sandbox execution backends."""

    LOCAL = "local"
    DOCKER = "docker"
    SSH = "ssh"
    MODAL = "modal"
    DAYTONA = "daytona"


class SandboxConfig(BaseModel):
    """Configuration for a sandboxed execution environment."""

    backend: SandboxBackend = SandboxBackend.LOCAL
    docker_image: str | None = Field(default=None)
    ssh_host: str | None = Field(default=None)
    timeout_seconds: int = Field(default=180, ge=1)
    read_only_root: bool = Field(default=True)
    network_enabled: bool = Field(default=False)
    work_dir: str = Field(default="/workspace")


class SandboxResult(BaseModel, frozen=True):
    """Immutable result of a sandboxed command execution."""

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int


class SandboxExecutor:
    """Execute commands in isolated sandbox environments.

    Currently provides a placeholder implementation.  Non-LOCAL backends
    return a stub result; LOCAL executes nothing for safety.  Real
    provider adapters (Docker SDK, paramiko, Modal client, Daytona API)
    will be injected once the adapter layer is implemented.
    """

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self._config = config or SandboxConfig()

    @property
    def config(self) -> SandboxConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        command: str,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute *command* in the configured sandbox backend.

        Returns a stub result for non-LOCAL backends.  LOCAL returns a
        safe no-op result to prevent accidental host execution.
        """
        start = time.monotonic()
        logger.info(
            "Sandbox execute (placeholder): backend=%s, command=%r",
            self._config.backend.value,
            command,
        )

        if self._config.backend == SandboxBackend.LOCAL:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return SandboxResult(
                success=True,
                stdout="",
                stderr="",
                exit_code=0,
                execution_time_ms=elapsed_ms,
            )

        # Non-LOCAL backends: stub until real adapters are wired
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return SandboxResult(
            success=False,
            stdout="",
            stderr=f"Backend '{self._config.backend.value}' not yet implemented",
            exit_code=1,
            execution_time_ms=elapsed_ms,
        )

    def is_available(self) -> bool:
        """Check whether the configured backend is ready for use.

        LOCAL is always available.  DOCKER and SSH require their
        respective configuration fields.  MODAL and DAYTONA are not
        yet supported.
        """
        backend = self._config.backend
        if backend == SandboxBackend.LOCAL:
            return True
        if backend == SandboxBackend.DOCKER:
            return self._config.docker_image is not None
        if backend == SandboxBackend.SSH:
            return self._config.ssh_host is not None
        # MODAL / DAYTONA – not yet wired
        return False
