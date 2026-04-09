from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import structlog

from agentic_core.adapters.primary.grpc.server import GrpcTransport
from agentic_core.adapters.primary.http_api import create_app
from agentic_core.adapters.primary.websocket import WebSocketTransport
from aiohttp import web
from agentic_core.application.commands.create_session import (
    CreateSessionCommand,
    CreateSessionHandler,
)
from agentic_core.application.commands.handle_message import (
    HandleMessageCommand,
    HandleMessageHandler,
)
from agentic_core.application.commands.resume_hitl import (
    ResumeHITLCommand,
    ResumeHITLHandler,
)
from agentic_core.application.middleware.base import MiddlewareChain, RequestContext
from agentic_core.application.middleware.tracing import TracingMiddleware
from agentic_core.application.queries.get_session import GetSessionHandler, GetSessionQuery
from agentic_core.application.queries.list_personas import ListPersonasHandler, ListPersonasQuery
from agentic_core.config.settings import AgenticSettings
from agentic_core.domain.entities.persona import Persona
from agentic_core.domain.entities.session import Session
from agentic_core.domain.services.routing import RoutingService
from agentic_core.domain.value_objects.messages import AgentMessage
from agentic_core.shared_kernel.events import EventBus

logger = logging.getLogger(__name__)


class _StubSessionPort:
    """In-memory stub for Phase 1. Replaced by PostgresAdapter in Phase 2."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def create(self, session: Session) -> None:
        self._sessions[session.id] = session

    async def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def update(self, session: Session) -> None:
        self._sessions[session.id] = session

    async def store_checkpoint(self, session_id: str, checkpoint_data: bytes) -> str:
        return f"ckpt_{session_id}"

    async def load_checkpoint(self, checkpoint_id: str) -> bytes:
        return b""


class _StubMemoryPort:
    """In-memory stub for Phase 1. Replaced by RedisAdapter in Phase 2."""

    async def store_message(self, message: object) -> None:
        pass

    async def get_messages(self, session_id: str, limit: int = 50) -> list[AgentMessage]:
        return []

    async def get_context_window(self, session_id: str, max_tokens: int) -> list[AgentMessage]:
        return []


class AgentRuntime:
    """Composition Root. The ONLY place that knows about concrete implementations."""

    def __init__(self, settings: AgenticSettings | None = None) -> None:
        self._settings = settings or AgenticSettings()
        self._is_running = False

        # Configure structured logging
        self._configure_logging()

        # Event bus
        self._event_bus = EventBus()

        # Domain services
        self._routing = RoutingService()

        # Stub ports (Phase 1) — replaced by real adapters in Phase 2
        session_port = _StubSessionPort()
        memory_port = _StubMemoryPort()

        # Command handlers
        self._create_session_handler = CreateSessionHandler(session_port, self._event_bus)  # type: ignore[arg-type]
        self._handle_message_handler = HandleMessageHandler(memory_port, session_port, self._event_bus)  # type: ignore[arg-type]
        self._resume_hitl_handler = ResumeHITLHandler(session_port)  # type: ignore[arg-type]

        # Query handlers
        self._get_session_handler = GetSessionHandler(session_port)  # type: ignore[arg-type]
        self._list_personas_handler = ListPersonasHandler(self._routing)

        # Middleware chain (Phase 1: tracing with no-op fallback only)
        self._middleware = MiddlewareChain(
            [TracingMiddleware(tracing_port=None)],
            handler=self._noop_handler,
        )

        # Primary adapters
        self._ws = WebSocketTransport(
            host=self._settings.ws_host,
            port=self._settings.ws_port,
        )
        self._grpc = GrpcTransport(
            host=self._settings.grpc_host,
            port=self._settings.grpc_port,
        )

        # Wire WebSocket callbacks
        self._ws.on_create_session = self._on_ws_create_session
        self._ws.on_message = self._on_ws_message

        # Wire gRPC callbacks
        self._grpc.servicer.on_create_session = self._on_grpc_create_session
        self._grpc.servicer.on_get_session = self._on_grpc_get_session
        self._grpc.servicer.on_list_personas = self._on_grpc_list_personas

    def _configure_logging(self) -> None:
        log_format = self._settings.observability.log_format
        processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
        ]
        if log_format == "console":
            processors.append(structlog.dev.ConsoleRenderer())
        else:
            processors.append(structlog.processors.JSONRenderer())

        structlog.configure(
            processors=processors,
            logger_factory=structlog.PrintLoggerFactory(),
        )

    @staticmethod
    async def _noop_handler(message: AgentMessage, ctx: RequestContext) -> AgentMessage:
        return message

    # -- WebSocket callbacks --

    async def _on_ws_create_session(self, persona_id: str, user_id: str) -> str:
        cmd = CreateSessionCommand(persona_id=persona_id, user_id=user_id)
        session = await self._create_session_handler.execute(cmd)
        return session.id

    async def _on_ws_message(
        self, session_id: str, persona_id: str, content: str,
    ) -> AsyncIterator[dict[str, Any]]:
        # Phase 2: will stream tokens from LangGraph
        return
        yield  # noqa: unreachable

    # -- gRPC callbacks --

    async def _on_grpc_create_session(self, persona_id: str, user_id: str) -> Session:
        cmd = CreateSessionCommand(persona_id=persona_id, user_id=user_id)
        return await self._create_session_handler.execute(cmd)

    async def _on_grpc_get_session(self, session_id: str) -> Session | None:
        return await self._get_session_handler.execute(GetSessionQuery(session_id))

    async def _on_grpc_list_personas(self) -> list[Persona]:
        return await self._list_personas_handler.execute(ListPersonasQuery())

    # -- Lifecycle --

    async def _start_http(self) -> None:
        """Start aiohttp server for REST API + static file serving."""
        self._http_app = create_app(
            agents_dir=self._settings.personas_dir,
            static_dir=self._settings.static_dir,
            settings=self._settings,
        )
        self._http_runner = web.AppRunner(self._http_app)
        await self._http_runner.setup()
        site = web.TCPSite(
            self._http_runner,
            self._settings.ws_host,
            self._settings.http_port,
        )
        await site.start()
        logger.info("HTTP API started on port %d", self._settings.http_port)

    async def start(self) -> None:
        logger.info(
            "Starting AgentRuntime in %s mode (ws=%s:%d, grpc=%s:%d)",
            self._settings.mode,
            self._settings.ws_host, self._settings.ws_port,
            self._settings.grpc_host, self._settings.grpc_port,
        )
        servers = [self._ws.start(), self._grpc.start()]
        if self._settings.mode == "standalone" and self._settings.api_enabled:
            servers.append(self._start_http())
        await asyncio.gather(*servers)
        self._is_running = True
        logger.info("AgentRuntime started")

    async def stop(self) -> None:
        logger.info("Stopping AgentRuntime")
        await asyncio.gather(self._ws.stop(), self._grpc.stop())
        self._is_running = False
        logger.info("AgentRuntime stopped")

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def routing(self) -> RoutingService:
        return self._routing

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus


async def _main() -> None:
    settings = AgenticSettings()
    runtime = AgentRuntime(settings)
    await runtime.start()
    try:
        await asyncio.Event().wait()  # Run forever
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(_main())
