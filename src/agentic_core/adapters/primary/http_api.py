"""HTTP API adapter (aiohttp) for standalone mode.

Provides REST routes for agent CRUD, gates, metrics, health, config,
and optional static-file serving with SPA fallback for Flutter Web.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aiohttp import web

from agentic_core.application.commands.create_agent import (
    CreateAgentCommand,
    CreateAgentHandler,
)
from agentic_core.application.commands.update_agent import (
    UpdateAgentCommand,
    UpdateAgentHandler,
)
from agentic_core.application.commands.update_gates import (
    UpdateGatesCommand,
    UpdateGatesHandler,
)
from agentic_core.application.queries.get_metrics import (
    GetMetricsHandler,
    GetMetricsQuery,
)
from agentic_core.application.queries.list_agents import (
    ListAgentsHandler,
    ListAgentsQuery,
)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def config(request: web.Request) -> web.Response:
    settings: dict[str, Any] | None = request.app.get("settings")
    if settings is None:
        return web.json_response({})
    safe_keys = {"mode", "ws_port", "personas_dir", "pii_redaction_enabled"}
    subset = {k: v for k, v in settings.items() if k in safe_keys}
    return web.json_response(subset)


async def list_agents(request: web.Request) -> web.Response:
    handler: ListAgentsHandler = request.app["list_agents_handler"]
    agents = await handler.execute(ListAgentsQuery())
    return web.json_response(agents)


async def create_agent(request: web.Request) -> web.Response:
    body = await request.json()
    handler: CreateAgentHandler = request.app["create_agent_handler"]
    cmd = CreateAgentCommand(
        name=body["name"],
        role=body.get("role", "assistant"),
        description=body.get("description", ""),
        graph_template=body.get("graph_template", "react"),
        tools=body.get("tools"),
        system_prompt=body.get("system_prompt", ""),
    )
    await handler.execute(cmd)
    return web.json_response({"name": cmd.name}, status=201)


async def get_agent_detail(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    handler: ListAgentsHandler = request.app["list_agents_handler"]
    agents = await handler.execute(ListAgentsQuery())
    for agent in agents:
        if agent.get("slug") == slug:
            return web.json_response(agent)
    return web.json_response({"error": "not found"}, status=404)


async def update_agent(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    body = await request.json()
    handler: UpdateAgentHandler = request.app["update_agent_handler"]
    try:
        updated = await handler.execute(UpdateAgentCommand(agent_slug=slug, updates=body))
    except FileNotFoundError:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response(updated)


async def delete_agent(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    agents_dir: str = request.app["agents_dir"]
    yaml_path = Path(agents_dir) / f"{slug}.yaml"
    if not yaml_path.exists():
        return web.json_response({"error": "not found"}, status=404)
    os.remove(yaml_path)
    return web.json_response({"deleted": slug})


async def get_gates(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    handler: ListAgentsHandler = request.app["list_agents_handler"]
    agents = await handler.execute(ListAgentsQuery())
    for agent in agents:
        if agent.get("slug") == slug:
            return web.json_response(agent.get("gates", []))
    return web.json_response({"error": "not found"}, status=404)


async def update_gates(request: web.Request) -> web.Response:
    slug = request.match_info["slug"]
    body = await request.json()
    handler: UpdateGatesHandler = request.app["update_gates_handler"]
    try:
        gates = await handler.execute(
            UpdateGatesCommand(agent_slug=slug, gates=body["gates"])
        )
    except FileNotFoundError:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response([g.model_dump(mode="json") for g in gates])


async def get_metrics(request: web.Request) -> web.Response:
    metric_type = request.match_info["metric_type"]
    window = request.query.get("window", "1h")
    handler: GetMetricsHandler = request.app["get_metrics_handler"]
    result = await handler.execute(GetMetricsQuery(metric_type=metric_type, window=window))
    return web.json_response(result)


async def spa_fallback(request: web.Request) -> web.Response:
    """Serve index.html for any non-API path (Flutter Web SPA routing)."""
    static_dir: str | None = request.app.get("static_dir")
    if static_dir is None:
        return web.json_response({"error": "not found"}, status=404)
    index = Path(static_dir) / "index.html"
    if not index.exists():
        return web.json_response({"error": "not found"}, status=404)
    return web.FileResponse(index)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(
    agents_dir: str,
    static_dir: str | None = None,
    settings: dict[str, Any] | None = None,
) -> web.Application:
    """Build and return an aiohttp ``Application`` wired to CQRS handlers."""

    app = web.Application()

    # Store references on app dict
    app["agents_dir"] = agents_dir
    app["static_dir"] = static_dir
    app["settings"] = settings
    app["list_agents_handler"] = ListAgentsHandler(agents_dir)
    app["create_agent_handler"] = CreateAgentHandler(agents_dir)
    app["update_agent_handler"] = UpdateAgentHandler(agents_dir)
    app["update_gates_handler"] = UpdateGatesHandler(agents_dir)
    app["get_metrics_handler"] = GetMetricsHandler()

    # --- API routes ---
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/config", config)
    app.router.add_get("/api/agents", list_agents)
    app.router.add_post("/api/agents", create_agent)
    app.router.add_get("/api/agents/{slug}", get_agent_detail)
    app.router.add_put("/api/agents/{slug}", update_agent)
    app.router.add_delete("/api/agents/{slug}", delete_agent)
    app.router.add_get("/api/agents/{slug}/gates", get_gates)
    app.router.add_put("/api/agents/{slug}/gates", update_gates)
    app.router.add_get("/api/metrics/{metric_type}", get_metrics)

    # --- Static files + SPA fallback ---
    if static_dir and Path(static_dir).is_dir():
        app.router.add_static("/static", static_dir)
        app.router.add_get("/{path:.*}", spa_fallback)

    return app
