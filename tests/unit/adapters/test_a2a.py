"""Unit tests for the A2A Protocol adapter."""

from __future__ import annotations

import pytest

from agentic_core.adapters.primary.a2a import (
    A2AServer,
    A2ATask,
    AgentCard,
    TaskState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_server(
    name: str = "Test Agent",
    description: str = "A test agent",
    url: str = "http://localhost:8080",
    capabilities: list[str] | None = None,
    skills: list[dict] | None = None,
) -> A2AServer:
    card = AgentCard(
        name=name,
        description=description,
        url=url,
        capabilities=capabilities or ["chat"],
        skills=skills or [],
    )
    return A2AServer(card)


def jsonrpc(method: str, params: dict, req_id: int = 1) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}


# ---------------------------------------------------------------------------
# 1. Agent card generation
# ---------------------------------------------------------------------------


def test_agent_card_fields():
    card = AgentCard(
        name="Orchestrator",
        description="Routes tasks to sub-agents",
        url="https://example.com",
        version="2.0",
        capabilities=["chat", "task_delegation"],
        skills=[{"id": "summarize", "name": "Summarize", "description": "Summarizes text"}],
    )
    data = card.to_dict()

    assert data["name"] == "Orchestrator"
    assert data["description"] == "Routes tasks to sub-agents"
    assert data["url"] == "https://example.com"
    assert data["version"] == "2.0"
    assert data["capabilities"] == ["chat", "task_delegation"]
    assert data["protocol"] == "a2a"
    assert data["protocolVersion"] == "0.1"
    assert len(data["skills"]) == 1
    assert data["skills"][0]["id"] == "summarize"
    assert data["skills"][0]["name"] == "Summarize"
    assert data["skills"][0]["description"] == "Summarizes text"


def test_agent_card_skill_description_defaults_to_empty_string():
    card = AgentCard(
        name="Agent",
        description="desc",
        url="http://x",
        skills=[{"id": "x", "name": "X"}],  # no description key
    )
    data = card.to_dict()
    assert data["skills"][0]["description"] == ""


def test_get_agent_card_via_server():
    server = make_server(name="MyBot", capabilities=["streaming"])
    card = server.get_agent_card()
    assert card["name"] == "MyBot"
    assert "streaming" in card["capabilities"]


# ---------------------------------------------------------------------------
# 2. Task creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_task_returns_task_id_and_state():
    server = make_server()
    resp = await server.handle_jsonrpc(jsonrpc("a2a.createTask", {}))

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    result = resp["result"]
    assert "taskId" in result
    assert result["state"] == TaskState.SUBMITTED.value


@pytest.mark.asyncio
async def test_create_task_with_initial_message():
    server = make_server()
    msg = {"role": "user", "content": "Hello agent"}
    resp = await server.handle_jsonrpc(jsonrpc("a2a.createTask", {"message": msg}))

    task_id = resp["result"]["taskId"]
    get_resp = await server.handle_jsonrpc(jsonrpc("a2a.getTask", {"taskId": task_id}))
    assert get_resp["result"]["messages"] == [msg]


@pytest.mark.asyncio
async def test_create_task_with_handler_completes():
    server = make_server()

    async def handler(task: A2ATask) -> dict:
        return {"answer": 42}

    server.set_task_handler(handler)
    resp = await server.handle_jsonrpc(jsonrpc("a2a.createTask", {}))
    result = resp["result"]
    assert result["state"] == TaskState.COMPLETED.value

    get_resp = await server.handle_jsonrpc(
        jsonrpc("a2a.getTask", {"taskId": result["taskId"]})
    )
    assert get_resp["result"]["result"] == {"answer": 42}


@pytest.mark.asyncio
async def test_create_task_handler_exception_marks_failed():
    server = make_server()

    async def failing_handler(task: A2ATask) -> dict:
        raise RuntimeError("boom")

    server.set_task_handler(failing_handler)
    resp = await server.handle_jsonrpc(jsonrpc("a2a.createTask", {}))
    result = resp["result"]
    assert result["state"] == TaskState.FAILED.value

    get_resp = await server.handle_jsonrpc(
        jsonrpc("a2a.getTask", {"taskId": result["taskId"]})
    )
    assert "error" in get_resp["result"]["result"]
    assert "boom" in get_resp["result"]["result"]["error"]


# ---------------------------------------------------------------------------
# 3. Task lifecycle (get, cancel)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_task_not_found_returns_error():
    server = make_server()
    resp = await server.handle_jsonrpc(jsonrpc("a2a.getTask", {"taskId": "missing"}))
    assert "error" in resp
    assert resp["error"]["code"] == -32000
    assert "Task not found" in resp["error"]["message"]


@pytest.mark.asyncio
async def test_cancel_task_changes_state():
    server = make_server()
    create_resp = await server.handle_jsonrpc(jsonrpc("a2a.createTask", {}))
    task_id = create_resp["result"]["taskId"]

    cancel_resp = await server.handle_jsonrpc(
        jsonrpc("a2a.cancelTask", {"taskId": task_id})
    )
    assert cancel_resp["result"]["state"] == TaskState.CANCELED.value


@pytest.mark.asyncio
async def test_cancel_nonexistent_task_returns_error():
    server = make_server()
    resp = await server.handle_jsonrpc(
        jsonrpc("a2a.cancelTask", {"taskId": "ghost"})
    )
    assert "error" in resp
    assert resp["error"]["code"] == -32000


@pytest.mark.asyncio
async def test_get_task_has_timestamps():
    server = make_server()
    create_resp = await server.handle_jsonrpc(jsonrpc("a2a.createTask", {}))
    task_id = create_resp["result"]["taskId"]

    get_resp = await server.handle_jsonrpc(jsonrpc("a2a.getTask", {"taskId": task_id}))
    data = get_resp["result"]
    assert "createdAt" in data
    assert "updatedAt" in data
    # ISO 8601 sanity check
    assert "T" in data["createdAt"]


# ---------------------------------------------------------------------------
# 4. Message sending
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_increments_count():
    server = make_server()
    create_resp = await server.handle_jsonrpc(jsonrpc("a2a.createTask", {}))
    task_id = create_resp["result"]["taskId"]

    msg1 = {"role": "user", "content": "First"}
    msg2 = {"role": "assistant", "content": "Second"}

    send1 = await server.handle_jsonrpc(
        jsonrpc("a2a.sendMessage", {"taskId": task_id, "message": msg1})
    )
    assert send1["result"]["messageCount"] == 1

    send2 = await server.handle_jsonrpc(
        jsonrpc("a2a.sendMessage", {"taskId": task_id, "message": msg2})
    )
    assert send2["result"]["messageCount"] == 2


@pytest.mark.asyncio
async def test_send_message_to_nonexistent_task():
    server = make_server()
    resp = await server.handle_jsonrpc(
        jsonrpc("a2a.sendMessage", {"taskId": "nope", "message": {"role": "user", "content": "hi"}})
    )
    assert "error" in resp
    assert resp["error"]["code"] == -32000


@pytest.mark.asyncio
async def test_send_message_persists_in_get_task():
    server = make_server()
    create_resp = await server.handle_jsonrpc(jsonrpc("a2a.createTask", {}))
    task_id = create_resp["result"]["taskId"]

    msg = {"role": "user", "content": "Remember this"}
    await server.handle_jsonrpc(
        jsonrpc("a2a.sendMessage", {"taskId": task_id, "message": msg})
    )

    get_resp = await server.handle_jsonrpc(jsonrpc("a2a.getTask", {"taskId": task_id}))
    assert msg in get_resp["result"]["messages"]


# ---------------------------------------------------------------------------
# 5. Error handling — JSON-RPC method not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_method_returns_method_not_found():
    server = make_server()
    resp = await server.handle_jsonrpc(jsonrpc("a2a.nonExistentMethod", {}))
    assert "error" in resp
    assert resp["error"]["code"] == -32601
    assert "Method not found" in resp["error"]["message"]


@pytest.mark.asyncio
async def test_response_preserves_request_id():
    server = make_server()
    resp = await server.handle_jsonrpc(jsonrpc("a2a.getAgentCard", {}, req_id=99))
    assert resp["id"] == 99


@pytest.mark.asyncio
async def test_get_agent_card_via_jsonrpc():
    server = make_server(name="CardBot")
    resp = await server.handle_jsonrpc(jsonrpc("a2a.getAgentCard", {}))
    assert "error" not in resp
    assert resp["result"]["name"] == "CardBot"
    assert resp["result"]["protocol"] == "a2a"


# ---------------------------------------------------------------------------
# 6. HTTP routes (integration via aiohttp test client)
# ---------------------------------------------------------------------------


@pytest.fixture
async def a2a_client(tmp_path, aiohttp_client):
    from agentic_core.adapters.primary.http_api import create_app

    app = create_app(agents_dir=str(tmp_path), static_dir=None)
    return await aiohttp_client(app)


async def test_well_known_agent_json(a2a_client):
    resp = await a2a_client.get("/.well-known/agent.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["name"] == "Agent Studio"
    assert data["protocol"] == "a2a"


async def test_a2a_jsonrpc_post(a2a_client):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "a2a.getAgentCard", "params": {}}
    resp = await a2a_client.post("/a2a", json=payload)
    assert resp.status == 200
    data = await resp.json()
    assert data["result"]["name"] == "Agent Studio"


async def test_a2a_create_and_get_task_via_http(a2a_client):
    create_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "a2a.createTask",
        "params": {"message": {"role": "user", "content": "Do something"}},
    }
    resp = await a2a_client.post("/a2a", json=create_payload)
    assert resp.status == 200
    create_data = await resp.json()
    task_id = create_data["result"]["taskId"]

    get_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "a2a.getTask",
        "params": {"taskId": task_id},
    }
    resp = await a2a_client.post("/a2a", json=get_payload)
    assert resp.status == 200
    get_data = await resp.json()
    assert get_data["result"]["taskId"] == task_id
    assert len(get_data["result"]["messages"]) == 1
