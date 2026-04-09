from __future__ import annotations

from agentic_core.config.settings import AgenticSettings
from agentic_core.domain.entities.persona import Persona
from agentic_core.runtime import AgentRuntime


async def test_runtime_lifecycle():
    settings = AgenticSettings(ws_port=0, grpc_port=0)
    runtime = AgentRuntime(settings)
    assert not runtime.is_running

    await runtime.start()
    assert runtime.is_running

    await runtime.stop()
    assert not runtime.is_running


async def test_runtime_sidecar_mode():
    settings = AgenticSettings(mode="sidecar", ws_port=0, grpc_port=0)
    runtime = AgentRuntime(settings)
    assert settings.ws_host == "127.0.0.1"
    assert settings.grpc_host == "127.0.0.1"
    await runtime.start()
    await runtime.stop()


async def test_runtime_has_routing_and_event_bus():
    settings = AgenticSettings(ws_port=0, grpc_port=0)
    runtime = AgentRuntime(settings)
    assert runtime.routing is not None
    assert runtime.event_bus is not None

    runtime.routing.register(Persona(name="test", role="r", description="d"))
    assert len(runtime.routing.list_personas()) == 1
