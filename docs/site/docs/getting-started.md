# Getting Started

This guide walks you from zero to a running Agent Studio instance in under five minutes.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker or Podman | 24+ / 4+ | Podman is the default in `make up` |
| Flutter SDK | 3.x | Only needed if you want to rebuild the web UI |
| Python | 3.12+ | Only needed for library usage / development |

For the quickest path — just Docker/Podman is enough.

---

## 1. Clone the Repository

```bash
git clone https://github.com/lapc506/agentic-core.git
cd agentic-core
```

---

## 2. Start Agent Studio

```bash
make up
```

`make up` does three things automatically:

1. Compiles the Flutter Web UI (`flutter build web --release`)
2. Builds the Python Docker image
3. Starts all four containers via `podman compose up -d`

The first run takes roughly 90 seconds (Flutter compile + Docker build). Subsequent runs are much faster because layers are cached.

---

## 3. Open the UI

Once `make up` finishes:

```
Agent Studio running at http://localhost:8765
```

Open **http://localhost:8765** in your browser. You should see the Agent Studio chat interface.

---

## 4. What's Running

| Container | Port | Purpose |
|-----------|------|---------|
| agentic-core | 8765 | Python runtime + Flutter UI + REST API + WebSocket |
| redis | 6379 (internal) | Session memory store |
| postgres | 5432 (internal) | Agent persistence + embeddings |
| falkordb | 6380 (internal) | Graph store |

All services include healthchecks. The `agentic-core` container waits for its dependencies before accepting connections.

---

## 5. Configure Your First Agent

Create a persona file in your project:

```yaml
# agents/my-agent.yaml
name: my-agent
role: "Customer support specialist"
graph_template: react
tools:
  - rag_search
model_config:
  provider: openrouter
  model: anthropic/claude-sonnet-4-6
  temperature: 0.3
```

See the [Personas guide](guides/personas.md) for the full YAML schema and Python override pattern.

---

## Development Workflow

For iterating on the UI without rebuilding Docker:

```bash
# Terminal 1 — dependencies + backend only
docker compose up redis postgres falkordb
AGENTIC_MODE=standalone \
  AGENTIC_REDIS_URL=redis://localhost:6379 \
  AGENTIC_POSTGRES_DSN=postgresql://agentic:agentic@localhost:5432/agentic \
  AGENTIC_FALKORDB_URL=redis://localhost:6380 \
  python -m agentic_core.runtime

# Terminal 2 — Flutter hot reload
cd ui
flutter run -d chrome
```

---

## Next Steps

- [Standalone Mode](standalone.md) — full Docker Compose reference and environment variables
- [REST API](api/rest.md) — all endpoints with curl examples
- [Providers Guide](guides/providers.md) — connect OpenRouter, Ollama, LM Studio, Fireworks
