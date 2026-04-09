# Spec: agentic-core Architecture

**Dominio:** core
**Servicios afectados:** All layers
**Ultima actualizacion:** 2026-04-09

## Vision General

agentic-core es una libreria Python 3.12+ de orquestacion de agentes AI. Arquitectura Hexagonal + DDD + CQRS. Todas las dependencias apuntan hacia adentro.

## Capas

### Primary Adapters (Driving)
- WebSocket (chat streaming, HITL)
- gRPC (backend-to-sidecar)
- HTTP API (REST + static + Ollama-compatible)
- A2A Protocol (agent-to-agent JSON-RPC)
- CLI / TUI (Go, Bubble Tea)

### Application Layer
- Commands: HandleMessage, CreateSession, CreateAgent, UpdateAgent, UpdateGates
- Queries: GetSession, ListPersonas, ListAgents, ListTools, GetMetrics
- Ports: 16 interfaces (Memory, Session, Embedding, Graph, Tool, Tracing, etc.)
- Services: PersonaRegistry, GSD, Superpowers, AutoResearch, MemoryExtraction, SkillCreation, MemoryManager, PersonaRouter, GraphService, HITLConfirmation, ToolViews, CodingTools, ToolCache, ContextBudget, SecurityAuditor, IterationBudget, DeploymentGates

### Domain Layer (zero dependencies)
- Entities: Session, Persona, Skill, Roadmap
- Value Objects: AgentMessage, Gate, ModelConfig, SLOTargets, TrajectoryScore
- Events: MessageProcessed, SLOBreached, ToolDegraded, HumanEscalation
- Services: Routing, Escalation, EvalScoring, ModelResolver, TrajectoryEvaluator

### Secondary Adapters (Driven)
- Redis, PostgreSQL+pgvector, FalkorDB
- MCP Bridge + OAuth 2.1, OpenTelemetry, Langfuse
- LangGraph (6 templates: ReAct, Plan-Execute, Reflexion, LLM-Compiler, Supervisor, HTN)

## Interfaces
- Flutter Web UI (Agent Studio) — GenUI + A2A
- Go TUI (Bubble Tea) — 20 Ralph patterns
- Ollama-compatible API
- REST API + WebSocket

## Deployment
- Standalone: docker compose up (Python + Flutter Web + Redis + PG + FalkorDB)
- Sidecar: Kubernetes Helm chart
