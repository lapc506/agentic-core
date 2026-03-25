from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable, Awaitable
from dataclasses import dataclass, field
from typing import Any

import websockets
from websockets.asyncio.server import Server, ServerConnection

from agentic_core.domain.value_objects.messages import AgentMessage

logger = logging.getLogger(__name__)

# Protocol message types
TYPE_CREATE_SESSION = "create_session"
TYPE_SESSION_CREATED = "session_created"
TYPE_CLOSE_SESSION = "close_session"
TYPE_SESSION_CLOSED = "session_closed"
TYPE_MESSAGE = "message"
TYPE_STREAM_START = "stream_start"
TYPE_STREAM_TOKEN = "stream_token"
TYPE_STREAM_END = "stream_end"
TYPE_HUMAN_ESCALATION = "human_escalation"
TYPE_HUMAN_RESPONSE = "human_response"
TYPE_AUDIO = "audio"
TYPE_ERROR = "error"

# Error codes
ERR_INVALID_SESSION = "invalid_session"
ERR_INVALID_PERSONA = "invalid_persona"
ERR_RATE_LIMITED = "rate_limited"
ERR_AUTH_FAILED = "auth_failed"
ERR_INTERNAL = "internal_error"
ERR_SESSION_LIMIT = "session_limit_exceeded"
ERR_INVALID_PAYLOAD = "invalid_payload"


@dataclass
class ConnectionState:
    sessions: set[str] = field(default_factory=set)
    max_sessions: int = 10


# Callback types
OnCreateSession = Callable[[str, str], Awaitable[str]]  # (persona_id, user_id) -> session_id
OnMessage = Callable[[str, str, str], AsyncIterator[dict[str, Any]]]  # (session_id, persona_id, content) -> stream
OnHumanResponse = Callable[[str, str], Awaitable[None]]  # (session_id, content)
OnCloseSession = Callable[[str], Awaitable[None]]  # (session_id)


class WebSocketTransport:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        max_sessions_per_connection: int = 10,
        heartbeat_interval: float = 30.0,
    ) -> None:
        self._host = host
        self._port = port
        self._max_sessions = max_sessions_per_connection
        self._heartbeat_interval = heartbeat_interval
        self._server: Server | None = None

        # Callbacks (wired by runtime)
        self.on_create_session: OnCreateSession | None = None
        self.on_message: OnMessage | None = None
        self.on_human_response: OnHumanResponse | None = None
        self.on_close_session: OnCloseSession | None = None

    async def start(self) -> None:
        self._server = await websockets.serve(
            self._handle_connection,
            self._host,
            self._port,
            ping_interval=self._heartbeat_interval,
            ping_timeout=self._heartbeat_interval,
        )
        logger.info("WebSocket server started on %s:%d", self._host, self._port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            logger.info("WebSocket server stopped")

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._server.is_serving()

    async def _handle_connection(self, ws: ServerConnection) -> None:
        state = ConnectionState(max_sessions=self._max_sessions)
        try:
            async for raw in ws:
                if isinstance(raw, bytes):
                    continue  # Skip binary frames for now
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await self._send_error(ws, None, ERR_INVALID_PAYLOAD, "Invalid JSON")
                    continue

                msg_type = data.get("type")
                try:
                    await self._dispatch(ws, state, msg_type, data)
                except Exception:
                    logger.exception("Error handling message type=%s", msg_type)
                    await self._send_error(
                        ws, data.get("session_id"), ERR_INTERNAL, "Internal server error"
                    )
        except websockets.ConnectionClosed:
            pass
        finally:
            # Connection dropped: pause all sessions
            for sid in state.sessions:
                logger.info("Connection dropped, pausing session %s", sid)

    async def _dispatch(
        self, ws: ServerConnection, state: ConnectionState,
        msg_type: str | None, data: dict[str, Any],
    ) -> None:
        if msg_type == TYPE_CREATE_SESSION:
            await self._handle_create_session(ws, state, data)
        elif msg_type == TYPE_CLOSE_SESSION:
            await self._handle_close_session(ws, state, data)
        elif msg_type == TYPE_MESSAGE:
            await self._handle_message(ws, state, data)
        elif msg_type == TYPE_HUMAN_RESPONSE:
            await self._handle_human_response(ws, data)
        else:
            await self._send_error(ws, None, ERR_INVALID_PAYLOAD, f"Unknown type: {msg_type}")

    async def _handle_create_session(
        self, ws: ServerConnection, state: ConnectionState, data: dict[str, Any],
    ) -> None:
        if len(state.sessions) >= state.max_sessions:
            await self._send_error(ws, None, ERR_SESSION_LIMIT, "Max sessions exceeded")
            return

        persona_id = data.get("persona_id", "")
        user_id = data.get("user_id", "")
        if not persona_id:
            await self._send_error(ws, None, ERR_INVALID_PERSONA, "persona_id required")
            return

        if self.on_create_session is not None:
            session_id = await self.on_create_session(persona_id, user_id)
        else:
            import uuid_utils
            session_id = str(uuid_utils.uuid7())

        state.sessions.add(session_id)
        await ws.send(json.dumps({
            "type": TYPE_SESSION_CREATED,
            "session_id": session_id,
        }))

    async def _handle_close_session(
        self, ws: ServerConnection, state: ConnectionState, data: dict[str, Any],
    ) -> None:
        session_id = data.get("session_id", "")
        if session_id in state.sessions:
            state.sessions.discard(session_id)
            if self.on_close_session is not None:
                await self.on_close_session(session_id)
        await ws.send(json.dumps({
            "type": TYPE_SESSION_CLOSED,
            "session_id": session_id,
        }))

    async def _handle_message(
        self, ws: ServerConnection, state: ConnectionState, data: dict[str, Any],
    ) -> None:
        session_id = data.get("session_id", "")
        persona_id = data.get("persona_id", "")
        content = data.get("content", "")

        if session_id not in state.sessions:
            await self._send_error(ws, session_id, ERR_INVALID_SESSION, "Session not found")
            return

        if self.on_message is not None:
            await ws.send(json.dumps({"type": TYPE_STREAM_START, "session_id": session_id}))
            async for chunk in self.on_message(session_id, persona_id, content):
                await ws.send(json.dumps(chunk))
            await ws.send(json.dumps({"type": TYPE_STREAM_END, "session_id": session_id}))

    async def _handle_human_response(
        self, ws: ServerConnection, data: dict[str, Any],
    ) -> None:
        session_id = data.get("session_id", "")
        content = data.get("content", "")
        if self.on_human_response is not None:
            await self.on_human_response(session_id, content)

    @staticmethod
    async def _send_error(
        ws: ServerConnection, session_id: str | None, code: str, message: str,
    ) -> None:
        await ws.send(json.dumps({
            "type": TYPE_ERROR,
            "session_id": session_id or "",
            "code": code,
            "message": message,
        }))
