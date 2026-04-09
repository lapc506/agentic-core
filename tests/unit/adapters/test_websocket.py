from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import websockets

from agentic_core.adapters.primary.websocket import WebSocketTransport

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
async def transport():
    t = WebSocketTransport(host="127.0.0.1", port=0, max_sessions_per_connection=3)

    async def mock_create(persona_id: str, user_id: str) -> str:
        return "test_session_001"

    async def mock_message(session_id: str, persona_id: str, content: str) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "stream_token", "session_id": session_id, "token": "Hello"}
        yield {"type": "stream_token", "session_id": session_id, "token": " world"}

    t.on_create_session = mock_create
    t.on_message = mock_message

    await t.start()
    # Get actual port from the server
    port = t._server.sockets[0].getsockname()[1]
    t._actual_port = port
    yield t
    await t.stop()


def _url(transport: WebSocketTransport) -> str:
    return f"ws://127.0.0.1:{transport._actual_port}"


async def test_start_stop(transport: WebSocketTransport):
    assert transport.is_running


async def test_create_session(transport: WebSocketTransport):
    async with websockets.connect(_url(transport)) as ws:
        await ws.send(json.dumps({
            "type": "create_session",
            "persona_id": "support",
            "user_id": "u1",
        }))
        resp = json.loads(await ws.recv())
        assert resp["type"] == "session_created"
        assert resp["session_id"] == "test_session_001"


async def test_message_streaming(transport: WebSocketTransport):
    async with websockets.connect(_url(transport)) as ws:
        # Create session first
        await ws.send(json.dumps({
            "type": "create_session", "persona_id": "support", "user_id": "u1",
        }))
        await ws.recv()  # session_created

        # Send message
        await ws.send(json.dumps({
            "type": "message",
            "session_id": "test_session_001",
            "persona_id": "support",
            "content": "hello",
        }))

        msgs = []
        for _ in range(4):  # stream_start + 2 tokens + stream_end
            msgs.append(json.loads(await ws.recv()))

        types = [m["type"] for m in msgs]
        assert types == ["stream_start", "stream_token", "stream_token", "stream_end"]
        assert msgs[1]["token"] == "Hello"
        assert msgs[2]["token"] == " world"


async def test_message_without_session(transport: WebSocketTransport):
    async with websockets.connect(_url(transport)) as ws:
        await ws.send(json.dumps({
            "type": "message",
            "session_id": "nonexistent",
            "persona_id": "support",
            "content": "hi",
        }))
        resp = json.loads(await ws.recv())
        assert resp["type"] == "error"
        assert resp["code"] == "invalid_session"


async def test_close_session(transport: WebSocketTransport):
    async with websockets.connect(_url(transport)) as ws:
        await ws.send(json.dumps({
            "type": "create_session", "persona_id": "support", "user_id": "u1",
        }))
        await ws.recv()

        await ws.send(json.dumps({
            "type": "close_session", "session_id": "test_session_001",
        }))
        resp = json.loads(await ws.recv())
        assert resp["type"] == "session_closed"
        assert resp["session_id"] == "test_session_001"


async def test_invalid_json(transport: WebSocketTransport):
    async with websockets.connect(_url(transport)) as ws:
        await ws.send("not json {{{")
        resp = json.loads(await ws.recv())
        assert resp["type"] == "error"
        assert resp["code"] == "invalid_payload"


async def test_unknown_type(transport: WebSocketTransport):
    async with websockets.connect(_url(transport)) as ws:
        await ws.send(json.dumps({"type": "bogus"}))
        resp = json.loads(await ws.recv())
        assert resp["type"] == "error"
        assert resp["code"] == "invalid_payload"


async def test_session_limit(transport: WebSocketTransport):
    # max_sessions_per_connection=3
    async with websockets.connect(_url(transport)) as ws:
        for i in range(3):
            async def _make_session(p: str, u: str, idx: int = i) -> str:
                return f"sess_{idx}"
            transport.on_create_session = _make_session
            await ws.send(json.dumps({
                "type": "create_session", "persona_id": "p", "user_id": "u",
            }))
            await ws.recv()

        # 4th should fail
        await ws.send(json.dumps({
            "type": "create_session", "persona_id": "p", "user_id": "u",
        }))
        resp = json.loads(await ws.recv())
        assert resp["type"] == "error"
        assert resp["code"] == "session_limit_exceeded"


async def test_create_session_no_persona(transport: WebSocketTransport):
    async with websockets.connect(_url(transport)) as ws:
        await ws.send(json.dumps({
            "type": "create_session", "persona_id": "", "user_id": "u1",
        }))
        resp = json.loads(await ws.recv())
        assert resp["type"] == "error"
        assert resp["code"] == "invalid_persona"


# ---------------------------------------------------------------------------
# Origin validation tests (CVE-2026-25253 mitigation)
# ---------------------------------------------------------------------------


async def test_connection_rejected_for_bad_origin(transport: WebSocketTransport):
    """Connections from unauthorized origins are closed immediately."""
    try:
        async with websockets.connect(
            _url(transport),
            additional_headers={"Origin": "https://evil.attacker.com"},
        ) as ws:
            # Server should close the connection with code 4003
            await ws.recv()
            pytest.fail("Expected connection to be closed")
    except websockets.ConnectionClosed as exc:
        assert exc.rcvd.code == 4003


async def test_connection_allowed_for_localhost_origin(transport: WebSocketTransport):
    """Connections from localhost origin are allowed."""
    port = transport._actual_port
    async with websockets.connect(
        _url(transport),
        additional_headers={"Origin": f"http://127.0.0.1:{port}"},
    ) as ws:
        await ws.send(json.dumps({
            "type": "create_session", "persona_id": "support", "user_id": "u1",
        }))
        resp = json.loads(await ws.recv())
        assert resp["type"] == "session_created"


async def test_connection_allowed_when_no_origin(transport: WebSocketTransport):
    """Connections without an Origin header (e.g. CLI tools) are allowed."""
    async with websockets.connect(_url(transport)) as ws:
        await ws.send(json.dumps({
            "type": "create_session", "persona_id": "support", "user_id": "u1",
        }))
        resp = json.loads(await ws.recv())
        assert resp["type"] == "session_created"
