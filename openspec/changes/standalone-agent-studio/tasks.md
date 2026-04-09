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
- [x] **AD-01** Agregar aiohttp a pyproject.toml (optional: standalone)
- [x] **AD-02** Crear HTTP API adapter (REST routes + static serving + SPA fallback)

### Runtime
- [x] **RT-01** Agregar settings: http_port, static_dir, api_enabled
- [x] **RT-02** Modificar runtime.py para iniciar aiohttp en modo standalone

### Infraestructura
- [x] **INF-01** Crear docker-compose.yml (4 services, healthchecks, volumes)
- [x] **INF-02** Actualizar Dockerfile (multi-stage con Flutter Web build)

### UI Placeholder
- [x] **UI-01** Crear Flutter Web app minima (pubspec.yaml, main.dart, index.html)

### Testing
- [x] **TE-01** Tests unitarios HTTP API adapter (12 tests)
- [x] **TE-02** Smoke test E2E (ciclo completo de agente)

## Plan 2: Flutter Web UI

### Scaffold
- [x] **FE-01** Configurar tema AduaNext (dark theme, Material 3, tokens de color)
- [x] **FE-02** Implementar DashboardLayout (rail + panel + content)
- [x] **FE-03** Configurar GoRouter con ShellRoute

### Paginas
- [x] **FE-04** ChatPage (home) con selector de agente y WebSocket streaming
- [x] **FE-05** AgentEditorPage con tabs (Inputs, Guardrails, Outputs) y cards
- [x] **FE-06** Gates editor (TextField Markdown, flutter_quill pendiente)
- [x] **FE-07** SessionsPage (historial con status badges)
- [x] **FE-08** ToolsPage (MCP servers + health status)
- [x] **FE-09** SettingsPage con tabs (Conexiones, Modelos, Variables, Debug, Docker)
- [x] **FE-10** MetricsPage con KPIs y chart placeholders (graphic pendiente)

### Componentes
- [x] **FE-11** SidebarRail + SidebarPanel (patron aduanext)
- [ ] **FE-12** DebugTerminal (xterm Dart puro) — placeholder implementado
- [x] **FE-13** Atomic design audit con /atomic-design-toolkit:audit:material3

### Integraciones
- [x] **FE-14** Integrar flutter_quill para WYSIWYG Markdown en gates
- [x] **FE-15** Integrar xterm (Dart puro) para terminal debug real
- [x] **FE-16** Integrar graphic para charts reales en MetricsPage

### Pendientes para iteracion futura
- [ ] **FE-17** API client conectado en todas las paginas (datos reales vs mock)
- [ ] **FE-18** WebSocket real en terminal debug (logs en vivo del container)
- [ ] **FE-19** Métricas reales desde /api/metrics en los charts
