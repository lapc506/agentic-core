# Deployment: Standalone vs Sidecar

Agent Studio supports two deployment topologies controlled by a single environment variable: `AGENTIC_MODE`.

---

## Standalone Mode

In standalone mode, Agent Studio runs as an independent service with its own network ingress. External clients (Flutter app, TUI, Ollama-compatible tools) connect directly via WebSocket on port `8765`.

```
Flutter Client
    │
    └─── WebSocket (Ingress :8765)
              │
         ┌────▼────────────────────┐
         │  agentic-core           │
         │  :8765 WS               │
         │  :50051 gRPC            │
         └────┬────────────────────┘
              │
    ┌─────────▼─────────┐
    │  NestJS / Backend │
    │  (gRPC service)   │
    └───────────────────┘
```

The backend communicates with Agent Studio via gRPC using service DNS. The Flutter client connects directly through the ingress.

**Use standalone mode for:**
- The local demo (`make up`)
- Projects where Agent Studio is the primary backend
- Kubernetes deployments where you want a dedicated agent service

---

## Sidecar Mode

In sidecar mode, Agent Studio runs in the **same Kubernetes Pod** as the application backend. The two containers share a network namespace, so communication happens over `localhost` — no ingress required for gRPC.

```
Flutter Client
    │
    └─── WebSocket (Ingress :8765)
              │
         ┌────▼─────────────────────────┐
         │  Pod (shared network ns)     │
         │  ┌───────────────────┐       │
         │  │  agentic-core     │       │
         │  │  127.0.0.1:8765   │       │
         │  │  127.0.0.1:50051  │◄──────┤── gRPC localhost
         │  └───────────────────┘       │
         │  ┌───────────────────┐       │
         │  │  NestJS / Backend │       │
         │  └───────────────────┘       │
         └──────────────────────────────┘
```

The backend calls `localhost:50051` (gRPC) with zero network latency. The Flutter client still reaches `agentic-core` through the Pod's ingress at `:8765`.

**Use sidecar mode for:**
- Existing Kubernetes applications adding agent capabilities
- When you want the tightest coupling between backend and agent runtime
- Multi-tenant deployments where each application gets its own agent runtime

---

## Configuring the Mode

```bash
AGENTIC_MODE=standalone   # default
AGENTIC_MODE=sidecar
```

In sidecar mode, the runtime binds to `127.0.0.1` by default (loopback only). In standalone mode, it binds to `0.0.0.0`.

---

## Kubernetes Deployment

Agent Studio ships a Helm chart that supports both modes.

### Standalone (separate Deployment)

```yaml
# helm/values.yaml
mode: standalone
service:
  type: ClusterIP
  port: 8765
ingress:
  enabled: true
  host: agent-studio.example.com
```

```bash
helm install agentic-core ./helm -f values.yaml
```

### Sidecar Injection

Add the sidecar to your existing Deployment:

```yaml
# your-app/deployment.yaml
spec:
  template:
    spec:
      containers:
        - name: your-app
          image: your-app:latest

        - name: agentic-core          # sidecar
          image: ghcr.io/lapc506/agentic-core:latest
          env:
            - name: AGENTIC_MODE
              value: sidecar
            - name: AGENTIC_REDIS_URL
              value: redis://redis-service:6379
          ports:
            - containerPort: 50051    # gRPC (localhost only)
            - containerPort: 8765     # WebSocket (via ingress)
```

---

## Integration Patterns

Agent Studio is currently deployed by five applications, each with a different frontend protocol:

| Application | Backend | Frontend Protocol |
|-------------|---------|-------------------|
| aduanext | gRPC native | gRPC |
| altrupets | NestJS | GraphQL |
| vertivolatam | Serverpod | Serverpod RPC |
| habitanexus | Direct | WebSocket |
| standalone demo | REST API | REST + WebSocket |

In all cases, Agent Studio's internal API is the same. Only the adapter layer changes.

---

## Resource Requirements

**Minimum (standalone demo):**

| Container | CPU | Memory |
|-----------|-----|--------|
| agentic-core | 250m | 512Mi |
| redis | 100m | 128Mi |
| postgres | 250m | 256Mi |
| falkordb | 250m | 512Mi |

**Production (sidecar):**

Adjust based on concurrent sessions and model response sizes. A single agentic-core instance comfortably handles 50 concurrent WebSocket sessions on 1 CPU / 1 GiB.
