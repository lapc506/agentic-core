from __future__ import annotations

import ast
import io
import logging
import time
from contextlib import redirect_stdout
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Modules / attributes that must never appear in executed code
_DISALLOWED_IMPORTS: frozenset[str] = frozenset(
    {
        "subprocess",
        "shutil",
        "ctypes",
        "importlib",
        "pickle",
        "shelve",
        "socket",
        "http",
        "ftplib",
        "smtplib",
        "webbrowser",
        "multiprocessing",
        "signal",
    }
)

_DISALLOWED_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "os.system",
        "os.popen",
        "os.exec",
        "os.execvp",
        "os.execvpe",
        "os.spawn",
        "os.remove",
        "os.unlink",
        "os.rmdir",
        "os.rename",
        "eval",
        "exec",
        "compile",
        "__import__",
    }
)


class CodeExecutionConfig(BaseModel):
    """Configuration for the sandboxed code executor."""

    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_output_bytes: int = Field(default=1_048_576, ge=1024)  # 1 MB
    allowed_modules: list[str] = Field(
        default_factory=lambda: ["math", "json", "re", "datetime", "collections", "itertools", "functools"],
    )


class CodeExecutionResult(BaseModel, frozen=True):
    """Immutable result of a code execution."""

    success: bool
    output: str = ""
    error: str = ""
    execution_time_ms: float = 0.0


class ProgrammaticToolExecutor:
    """Execute Python code strings with restricted globals and captured stdout.

    Intended for chaining multiple tool calls with conditional logic in a
    sandboxed environment.
    """

    def __init__(self, config: CodeExecutionConfig | None = None) -> None:
        self._config = config or CodeExecutionConfig()

    @property
    def config(self) -> CodeExecutionConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_code(self, code: str) -> list[str]:
        """Static analysis: return a list of violation messages.

        Checks for disallowed imports and dangerous attribute access.
        """
        violations: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            violations.append(f"SyntaxError: {exc}")
            return violations

        for node in ast.walk(tree):
            # import <module>
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in _DISALLOWED_IMPORTS:
                        violations.append(f"Disallowed import: {alias.name}")

            # from <module> import ...
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    if top in _DISALLOWED_IMPORTS:
                        violations.append(f"Disallowed import: {node.module}")

            # Attribute access like os.system
            elif isinstance(node, ast.Attribute):
                full = _resolve_attribute(node)
                if full is not None:
                    for disallowed in _DISALLOWED_ATTRIBUTES:
                        if full == disallowed or full.startswith(disallowed + "."):
                            violations.append(f"Disallowed attribute: {full}")

            # Bare calls to eval / exec / __import__
            elif isinstance(node, ast.Name):
                if node.id in _DISALLOWED_ATTRIBUTES:
                    violations.append(f"Disallowed builtin: {node.id}")

        return violations

    def execute(self, code: str, context: dict[str, Any] | None = None) -> CodeExecutionResult:
        """Execute *code* with an optional *context* dict injected as local variables.

        Returns a :class:`CodeExecutionResult` with captured stdout or error info.
        """
        violations = self.validate_code(code)
        if violations:
            return CodeExecutionResult(
                success=False,
                error="Code validation failed: " + "; ".join(violations),
            )

        # Build restricted globals (no __builtins__ leak beyond safe set)
        raw_builtins: dict[str, Any] = __builtins__  # type: ignore[assignment]
        if not isinstance(raw_builtins, dict):
            raw_builtins = vars(__builtins__)

        safe_builtins: dict[str, Any] = {
            k: v
            for k, v in raw_builtins.items()
            if k not in {"eval", "exec", "compile", "__import__", "open", "breakpoint", "exit", "quit"}
        }
        restricted_globals: dict[str, Any] = {"__builtins__": safe_builtins}

        local_vars: dict[str, Any] = dict(context) if context else {}

        stdout_buf = io.StringIO()
        start = time.monotonic()

        try:
            compiled = compile(code, "<programmatic_tool>", "exec")
            with redirect_stdout(stdout_buf):
                _safe_exec(compiled, restricted_globals, local_vars)
        except Exception as exc:  # noqa: BLE001
            elapsed = (time.monotonic() - start) * 1000
            logger.debug("Code execution failed in %.1f ms: %s", elapsed, exc)
            return CodeExecutionResult(
                success=False,
                output=stdout_buf.getvalue()[: self._config.max_output_bytes],
                error=str(exc),
                execution_time_ms=round(elapsed, 2),
            )

        elapsed = (time.monotonic() - start) * 1000
        raw_output = stdout_buf.getvalue()
        truncated = raw_output[: self._config.max_output_bytes]

        logger.debug("Code executed in %.1f ms, output=%d bytes", elapsed, len(raw_output))

        return CodeExecutionResult(
            success=True,
            output=truncated,
            execution_time_ms=round(elapsed, 2),
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _safe_exec(
    compiled: Any,
    restricted_globals: dict[str, Any],
    local_vars: dict[str, Any],
) -> None:
    """Thin wrapper so the security-sensitive call is isolated."""
    exec(compiled, restricted_globals, local_vars)  # noqa: S102


def _resolve_attribute(node: ast.Attribute) -> str | None:
    """Resolve a dotted attribute chain to a string like 'os.system'."""
    parts: list[str] = [node.attr]
    current: ast.expr = node.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None
