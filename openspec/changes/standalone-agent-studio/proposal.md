# Cambio: standalone-agent-studio

**Change ID:** standalone-agent-studio
**Fecha:** 2026-04-08
**Branch:** feat/standalone-agent-studio-backend

## Que

Modo standalone de agentic-core que corre con Docker/Podman sin depender de Kubernetes. Incluye una Flutter Web UI ("Agent Studio") para configurar agentes, probar conversaciones y monitorear metricas.

## Por que

- **Demo con clientes:** Necesitamos una forma de mostrar agentic-core sin infraestructura de produccion. `docker compose up` → `localhost:8765` y listo.
- **Experiencia zero-config:** El cliente no necesita saber de K8s, Helm, o Terraform.
- **Agent Studio UI:** Los usuarios no-tecnicos (product managers, operadores) necesitan configurar agentes visualmente: personalidad, guardrails, reglas de negocio.

## Alcance

### Incluido (Plan 1 — Backend + Docker)
- REST API adapter (aiohttp) para CRUD de agentes, gates, metricas
- Gate Value Object en el dominio
- Static file serving desde agentic-core
- docker-compose.yml con healthchecks (Redis, PostgreSQL+pgvector, FalkorDB)
- Dockerfile multi-stage (Python + Flutter Web)
- Placeholder Flutter Web app

### Incluido (Plan 2 — Flutter Web UI, pendiente)
- Flutter Web app completa con tema oscuro estilo aduanext
- Sidebar: Chat (home), Cliente, Reglas, Sesiones, Herramientas, Sistema, Metricas
- Editor de agentes con tabs (Inputs, Guardrails, Outputs) y cards
- Gates con editor WYSIWYG Markdown (flutter_quill)
- Terminal debug (xterm, Dart puro)
- Charts con graphic (Grammar of Graphics)

### Excluido
- Observabilidad de produccion (Alloy/Grafana/Prometheus)
- Auth multi-tenant
- Despliegue Kubernetes (ya existe por separado)
- Hot reload en Docker

## Etiquetas

- **Tipo:** feature
- **Prioridad:** alta
- **Tamano:** L (semanas)
- **Dependencias:** ninguna (es un nuevo modo de despliegue)
- **Personas afectadas:** desarrolladores, clientes en demo

## Criterios de Aceptacion

- [ ] `docker compose up` levanta el stack completo en < 2 minutos
- [ ] `localhost:8765` muestra la UI del Agent Studio
- [ ] Se pueden crear, editar y eliminar agentes via REST API
- [ ] Los gates son editables con contenido Markdown
- [ ] Compatible con Podman Compose (rootless)
