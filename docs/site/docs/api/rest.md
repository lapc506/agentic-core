# REST API Reference

The standalone mode exposes a REST API at `http://localhost:8765/api/`. This API is used by the Flutter UI and is available for programmatic access during development. In production sidecar deployments, backends communicate via gRPC instead.

---

## Base URL

```
http://localhost:8765/api
```

All requests and responses use `application/json`.

---

## Endpoints

### Health

#### `GET /api/health`

Returns the runtime health status and dependency connectivity.

```bash
curl http://localhost:8765/api/health
```

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "dependencies": {
    "redis": "ok",
    "postgres": "ok",
    "falkordb": "ok"
  }
}
```

---

### Agents

#### `GET /api/agents`

Returns all configured agents (personas).

```bash
curl http://localhost:8765/api/agents
```

**Response:**
```json
[
  {
    "slug": "support-agent",
    "name": "Support Agent",
    "role": "Customer support specialist",
    "graph_template": "react",
    "model_config": {
      "provider": "openrouter",
      "model": "anthropic/claude-sonnet-4-6"
    }
  }
]
```

---

#### `POST /api/agents`

Create a new agent.

```bash
curl -X POST http://localhost:8765/api/agents \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "My Agent",
    "role": "assistant",
    "description": "A helpful assistant"
  }'
```

**Body fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Human-readable agent name |
| `role` | string | yes | One-line role description |
| `description` | string | no | Longer system prompt context |
| `graph_template` | string | no | `react` (default), `plan-and-execute`, `reflexion`, `llm-compiler`, `supervisor`, `orchestrator` |
| `model_config` | object | no | Provider and model override |
| `tools` | array | no | MCP tool patterns (e.g., `mcp_zendesk_*`) |

**Response:** `201 Created` with the agent object including generated `slug`.

---

#### `GET /api/agents/:slug`

Fetch a single agent by slug.

```bash
curl http://localhost:8765/api/agents/support-agent
```

---

#### `PUT /api/agents/:slug`

Update an existing agent.

```bash
curl -X PUT http://localhost:8765/api/agents/support-agent \
  -H 'Content-Type: application/json' \
  -d '{"role": "Senior support specialist"}'
```

---

#### `DELETE /api/agents/:slug`

Delete an agent.

```bash
curl -X DELETE http://localhost:8765/api/agents/support-agent
```

**Response:** `204 No Content`

---

### Gates

Gates are middleware rules applied to each message (input filters, guardrails, output redaction).

#### `GET /api/agents/:slug/gates`

```bash
curl http://localhost:8765/api/agents/support-agent/gates
```

**Response:**
```json
{
  "gates": [
    {
      "name": "PII Filter",
      "content": "Redact all PII from the response",
      "action": "redact",
      "order": 0
    }
  ]
}
```

---

#### `PUT /api/agents/:slug/gates`

Replace all gates for an agent.

```bash
curl -X PUT http://localhost:8765/api/agents/support-agent/gates \
  -H 'Content-Type: application/json' \
  -d '{
    "gates": [
      {
        "name": "PII Filter",
        "content": "Redact PII",
        "action": "redact",
        "order": 0
      },
      {
        "name": "Topic Guard",
        "content": "Block requests about competitor pricing",
        "action": "block",
        "order": 1
      }
    ]
  }'
```

**Gate actions:** `block` (return error), `redact` (strip matching content), `transform` (rewrite).

---

### Metrics

#### `GET /api/metrics/:type`

Fetch runtime metrics.

| Type | Description |
|------|-------------|
| `tokens` | Token usage by agent and model |
| `latency` | p50/p95/p99 response latencies |
| `errors` | Error counts by category |
| `cost` | Estimated LLM cost (requires Langfuse) |

```bash
curl http://localhost:8765/api/metrics/tokens
```

---

### Config

#### `GET /api/config`

Returns the current runtime configuration (redacted secrets).

```bash
curl http://localhost:8765/api/config
```

**Response:**
```json
{
  "mode": "standalone",
  "default_model": "anthropic/claude-sonnet-4-6",
  "providers": ["openrouter", "ollama"],
  "mcp_servers": []
}
```

---

## Error Responses

All errors follow this shape:

```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "No agent with slug 'unknown-agent'",
    "request_id": "req_abc123"
  }
}
```

| HTTP Status | Code | Meaning |
|-------------|------|---------|
| 400 | `VALIDATION_ERROR` | Request body failed schema validation |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Agent slug already taken |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
