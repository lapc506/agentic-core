# Diseno: genui-integration

## Arquitectura

Flutter frontend se comunica con el backend Python via WebSocket. El A2uiTransportAdapter traduce mensajes WebSocket al protocolo A2A. GenUI renderiza UI dinamica basada en los eventos del agente.

## Capas

```
ChatPage
  └── SurfaceController (GenUI)
        ├── BasicCatalogItems (text, form, confirmation, tool_result)
        └── A2uiTransportAdapter
              └── WebSocket → AgentHttpClient → Python Backend
```

## Componentes implementados

| Componente | Descripcion | Estado |
|---|---|---|
| ChatPage (rewrite) | Pagina principal con GenUI + A2A | Completado |
| SurfaceController | Controlador de superficies GenUI | Completado |
| BasicCatalogItems | Items de catalogo basicos (text, forms) | Completado |
| A2uiTransportAdapter | Bridge WebSocket ↔ A2A protocol | Completado |
| HITL ActionDelegate | Delegado para confirmaciones humanas | Completado |
| AgentSelector | Dropdown con lista de agentes disponibles | Completado |
| ConnectionStatus | Indicador de estado de conexion | Completado |

## Protocolo A2A

El agente envia eventos con estructura:
- `task.submitted` — nueva tarea recibida
- `task.working` — procesando, con tool calls opcionales
- `task.completed` — resultado final
- `task.failed` — error con razon
- `hitl.confirm_required` — requiere confirmacion humana

## Pendiente

- AG-UI SSE: endpoint `/events` en backend para Server-Sent Events
- Custom catalog items: componentes Flutter para tool-specific UIs
- State sync: cada interaccion UI envia contexto al agente
