from __future__ import annotations

from agentic_core.application.services.sandbox import (
    SandboxBackend,
    SandboxConfig,
    SandboxExecutor,
    SandboxResult,
)

# ── Backend enum ────────────────────────────────────────────────


def test_sandbox_backend_values() -> None:
    assert SandboxBackend.LOCAL.value == "local"
    assert SandboxBackend.DOCKER.value == "docker"
    assert SandboxBackend.SSH.value == "ssh"
    assert SandboxBackend.MODAL.value == "modal"
    assert SandboxBackend.DAYTONA.value == "daytona"


# ── SandboxConfig ───────────────────────────────────────────────


def test_sandbox_config_defaults() -> None:
    cfg = SandboxConfig()
    assert cfg.backend == SandboxBackend.LOCAL
    assert cfg.docker_image is None
    assert cfg.ssh_host is None
    assert cfg.timeout_seconds == 180
    assert cfg.read_only_root is True
    assert cfg.network_enabled is False
    assert cfg.work_dir == "/workspace"


def test_sandbox_config_custom() -> None:
    cfg = SandboxConfig(
        backend=SandboxBackend.DOCKER,
        docker_image="python:3.12-slim",
        timeout_seconds=60,
        read_only_root=False,
        network_enabled=True,
        work_dir="/app",
    )
    assert cfg.backend == SandboxBackend.DOCKER
    assert cfg.docker_image == "python:3.12-slim"
    assert cfg.timeout_seconds == 60
    assert cfg.read_only_root is False
    assert cfg.network_enabled is True
    assert cfg.work_dir == "/app"


# ── SandboxResult ───────────────────────────────────────────────


def test_sandbox_result_construction() -> None:
    result = SandboxResult(
        success=True,
        stdout="hello",
        stderr="",
        exit_code=0,
        execution_time_ms=42,
    )
    assert result.success is True
    assert result.stdout == "hello"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert result.execution_time_ms == 42


def test_sandbox_result_is_frozen() -> None:
    result = SandboxResult(
        success=True, stdout="", stderr="", exit_code=0, execution_time_ms=0
    )
    try:
        result.success = False  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised, "SandboxResult should be frozen"


# ── SandboxExecutor ─────────────────────────────────────────────


def test_executor_default_config() -> None:
    executor = SandboxExecutor()
    assert executor.config.backend == SandboxBackend.LOCAL


def test_executor_exposes_config() -> None:
    cfg = SandboxConfig(backend=SandboxBackend.SSH, ssh_host="10.0.0.1")
    executor = SandboxExecutor(config=cfg)
    assert executor.config.ssh_host == "10.0.0.1"


def test_execute_local_returns_success() -> None:
    executor = SandboxExecutor()
    result = executor.execute("echo hello")
    assert result.success is True
    assert result.exit_code == 0
    assert result.execution_time_ms >= 0


def test_execute_nonlocal_returns_stub() -> None:
    cfg = SandboxConfig(backend=SandboxBackend.DOCKER, docker_image="alpine")
    executor = SandboxExecutor(config=cfg)
    result = executor.execute("ls")
    assert result.success is False
    assert result.exit_code == 1
    assert "not yet implemented" in result.stderr


def test_is_available_local() -> None:
    executor = SandboxExecutor()
    assert executor.is_available() is True


def test_is_available_docker_without_image() -> None:
    cfg = SandboxConfig(backend=SandboxBackend.DOCKER)
    executor = SandboxExecutor(config=cfg)
    assert executor.is_available() is False


def test_is_available_docker_with_image() -> None:
    cfg = SandboxConfig(backend=SandboxBackend.DOCKER, docker_image="alpine")
    executor = SandboxExecutor(config=cfg)
    assert executor.is_available() is True


def test_is_available_ssh_without_host() -> None:
    cfg = SandboxConfig(backend=SandboxBackend.SSH)
    executor = SandboxExecutor(config=cfg)
    assert executor.is_available() is False


def test_is_available_ssh_with_host() -> None:
    cfg = SandboxConfig(backend=SandboxBackend.SSH, ssh_host="example.com")
    executor = SandboxExecutor(config=cfg)
    assert executor.is_available() is True


def test_is_available_modal_not_supported() -> None:
    cfg = SandboxConfig(backend=SandboxBackend.MODAL)
    executor = SandboxExecutor(config=cfg)
    assert executor.is_available() is False
