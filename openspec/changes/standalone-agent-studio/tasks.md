# Tasks: standalone-agent-studio

**Plan completo:** `docs/superpowers/plans/2026-04-08-standalone-backend-docker.md`

## Plan 1: Backend + Docker

### Dominio
- [x] **DO-01** Crear Gate value object (Pydantic frozen) + GateAction enum
- [x] **DO-02** Agregar campo `gates: list[Gate]` a Persona entity

### Application — Commands
- [x] **AP-01** CreateAgentCommand + Handler (YAML persistence, slugify)
- [x] **AP-02** UpdateAgentCommand + Handler (allowed keys only)
- [x] **AP-03** UpdateGatesCommand + Handler (Gate objects, YAML persistence)

### Application — Queries
- [x] **AP-04** ListAgentsQuery + Handler (read YAML dir, add slug)
- [x] **AP-05** ListToolsQuery + Handler (ToolPort + healthcheck)
- [x] **AP-06** GetMetricsQuery + Handler (stub, in-memory store)

### Adapters
- [ ] **AD-01** Agregar aiohttp a pyproject.toml (optional: standalone)
- [ ] **AD-02** Crear HTTP API adapter (REST routes + static serving + SPA fallback)

### Runtime
- [ ] **RT-01** Agregar settings: http_port, static_dir, api_enabled
- [ ] **RT-02** Modificar runtime.py para iniciar aiohttp en modo standalone

### Infraestructura
- [ ] **INF-01** Crear docker-compose.yml (4 services, healthchecks, volumes)
- [ ] **INF-02** Actualizar Dockerfile (multi-stage con Flutter Web build)

### UI Placeholder
- [ ] **UI-01** Crear Flutter Web app minima (pubspec.yaml, main.dart, index.html)

### Testing
- [ ] **TE-01** Tests unitarios HTTP API adapter (6+ tests)
- [ ] **TE-02** Smoke test E2E (ciclo completo de agente)

## Plan 2: Flutter Web UI (pendiente)

### Scaffold
- [ ] **FE-01** Configurar tema AduaNext (dark theme, Material 3, tokens de color)
- [ ] **FE-02** Implementar DashboardLayout (rail + panel + content)
- [ ] **FE-03** Configurar GoRouter con ShellRoute

### Paginas
- [ ] **FE-04** ChatPage (home) con selector de agente y WebSocket streaming
- [ ] **FE-05** AgentEditorPage con tabs (Inputs, Guardrails, Outputs) y cards
- [ ] **FE-06** Gates editor con flutter_quill WYSIWYG y flip animation
- [ ] **FE-07** SessionsPage (historial + escalaciones HITL)
- [ ] **FE-08** ToolsPage (MCP servers + health status)
- [ ] **FE-09** SettingsPage con tabs (Conexiones, Modelos, Variables, Debug, Docker)
- [ ] **FE-10** MetricsPage con charts graphic (latencia, tokens, gates, sesiones)

### Componentes
- [ ] **FE-11** SidebarRail + SidebarPanel (patron aduanext)
- [ ] **FE-12** DebugTerminal (xterm Dart puro)
- [ ] **FE-13** Atomic design audit con /atomic-design-toolkit:audit:material3
