from agentic_core.domain.value_objects.tools import ToolError, ToolHealthStatus, ToolResult


def test_tool_health_healthy():
    h = ToolHealthStatus(tool_name="mcp_github_create_issue", healthy=True)
    assert h.healthy is True
    assert h.reason is None


def test_tool_health_unhealthy():
    h = ToolHealthStatus(
        tool_name="mcp_slack_send", healthy=False, reason="MCP server disconnected"
    )
    assert h.healthy is False
    assert "disconnected" in h.reason  # type: ignore[operator]


def test_tool_result_success():
    r = ToolResult(success=True, output='{"id": 123}')
    assert r.success is True
    assert r.error is None


def test_tool_result_failure():
    err = ToolError(code="capability_missing", message="subagent not available", retriable=False)
    r = ToolResult(success=False, error=err)
    assert r.success is False
    assert r.error is not None
    assert r.error.code == "capability_missing"
    assert r.error.retriable is False


def test_tool_error_codes():
    for code in ("not_found", "execution_failed", "capability_missing", "timeout"):
        err = ToolError(code=code, message="test", retriable=True)  # type: ignore[arg-type]
        assert err.code == code
