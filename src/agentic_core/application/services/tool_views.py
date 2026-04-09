"""Tool view specifications — tools declare their own UI rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ViewType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    FORM = "form"
    CODE = "code"
    PROGRESS = "progress"
    CHART = "chart"
    CONFIRMATION = "confirmation"
    FILE_UPLOAD = "file_upload"
    MEDIA = "media"


@dataclass
class ToolViewSpec:
    """Declares how a tool's results should be rendered in the UI."""
    view_type: ViewType
    schema: dict[str, Any] = field(default_factory=dict)
    layout_hints: dict[str, Any] = field(default_factory=dict)
    streaming: bool = False
    auto_respond: bool = False


class ToolViewRegistry:
    """Registry mapping tools to their view specifications."""

    def __init__(self) -> None:
        self._views: dict[str, ToolViewSpec] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._views["search"] = ToolViewSpec(
            view_type=ViewType.TABLE,
            schema={"columns": ["title", "url", "snippet"]},
        )
        self._views["code_edit"] = ToolViewSpec(
            view_type=ViewType.CODE,
            schema={"language": "auto", "diff": True},
        )
        self._views["file_read"] = ToolViewSpec(
            view_type=ViewType.CODE,
            schema={"language": "auto", "line_numbers": True},
        )
        self._views["confirmation"] = ToolViewSpec(
            view_type=ViewType.CONFIRMATION,
            schema={"actions": ["approve", "reject"]},
            auto_respond=True,
        )
        self._views["progress"] = ToolViewSpec(
            view_type=ViewType.PROGRESS,
            schema={"show_percentage": True, "show_eta": True},
            streaming=True,
        )

    def register(self, tool_name: str, view: ToolViewSpec) -> None:
        self._views[tool_name] = view

    def get(self, tool_name: str) -> ToolViewSpec | None:
        return self._views.get(tool_name)

    def has_view(self, tool_name: str) -> bool:
        return tool_name in self._views

    def list_tools_with_views(self) -> list[str]:
        return list(self._views.keys())

    def to_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "tool": name,
                "view_type": view.view_type.value,
                "schema": view.schema,
                "streaming": view.streaming,
                "auto_respond": view.auto_respond,
            }
            for name, view in self._views.items()
        ]
