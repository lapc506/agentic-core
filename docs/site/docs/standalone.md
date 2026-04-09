# Standalone Mode

Standalone mode runs the complete Agent Studio stack as a local Docker Compose application. This is the recommended way to demo or develop against a full environment.

---

## Quick Start

```bash
make up
```

Or step by step:

```bash
make build-web      # compile Flutter Web UI (~30 sec)
make build-docker   # build Python image (~60 sec)
podman compose up   # start all four containers
```

---

## Docker Compose Services

```yaml
# docker-compose.yml (excerpt)
services:
  agentic-core:
    image: ghcr.io/lapc506/agentic-core
    ports:
      - "8765:8765"
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
      falkordb:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    # port 6379 internal only

  postgres:
    image: pgvector/pgvector:pg16
    # port 5432 internal only

  falkordb:
    image: falkordb/falkordb:latest
    # port 6380 internal only
```

All services include healthchecks. `agentic-core` will not start until Redis, PostgreSQL, and FalkorDB pass their health probes.

---

## Environment Variables

Set these on the `agentic-core` container (or export locally when running the backend without Docker):

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTIC_MODE` | `standalone` | Deployment mode: `standalone` or `sidecar` |
| `AGENTIC_REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `AGENTIC_POSTGRES_DSN` | `postgresql://agentic:agentic@postgres:5432/agentic` | PostgreSQL DSN |
| `AGENTIC_FALKORDB_URL` | `redis://falkordb:6380` | FalkorDB connection URL (uses Redis protocol) |
| `AGENTIC_DEFAULT_MODEL` | _(none)_ | Default LLM for all agents (e.g., `anthropic/claude-sonnet-4-6`) |
| `AGENTIC_OPENROUTER_API_KEY` | _(none)_ | API key for OpenRouter |
| `AGENTIC_OLLAMA_URL` | `http://localhost:11434` | Ollama base URL |
| `AGENTIC_LOG_LEVEL` | `INFO` | Python log level |
| `AGENTIC_OTEL_ENDPOINT` | _(none)_ | OpenTelemetry collector OTLP endpoint |
| `AGENTIC_LANGFUSE_PUBLIC_KEY` | _(none)_ | Langfuse public key for LLM cost tracking |
| `AGENTIC_LANGFUSE_SECRET_KEY` | _(none)_ | Langfuse secret key |

---

## Exposed Ports

| Port | Protocol | Description |
|------|----------|-------------|
| `8765` | HTTP / WebSocket | Flutter UI, REST API, WebSocket streaming |
| `50051` | gRPC | Backend-to-sidecar communication (sidecar mode) |

In standalone mode, only port `8765` is exposed to the host. Internal service ports stay within the Compose network.

---

## Stopping and Cleanup

```bash
make down          # stop all containers (data persists in volumes)
make clean         # stop + remove volumes + remove the Docker image
```

---

## Using Podman vs Docker

The Makefile defaults to `podman compose`. If you prefer plain Docker:

```bash
docker compose up -d
```

Both work identically — the Compose file is compatible with both runtimes.

---

## Customizing the Compose File

To add your own MCP servers or override provider credentials, create a `docker-compose.override.yml` in the project root:

```yaml
services:
  agentic-core:
    environment:
      AGENTIC_OPENROUTER_API_KEY: "sk-or-..."
      AGENTIC_DEFAULT_MODEL: "anthropic/claude-opus-4-6"
```

Docker/Podman Compose automatically merges override files.
