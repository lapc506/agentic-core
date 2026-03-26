"""Multi-persona supervisor example: orchestrator routes to support + billing."""
from __future__ import annotations

import asyncio

from agentic_core.config.settings import AgenticSettings
from agentic_core.application.services.persona_registry import PersonaRegistry
from agentic_core.domain.services.routing import RoutingService
from agentic_core.runtime import AgentRuntime


async def main() -> None:
    settings = AgenticSettings(
        mode="standalone",
        ws_port=8766,
        grpc_port=50052,
        personas_dir="examples/multi_persona_supervisor/personas",
    )

    routing = RoutingService()
    registry = PersonaRegistry(routing)
    count = registry.discover(settings.personas_dir)
    print(f"Discovered {count} personas:")
    for p in routing.list_personas():
        print(f"  - {p.name} ({p.graph_template.value})")

    runtime = AgentRuntime(settings)
    print("\nStarting supervisor agent...")
    print("  WebSocket: ws://localhost:8766")
    await runtime.start()

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
