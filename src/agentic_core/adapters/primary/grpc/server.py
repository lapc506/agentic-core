from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import grpc
from grpc import aio as grpc_aio

from agentic_core.adapters.primary.grpc.generated import (
    agentic_core_pb2,
    agentic_core_pb2_grpc,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class AgentServiceServicer(agentic_core_pb2_grpc.AgentServiceServicer):
    """gRPC service implementation. Callbacks wired by runtime."""

    def __init__(self) -> None:
        self.on_create_session: Any = None
        self.on_send_message: Any = None
        self.on_get_session: Any = None
        self.on_resume_hitl: Any = None
        self.on_list_personas: Any = None

    async def CreateSession(
        self, request: agentic_core_pb2.CreateSessionRequest, context: grpc_aio.ServicerContext,
    ) -> agentic_core_pb2.SessionInfo:
        if self.on_create_session is not None:
            session = await self.on_create_session(request.persona_id, request.user_id)
            return agentic_core_pb2.SessionInfo(
                session_id=session.id,
                persona_id=session.persona_id,
                user_id=session.user_id,
                state=session.state.value,
                created_at=session.created_at.isoformat(),
            )
        await context.abort(grpc.StatusCode.UNIMPLEMENTED, "Not configured")
        return agentic_core_pb2.SessionInfo()  # unreachable but satisfies type checker

    async def GetSession(
        self, request: agentic_core_pb2.GetSessionRequest, context: grpc_aio.ServicerContext,
    ) -> agentic_core_pb2.SessionInfo:
        if self.on_get_session is not None:
            session = await self.on_get_session(request.session_id)
            if session is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Session not found")
                return agentic_core_pb2.SessionInfo()
            return agentic_core_pb2.SessionInfo(
                session_id=session.id,
                persona_id=session.persona_id,
                user_id=session.user_id,
                state=session.state.value,
                created_at=session.created_at.isoformat(),
            )
        await context.abort(grpc.StatusCode.UNIMPLEMENTED, "Not configured")
        return agentic_core_pb2.SessionInfo()

    async def SendMessage(
        self, request: agentic_core_pb2.AgentRequest, context: grpc_aio.ServicerContext,
    ) -> AsyncIterator[agentic_core_pb2.AgentResponse]:
        if self.on_send_message is not None:
            async for chunk in self.on_send_message(
                request.session_id, request.persona_id, request.content,
            ):
                yield chunk
        else:
            yield agentic_core_pb2.AgentResponse(
                error=agentic_core_pb2.ErrorDetail(
                    session_id=request.session_id,
                    code="internal_error",
                    message="Not configured",
                )
            )

    async def ResumeHITL(
        self, request: agentic_core_pb2.HumanResponse, context: grpc_aio.ServicerContext,
    ) -> AsyncIterator[agentic_core_pb2.AgentResponse]:
        if self.on_resume_hitl is not None:
            async for chunk in self.on_resume_hitl(request.session_id, request.content):
                yield chunk
        else:
            yield agentic_core_pb2.AgentResponse(
                error=agentic_core_pb2.ErrorDetail(
                    session_id=request.session_id,
                    code="internal_error",
                    message="Not configured",
                )
            )

    async def ListPersonas(
        self, request: agentic_core_pb2.Empty, context: grpc_aio.ServicerContext,
    ) -> agentic_core_pb2.PersonaList:
        if self.on_list_personas is not None:
            personas = await self.on_list_personas()
            return agentic_core_pb2.PersonaList(
                personas=[
                    agentic_core_pb2.PersonaInfo(
                        name=p.name,
                        role=p.role,
                        description=p.description,
                        graph_template=p.graph_template.value,
                    )
                    for p in personas
                ]
            )
        return agentic_core_pb2.PersonaList()

    async def HealthCheck(
        self, request: agentic_core_pb2.Empty, context: grpc_aio.ServicerContext,
    ) -> agentic_core_pb2.HealthStatus:
        return agentic_core_pb2.HealthStatus(healthy=True, version="0.1.0", active_sessions=0)


class GrpcTransport:
    def __init__(self, host: str = "0.0.0.0", port: int = 50051) -> None:
        self._host = host
        self._port = port
        self._server: grpc_aio.Server | None = None
        self.servicer = AgentServiceServicer()

    async def start(self) -> None:
        self._server = grpc_aio.server()
        agentic_core_pb2_grpc.add_AgentServiceServicer_to_server(  # type: ignore[no-untyped-call]
            self.servicer, self._server
        )
        bind_address = f"{self._host}:{self._port}"
        self._server.add_insecure_port(bind_address)
        await self._server.start()
        logger.info("gRPC server started on %s", bind_address)

    async def stop(self) -> None:
        if self._server is not None:
            await self._server.stop(grace=5)
            logger.info("gRPC server stopped")

    @property
    def is_running(self) -> bool:
        return self._server is not None
