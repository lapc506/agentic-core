# Cambio: docs-infrastructure

**Change ID:** docs-infrastructure
**Fecha:** 2026-04-09

## Que
Infraestructura de documentacion para agentic-core: sitio Zensical con 13 paginas, specs tecnicas en MyST, Makefile con targets de build, tabla comparativa en README y estructura OpenSpec.

## Por que
- El proyecto no tenia documentacion publica estructurada
- Los desarrolladores necesitan API reference y guias de integracion
- La tabla comparativa en README demuestra el posicionamiento vs competidores
- OpenSpec + linear-setup.json estandariza el tracking de cambios arquitectonicos

## Alcance
### Incluido
- Sitio Zensical: 13 paginas con estructura jerarquica (guias, conceptos, referencia API)
- MyST technical specs: especificaciones tecnicas en formato MyST Markdown
- Makefile targets: docs-site (Zensical), docs-specs (MyST), docs (ambos)
- README: tabla comparativa vs ElizaOS/OpenClaw/Gemini CLI/Claude Code
- README: instrucciones de demo standalone con Docker
- OpenSpec: estructura de directorios + linear-setup.json para tracking

### Pendiente
- GitHub Pages deployment automatico desde CI
- API docs auto-generados desde Python docstrings (Sphinx/pdoc)
- Changelog automation (conventional commits → CHANGELOG.md)

## Etiquetas
- Tipo: docs
- Tamano: M
- Prioridad: media
