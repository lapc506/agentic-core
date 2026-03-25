from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ToolHealthStatus(BaseModel, frozen=True):
    tool_name: str
    healthy: bool
    reason: str | None = None


class ToolError(BaseModel, frozen=True):
    code: Literal["not_found", "execution_failed", "capability_missing", "timeout"]
    message: str
    retriable: bool


class ToolResult(BaseModel, frozen=True):
    success: bool
    output: str | None = None
    error: ToolError | None = None
