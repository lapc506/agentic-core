# Diseno: gemini-cli-patterns

## Arquitectura

Los patrones Gemini CLI se implementan como capas transversales sobre el runtime del agente. Algunos son middleware (policy engine, model steering), otros son modos de operacion (Plan Mode, ACP Mode) y otros son servicios de estado (checkpointing, rewind).

## Patrones a implementar

### Policy Engine (GEM-01)
- Archivo: `services/policy_engine.py`
- Reglas TOML con 5 niveles de prioridad: system > enterprise > project > user > default
- Acciones: allow / deny / ask (requiere confirmacion HITL)
- Evaluacion antes de cada tool call

### Plan Mode (GEM-02)
- Flag `--plan` en CLI y modo en TUI
- Restringe tools a read-only durante la fase de investigacion
- Genera artefacto `PLAN.md` antes de pedir confirmacion para ejecutar

### Checkpointing (GEM-03)
- Shadow git repo en `.agentic-studio/checkpoints/`
- Snapshot automatico antes de cualquier mutacion (write, edit, bash)
- Metadata: timestamp, tool_call, descripcion

### Rewind (GEM-04)
- Comando `/rewind` en TUI
- Lista checkpoints disponibles con diff
- Restaura archivos + trunca historial de conversacion al punto seleccionado

### Progressive Skill Disclosure (GEM-05)
- Skills definidos en `skills/` con metadata de activacion
- Tool `activate_skill(name)` para cargar bajo demanda
- Reduce tokens iniciales del system prompt

### Model Steering (GEM-06)
- Canal de hints fuera del contexto principal
- El usuario puede escribir hints mientras el agente trabaja
- Hints se inyectan como mensajes de sistema en el siguiente step

## Stack tecnico
- Policy rules: TOML
- Checkpoints: git plumbing (git hash-object, git write-tree)
- Rewind UI: lista interactiva en TUI (Bubble Tea)
- ACP Mode: JSON-RPC 2.0 sobre stdio
