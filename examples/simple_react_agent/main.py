"""Simple ReAct agent example with 2 calculator tools."""
from __future__ import annotations

import asyncio

from agentic_core.config.settings import AgenticSettings
from agentic_core.runtime import AgentRuntime


async def main() -> None:
    settings = AgenticSettings(
        mode="standalone",
        ws_port=8765,
        grpc_port=50051,
    )
    runtime = AgentRuntime(settings)

    # Register persona from YAML
    # In production: runtime.routing.register(persona_from_yaml)

    print("Starting simple ReAct agent...")
    print("  WebSocket: ws://localhost:8765")
    print("  gRPC:      localhost:50051")
    await runtime.start()

    try:
        await asyncio.Event().wait()  # Run forever
    except KeyboardInterrupt:
        pass
    finally:
        await runtime.stop()
        print("Agent stopped.")


if __name__ == "__main__":
    asyncio.run(main())
