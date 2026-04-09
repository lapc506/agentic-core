# Ollama-Compatible API

Agent Studio exposes an Ollama-compatible API endpoint, allowing tools that speak the Ollama protocol (Open WebUI, Continue.dev, LM Studio, etc.) to route requests through Agent Studio's persona and middleware pipeline instead of directly to a model.

---

## Base URL

```
http://localhost:8765/ollama
```

This mirrors the standard Ollama API at `http://localhost:11434`. Swap the base URL in your client config and traffic flows through Agent Studio.

---

## Supported Endpoints

### `POST /ollama/api/chat`

Chat completions with full streaming support.

```bash
curl -X POST http://localhost:8765/ollama/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "support-agent",
    "messages": [
      {"role": "user", "content": "I need help with my order"}
    ],
    "stream": true
  }'
```

The `model` field maps to an Agent Studio persona slug. If no matching persona exists, the request is forwarded to the underlying Ollama instance at `AGENTIC_OLLAMA_URL`.

**Streaming response** (NDJSON):

```json
{"model":"support-agent","created_at":"2026-04-08T12:00:00Z","message":{"role":"assistant","content":"I"},"done":false}
{"model":"support-agent","created_at":"2026-04-08T12:00:01Z","message":{"role":"assistant","content":" can"},"done":false}
{"model":"support-agent","created_at":"2026-04-08T12:00:01Z","message":{"role":"assistant","content":""},"done":true,"total_duration":1234567890}
```

---

### `POST /ollama/api/generate`

Text generation (legacy, single-turn).

```bash
curl -X POST http://localhost:8765/ollama/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "support-agent",
    "prompt": "Summarize this ticket: customer wants refund",
    "stream": false
  }'
```

---

### `GET /ollama/api/tags`

List available "models" — returns all configured Agent Studio personas alongside any locally installed Ollama models.

```bash
curl http://localhost:8765/ollama/api/tags
```

**Response:**
```json
{
  "models": [
    {
      "name": "support-agent",
      "modified_at": "2026-04-08T12:00:00Z",
      "size": 0,
      "details": {
        "format": "agentic-core-persona",
        "family": "anthropic"
      }
    },
    {
      "name": "llama3.2:latest",
      "modified_at": "2026-04-01T09:00:00Z",
      "size": 4700000000
    }
  ]
}
```

---

### `POST /ollama/api/show`

Show model / persona details.

```bash
curl -X POST http://localhost:8765/ollama/api/show \
  -d '{"name": "support-agent"}'
```

---

## Using with Open WebUI

1. Start Agent Studio: `make up`
2. In Open WebUI, go to **Settings → Connections**
3. Set the Ollama API URL to `http://localhost:8765/ollama`
4. Your Agent Studio personas appear alongside local Ollama models

---

## Using with Continue.dev

In `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Support Agent",
      "provider": "ollama",
      "model": "support-agent",
      "apiBase": "http://localhost:8765/ollama"
    }
  ]
}
```

---

## Notes

- **Tools are active**: When you chat via the Ollama API, Agent Studio still executes MCP tools, applies gates, and tracks the session — unlike a direct Ollama call.
- **Model fallthrough**: If the model name does not match any persona, the request is proxied to the real Ollama instance at `AGENTIC_OLLAMA_URL`.
- **Session tracking**: Each Ollama chat request creates or continues an Agent Studio session. Pass `options.session_id` in the request to explicitly resume a session.
