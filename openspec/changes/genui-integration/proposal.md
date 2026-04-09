# Cambio: genui-integration

**Change ID:** genui-integration
**Fecha:** 2026-04-09

## Que
Integracion de Flutter GenUI con el protocolo A2A (Agent-to-Agent) en la ChatPage del Standalone Agent Studio. GenUI permite que el agente genere UI dinamica en respuesta a sus acciones, eliminando la necesidad de hardcodear cada tipo de interaccion.

## Por que
- La ChatPage actual usa WebSocket raw sin protocolo estructurado
- A2A define un ciclo de vida de tareas estandar (submit → working → completed/failed)
- GenUI permite al agente controlar la UI desde el backend (tool calls, confirmaciones, formularios)
- HITL (Human-in-the-Loop) requiere un mecanismo de confirmacion en el frontend

## Alcance
### Incluido
- Rewrite de ChatPage con GenUI + A2A
- SurfaceController con BasicCatalogItems
- A2uiTransportAdapter bridging WebSocket a protocolo A2A
- HITL ActionDelegate para confirmation dialogs
- Agent selector y connection status

### Pendiente
- Custom catalog items para tools especificos de agentic-core
- AG-UI SSE endpoint en el backend Python
- State sync bidireccional (UI interactions → agent context)
- Auto-respond en tool interactions sin confirmacion
- DevTools panel (tool calls, token budget, memory status)

## Etiquetas
- Tipo: feature
- Tamano: M
- Prioridad: alta
