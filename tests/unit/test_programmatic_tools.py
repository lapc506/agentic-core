from __future__ import annotations

from agentic_core.application.services.programmatic_tools import (
    CodeExecutionConfig,
    CodeExecutionResult,
    ProgrammaticToolExecutor,
)

# ── Config defaults ──────────────────────────────────────────────


def test_config_defaults() -> None:
    cfg = CodeExecutionConfig()
    assert cfg.timeout_seconds == 30
    assert cfg.max_output_bytes == 1_048_576
    assert "math" in cfg.allowed_modules


def test_config_custom() -> None:
    cfg = CodeExecutionConfig(timeout_seconds=10, max_output_bytes=2048)
    assert cfg.timeout_seconds == 10
    assert cfg.max_output_bytes == 2048


# ── Result immutability ──────────────────────────────────────────


def test_result_frozen() -> None:
    result = CodeExecutionResult(success=True, output="hi")
    try:
        result.success = False  # type: ignore[misc]
        raise AssertionError("Expected frozen model to reject mutation")
    except Exception:
        pass
    assert result.success is True


# ── Simple execution ─────────────────────────────────────────────


def test_execute_simple_print() -> None:
    executor = ProgrammaticToolExecutor()
    result = executor.execute('print("hello world")')
    assert result.success is True
    assert "hello world" in result.output
    assert result.execution_time_ms >= 0


def test_execute_math() -> None:
    executor = ProgrammaticToolExecutor()
    result = executor.execute("x = 2 + 3\nprint(x)")
    assert result.success is True
    assert "5" in result.output


def test_execute_with_context() -> None:
    executor = ProgrammaticToolExecutor()
    result = executor.execute(
        "print(greeting + ' ' + name)",
        context={"greeting": "Hello", "name": "Agent"},
    )
    assert result.success is True
    assert "Hello Agent" in result.output


def test_execute_context_mutation() -> None:
    """Context variables are available but the original dict is not mutated."""
    ctx: dict[str, object] = {"items": [1, 2, 3]}
    executor = ProgrammaticToolExecutor()
    result = executor.execute("print(sum(items))", context=ctx)
    assert result.success is True
    assert "6" in result.output


# ── Validation / disallowed imports ──────────────────────────────


def test_validate_disallowed_subprocess() -> None:
    executor = ProgrammaticToolExecutor()
    violations = executor.validate_code("import subprocess\nsubprocess.run(['ls'])")
    assert len(violations) >= 1
    assert any("subprocess" in v for v in violations)


def test_validate_disallowed_os_system() -> None:
    executor = ProgrammaticToolExecutor()
    violations = executor.validate_code("import os\nos.system('echo hi')")
    assert len(violations) >= 1
    assert any("os.system" in v for v in violations)


def test_validate_disallowed_eval_builtin() -> None:
    executor = ProgrammaticToolExecutor()
    # The string "eval('1+1')" is intentionally disallowed input
    violations = executor.validate_code("result = eval('1+1')")  # noqa: S307
    assert len(violations) >= 1
    assert any("eval" in v for v in violations)


def test_execute_rejected_on_violations() -> None:
    executor = ProgrammaticToolExecutor()
    result = executor.execute("import subprocess\nsubprocess.run(['ls'])")
    assert result.success is False
    assert "validation failed" in result.error.lower()


def test_validate_clean_code() -> None:
    executor = ProgrammaticToolExecutor()
    violations = executor.validate_code("x = 1 + 2\nprint(x)")
    assert violations == []


# ── Output truncation ────────────────────────────────────────────


def test_output_truncation() -> None:
    cfg = CodeExecutionConfig(max_output_bytes=1024)
    executor = ProgrammaticToolExecutor(config=cfg)
    result = executor.execute("print('A' * 5000)")
    assert result.success is True
    assert len(result.output) <= 1024 + 1  # +1 for trailing newline char within limit


# ── Error handling ───────────────────────────────────────────────


def test_execute_runtime_error() -> None:
    executor = ProgrammaticToolExecutor()
    result = executor.execute("1 / 0")
    assert result.success is False
    assert "division by zero" in result.error.lower()
    assert result.execution_time_ms >= 0
