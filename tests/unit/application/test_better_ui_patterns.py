"""Unit tests for better-UI / coding-agent patterns:
HITL confirmation, tool views, coding primitives, tool cache, context budget."""

from __future__ import annotations

import asyncio
import time

import pytest

from agentic_core.application.services.hitl_confirmation import (
    ConfirmationMode,
    HITLConfirmationService,
    ToolHints,
)
from agentic_core.application.services.tool_views import (
    ToolViewRegistry,
    ToolViewSpec,
    ViewType,
)
from agentic_core.application.services.coding_tools import (
    BashTool,
    FileEditTool,
    FileReadTool,
    ListFilesTool,
)
from agentic_core.application.services.tool_cache import (
    CacheConfig,
    ToolCache,
)
from agentic_core.application.services.context_budget import (
    ContextBudgetManager,
)


# ---------------------------------------------------------------------------
# HITL Confirmation Service
# ---------------------------------------------------------------------------

def test_hitl_configure_tool_mode() -> None:
    svc = HITLConfirmationService()
    svc.configure_tool("deploy", mode=ConfirmationMode.ALWAYS)
    cfg = svc.get_tool_config("deploy")
    assert cfg["mode"] == "always"


def test_hitl_requires_confirmation_always() -> None:
    svc = HITLConfirmationService()
    svc.configure_tool("deploy", mode=ConfirmationMode.ALWAYS)
    assert svc.requires_confirmation("deploy", {}) is True
    assert svc.requires_confirmation("read_file", {}) is False


def test_hitl_destructive_auto_flag() -> None:
    svc = HITLConfirmationService()
    svc.configure_tool("rm_rf", mode=ConfirmationMode.NEVER, hints=[ToolHints.DESTRUCTIVE])
    # Destructive hint should override NEVER -> ALWAYS
    assert svc.requires_confirmation("rm_rf", {}) is True


def test_hitl_pending_count() -> None:
    svc = HITLConfirmationService()
    assert svc.pending_count == 0


# ---------------------------------------------------------------------------
# Tool Views
# ---------------------------------------------------------------------------

def test_tool_views_register_and_get() -> None:
    reg = ToolViewRegistry()
    spec = ToolViewSpec(view_type=ViewType.CHART, schema={"x": "time", "y": "value"})
    reg.register("analytics", spec)
    assert reg.get("analytics") is spec
    assert reg.get("analytics").view_type == ViewType.CHART


def test_tool_views_get_returns_none_for_unknown() -> None:
    reg = ToolViewRegistry()
    assert reg.get("nonexistent") is None


def test_tool_views_defaults_exist() -> None:
    reg = ToolViewRegistry()
    assert reg.has_view("search")
    assert reg.has_view("code_edit")
    assert reg.has_view("file_read")
    assert reg.has_view("confirmation")
    assert reg.has_view("progress")


def test_tool_views_catalog_export() -> None:
    reg = ToolViewRegistry()
    catalog = reg.to_catalog()
    assert isinstance(catalog, list)
    assert len(catalog) >= 5
    names = [entry["tool"] for entry in catalog]
    assert "search" in names
    for entry in catalog:
        assert "view_type" in entry
        assert "schema" in entry
        assert "streaming" in entry


# ---------------------------------------------------------------------------
# Coding Tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coding_file_read(tmp_path) -> None:
    f = tmp_path / "hello.txt"
    f.write_text("line1\nline2\nline3\n")
    tool = FileReadTool()
    result = await tool.execute(str(f))
    assert "line1" in result["content"]
    assert result["total_lines"] == 3


@pytest.mark.asyncio
async def test_coding_file_edit_unique_match(tmp_path) -> None:
    f = tmp_path / "code.py"
    f.write_text("x = 1\ny = 2\n")
    tool = FileEditTool()
    result = await tool.execute(str(f), old_str="x = 1", new_str="x = 42")
    assert result["status"] == "OK"
    assert "x = 42" in f.read_text()


@pytest.mark.asyncio
async def test_coding_list_files(tmp_path) -> None:
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    tool = ListFilesTool()
    result = await tool.execute(str(tmp_path), pattern="*.py")
    assert result["total"] == 2
    assert "a.py" in result["files"]


@pytest.mark.asyncio
async def test_coding_bash_execute() -> None:
    tool = BashTool()
    result = await tool.execute("echo hello")
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]


# ---------------------------------------------------------------------------
# Tool Cache
# ---------------------------------------------------------------------------

def test_cache_put_and_get() -> None:
    cache = ToolCache()
    cache.put("search", {"q": "foo"}, {"results": [1, 2]})
    assert cache.get("search", {"q": "foo"}) == {"results": [1, 2]}


def test_cache_ttl_expiry() -> None:
    cache = ToolCache()
    cache.configure_tool("fast", CacheConfig(ttl_seconds=0.01))
    cache.put("fast", {"a": 1}, "value")
    time.sleep(0.05)
    assert cache.get("fast", {"a": 1}) is None


def test_cache_invalidate() -> None:
    cache = ToolCache()
    cache.put("search", {"q": "a"}, "r1")
    cache.put("search", {"q": "b"}, "r2")
    removed = cache.invalidate("search")
    assert removed == 2
    assert cache.get("search", {"q": "a"}) is None


def test_cache_stats() -> None:
    cache = ToolCache()
    cache.put("t", {"x": 1}, "v")
    cache.get("t", {"x": 1})  # hit
    cache.get("t", {"x": 2})  # miss
    s = cache.stats
    assert s["hits"] == 1
    assert s["misses"] == 1
    assert s["size"] == 1


# ---------------------------------------------------------------------------
# Context Budget
# ---------------------------------------------------------------------------

def test_budget_allocate() -> None:
    mgr = ContextBudgetManager()
    assert mgr.allocate("system_prompt", 3000) is True
    assert mgr.allocate("system_prompt", 999999) is False  # exceeds max


def test_budget_available() -> None:
    mgr = ContextBudgetManager()
    full = mgr.available()
    mgr.allocate("conversation", 50000)
    assert mgr.available() == full - 50000


def test_budget_max_tools() -> None:
    mgr = ContextBudgetManager()
    # Default tool_definitions max = 8000, 200 per tool -> 40 tools
    assert mgr.max_tools() == 40
    assert mgr.max_tools(avg_tokens_per_tool=400) == 20


def test_budget_utilization() -> None:
    mgr = ContextBudgetManager()
    assert mgr.utilization() == 0.0
    mgr.allocate("conversation", 88000)
    assert mgr.utilization() == 88000 / 176000
