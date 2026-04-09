# A2A Protocol

Agent Studio implements the [Google A2A specification](https://google.github.io/A2A/) — a JSON-RPC 2.0 protocol for agent-to-agent communication over HTTP. It enables agent discovery, task delegation, and streamed result passing between independent agents.

---

## Base URL

```
http://localhost:8765/a2a
```

---

## Agent Card

Each agent exposes a self-describing card for discovery.

### `GET /.well-known/agent.json`

Returns the AgentCard for this runtime.

```bash
curl http://localhost:8765/.well-known/agent.json
```

**Response:**

```json
{
  "name": "Agent Studio",
  "description": "Production-ready AI agent runtime",
  "url": "http://localhost:8765/a2a",
  "version": "1.0",
  "protocol": "a2a",
  "protocolVersion": "0.1",
  "capabilities": ["streaming", "hitl", "rag"],
  "skills": [
    {
      "id": "handle_message",
      "name": "Handle Message",
      "description": "Process a user message and return an agent response"
    }
  ]
}
```

---

## JSON-RPC Endpoint

All A2A calls are sent as `POST` to `/a2a` with a `Content-Type: application/json` body conforming to JSON-RPC 2.0.

```
POST http://localhost:8765/a2a
Content-Type: application/json
```

---

## Methods

### `a2a.getAgentCard`

Returns the same payload as `GET /.well-known/agent.json`.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "a2a.getAgentCard",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": { ... }
}
```

---

### `a2a.createTask`

Submit a new task to the agent. The agent begins processing immediately.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "a2a.createTask",
  "params": {
    "message": {
      "role": "user",
      "content": "Summarise the last three support tickets"
    },
    "metadata": {
      "agentSlug": "support-agent",
      "sessionId": "sess_abc123"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "taskId": "task_9f3a...",
    "state": "working"
  }
}
```

---

### `a2a.getTask`

Poll a task for its current state and result.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "a2a.getTask",
  "params": {
    "taskId": "task_9f3a..."
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "result": {
    "taskId": "task_9f3a...",
    "state": "completed",
    "messages": [
      { "role": "user", "content": "Summarise the last three support tickets" }
    ],
    "result": {
      "content": "Tickets #101, #102, #103 concern login failures..."
    },
    "createdAt": "2026-04-08T10:00:00Z",
    "updatedAt": "2026-04-08T10:00:04Z"
  }
}
```

---

### `a2a.sendMessage`

Append a follow-up message to an existing task (multi-turn within one task context).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "4",
  "method": "a2a.sendMessage",
  "params": {
    "taskId": "task_9f3a...",
    "message": {
      "role": "user",
      "content": "Which of those tickets is still open?"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "4",
  "result": {
    "taskId": "task_9f3a...",
    "messageCount": 2
  }
}
```

---

### `a2a.cancelTask`

Cancel a task that is in `submitted` or `working` state.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "5",
  "method": "a2a.cancelTask",
  "params": {
    "taskId": "task_9f3a..."
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "5",
  "result": {
    "taskId": "task_9f3a...",
    "state": "canceled"
  }
}
```

---

## Task Lifecycle

```
submitted → working → completed
                    → failed
         → canceled
```

| State | Meaning |
|-------|---------|
| `submitted` | Task received, queued for processing |
| `working` | Agent is actively processing the task |
| `completed` | Task finished successfully; result is available |
| `failed` | Task encountered an unrecoverable error |
| `canceled` | Caller canceled the task before completion |

---

## Error Responses

JSON-RPC errors are returned in the `error` field:

```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "error": {
    "code": -32000,
    "message": "Task not found: task_9f3a..."
  }
}
```

| Code | Meaning |
|------|---------|
| `-32700` | Parse error — malformed JSON |
| `-32600` | Invalid request — missing required fields |
| `-32601` | Method not found |
| `-32000` | Application error (task not found, handler failure, etc.) |

---

## GenUI Integration

The Flutter frontend uses the A2A protocol via `A2uiTransportAdapter`, which bridges WebSocket events to A2A task lifecycle events:

| WebSocket event | A2A equivalent |
|-----------------|----------------|
| Message sent | `a2a.createTask` |
| Token stream | `task.working` updates |
| Final response | `task.completed` |
| HITL gate triggered | `hitl.confirm_required` |
| Error | `task.failed` |

See [WebSocket Protocol](websocket.md) for the underlying WebSocket message format.
