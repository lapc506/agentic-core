# Cambio: gemini-cli-patterns

**Change ID:** gemini-cli-patterns
**Fecha:** 2026-04-09

## Que
Adopcion de patrones de Gemini CLI en agentic-core: policy engine, Plan Mode, checkpointing, rewind, progressive skill disclosure, model steering y herramientas avanzadas de control del agente.

## Por que
- Gemini CLI introdujo patrones de seguridad y control que son best practices en 2026
- Policy engine con reglas TOML permite control granular sin codigo
- Plan Mode previene mutaciones no deseadas durante investigacion
- Checkpointing + Rewind da al usuario control total sobre el estado del agente
- Progressive skill disclosure reduce el context window inicial

## Alcance
### Incluido (pendiente de implementacion)
- Policy engine: reglas TOML con allow/deny/ask, 5 niveles de prioridad
- Plan Mode: modo read-only que genera un plan antes de ejecutar
- Checkpointing: snapshots git automaticos antes de cada mutacion
- Rewind: revertir conversacion y archivos a cualquier punto anterior
- Progressive skill disclosure: skills se cargan bajo demanda
- Model steering: hints en tiempo real mientras el agente trabaja
- Tool output masking: filtrar/destilar outputs sensibles o verbosos
- Custom TOML commands: comandos personalizados en .agentic-studio/commands/
- Enterprise admin controls: configuracion inmutable desde nivel sistema
- ACP Mode: integracion JSON-RPC stdio para IDEs
- Context file imports: sintaxis @file.md para incluir archivos en contexto

## Etiquetas
- Tipo: feature
- Tamano: L
- Prioridad: media
