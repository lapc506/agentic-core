"""Tests for the 4 critical security fixes.

Covers:
  1. JWT validation (valid, expired, invalid signature, bypass mode)
  2. File path validation (traversal, denied patterns, workspace boundary)
  3. CORS middleware (allowed origin, denied origin)
"""
from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jwt
import pytest
import uuid_utils
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from agentic_core.application.middleware.auth import AuthMiddleware
from agentic_core.application.middleware.base import MiddlewareChain, RequestContext
from agentic_core.application.services.coding_tools import (
    DENIED_PATTERNS,
    FileEditTool,
    FileReadTool,
    _validate_path,
)
from agentic_core.domain.value_objects.messages import AgentMessage

# Pydantic needs the real datetime type resolved (it is behind TYPE_CHECKING
# in the module that defines AgentMessage).
AgentMessage.model_rebuild()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

JWT_SECRET = "test-secret-key-that-is-long-enough-for-hs256"


def _msg(content: str = "hello", **meta: object) -> AgentMessage:
    return AgentMessage(
        id=str(uuid_utils.uuid7()),
        session_id="s1",
        persona_id="p1",
        role="user",
        content=content,
        metadata=meta,
        timestamp=datetime.now(UTC),
    )


async def _echo(message: AgentMessage, ctx: RequestContext) -> AgentMessage:
    return message


def _make_token(payload: dict, secret: str = JWT_SECRET) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


# ===================================================================
# Fix 1 — JWT validation
# ===================================================================


class TestJWTValidation:
    """AuthMiddleware must validate JWT signature, expiry, and user_id."""

    async def test_valid_token_passes(self):
        token = _make_token({"user_id": "u42", "exp": time.time() + 3600})
        mw = AuthMiddleware(api_keys={"k"}, jwt_secret=JWT_SECRET)
        chain = MiddlewareChain([mw], _echo)
        msg = _msg(authorization=f"Bearer {token}")
        ctx = RequestContext()
        result = await chain(msg, ctx)
        assert result is not None
        assert ctx.user_id == "u42"

    async def test_expired_token_rejected(self):
        token = _make_token({"user_id": "u1", "exp": time.time() - 10})
        mw = AuthMiddleware(api_keys={"k"}, jwt_secret=JWT_SECRET)
        chain = MiddlewareChain([mw], _echo)
        msg = _msg(authorization=f"Bearer {token}")
        with pytest.raises(PermissionError, match="expired"):
            await chain(msg, RequestContext())

    async def test_invalid_signature_rejected(self):
        token = _make_token({"user_id": "u1", "exp": time.time() + 3600}, secret="wrong-secret-that-is-long-enough-for-hs256")
        mw = AuthMiddleware(api_keys={"k"}, jwt_secret=JWT_SECRET)
        chain = MiddlewareChain([mw], _echo)
        msg = _msg(authorization=f"Bearer {token}")
        with pytest.raises(PermissionError, match="Invalid token"):
            await chain(msg, RequestContext())

    async def test_bypass_mode(self):
        with patch.dict(os.environ, {"AGENTIC_AUTH_BYPASS": "true"}):
            mw = AuthMiddleware(api_keys={"k"}, jwt_secret=JWT_SECRET)
        chain = MiddlewareChain([mw], _echo)
        msg = _msg()  # no auth at all
        ctx = RequestContext()
        result = await chain(msg, ctx)
        assert result is not None
        assert ctx.user_id == "bypass_user"


# ===================================================================
# Fix 2 — File-path validation
# ===================================================================


class TestFilePathSecurity:
    """FileReadTool / FileEditTool must block traversal and sensitive files."""

    def test_path_traversal_blocked(self, tmp_path: Path):
        outside = tmp_path / "outside.txt"
        outside.write_text("secret")
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        with pytest.raises(PermissionError, match="outside workspace"):
            _validate_path(str(outside), str(workspace))

    def test_denied_patterns_blocked(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        evil = workspace / ".env"
        evil.write_text("SECRET=123")
        with pytest.raises(PermissionError, match="Access denied"):
            _validate_path(str(evil), str(workspace))

    def test_workspace_boundary_enforced(self, tmp_path: Path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        traversal_path = str(workspace / ".." / "outside.txt")
        with pytest.raises(PermissionError, match="outside workspace"):
            _validate_path(traversal_path, str(workspace))

    async def test_file_read_tool_rejects_traversal(self, tmp_path: Path):
        workspace = tmp_path / "ws"
        workspace.mkdir()
        tool = FileReadTool(workspace_root=str(workspace))
        result = await tool.execute(str(tmp_path / "secret.txt"))
        assert "error" in result
        assert "outside workspace" in result["error"].lower()

    async def test_file_edit_tool_rejects_denied_pattern(self, tmp_path: Path):
        workspace = tmp_path / "ws"
        workspace.mkdir()
        target = workspace / ".env"
        target.write_text("old")
        tool = FileEditTool(workspace_root=str(workspace))
        result = await tool.execute(str(target), "old", "new")
        assert "error" in result
        assert "access denied" in result["error"].lower()


# ===================================================================
# Fix 4 — CORS middleware
# ===================================================================


class TestCORSMiddleware:
    """CORS headers must only appear for allowed origins."""

    def _build_app(self) -> web.Application:
        from agentic_core.adapters.primary.http_api import cors_middleware

        async def dummy_handler(request: web.Request) -> web.Response:
            return web.json_response({"ok": True})

        app = web.Application(middlewares=[cors_middleware])
        app.router.add_get("/test", dummy_handler)
        # Provide settings so _get_allowed_origins can resolve the port
        app["settings"] = {"http_port": 8080}
        return app

    async def test_allowed_origin_gets_headers(self, aiohttp_client):
        client = await aiohttp_client(self._build_app())
        resp = await client.get("/test", headers={"Origin": "http://localhost:8080"})
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:8080"
        assert "Authorization" in resp.headers.get("Access-Control-Allow-Headers", "")

    async def test_denied_origin_no_cors_headers(self, aiohttp_client):
        client = await aiohttp_client(self._build_app())
        resp = await client.get("/test", headers={"Origin": "http://evil.example.com"})
        assert resp.status == 200
        assert "Access-Control-Allow-Origin" not in resp.headers
