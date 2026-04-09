from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from agentic_core.domain.entities.persona import (
    DelegateConfig,
    EscalationRule,
    Persona,
    PersonaCapabilities,
)
from agentic_core.domain.enums import GraphTemplate
from agentic_core.domain.value_objects.model_config import ModelConfig
from agentic_core.domain.value_objects.slo import SLOTargets

if TYPE_CHECKING:
    from collections.abc import Callable

    from agentic_core.domain.services.routing import RoutingService
    from agentic_core.graph_templates.base import BaseAgentGraph

logger = logging.getLogger(__name__)

# Global registry for @agent_persona decorator
_GRAPH_REGISTRY: dict[str, type[BaseAgentGraph]] = {}


def agent_persona(persona_name: str) -> Callable[[type[BaseAgentGraph]], type[BaseAgentGraph]]:
    """Decorator to register a graph class for a persona.
    The class overrides the YAML graph_template when present."""

    def decorator(cls: type[BaseAgentGraph]) -> type[BaseAgentGraph]:
        _GRAPH_REGISTRY[persona_name] = cls
        return cls

    return decorator


class PersonaRegistry:
    """Discovers personas from YAML files and connects them with graph classes."""

    def __init__(self, routing_service: RoutingService) -> None:
        self._routing = routing_service

    def discover(self, personas_dir: str | Path) -> int:
        path = Path(personas_dir)
        if not path.exists():
            logger.warning("Personas directory not found: %s", path)
            return 0

        count = 0
        for yaml_file in sorted(path.glob("*.yaml")):
            try:
                persona = self._load_yaml(yaml_file)
                # Wire graph class from decorator registry
                if persona.name in _GRAPH_REGISTRY:
                    persona.graph_cls = _GRAPH_REGISTRY[persona.name]
                self._routing.register(persona)
                count += 1
                logger.info("Loaded persona: %s (template=%s)", persona.name, persona.graph_template.value)
            except Exception:
                logger.exception("Failed to load persona from %s", yaml_file)
        return count

    def _load_yaml(self, path: Path) -> Persona:
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f)

        model_config = None
        if mc := data.get("model_config"):
            model_config = ModelConfig(**mc)

        slo_targets = None
        if slo := data.get("slo_targets"):
            slo_targets = SLOTargets(**slo)

        caps_data = data.get("capabilities", {})
        capabilities = PersonaCapabilities(
            gsd_enabled=caps_data.get("gsd_enabled", False),
            superpowers_flow=caps_data.get("superpowers_flow", False),
            auto_research=caps_data.get("auto_research", False),
        )

        escalation_rules = [
            EscalationRule(**r) for r in data.get("escalation_rules", [])
        ]

        delegate_to = []
        for d in data.get("delegate_to", []):
            d_mc = ModelConfig(**d["model_config"]) if "model_config" in d else None
            delegate_to.append(DelegateConfig(name=d["name"], model_config=d_mc))

        template_str = data.get("graph_template", "react")
        graph_template = GraphTemplate(template_str)

        return Persona(
            name=data["name"],
            role=data.get("role", ""),
            description=data.get("description", ""),
            graph_template=graph_template,
            skills=data.get("skills", []),
            tools=data.get("tools", []),
            escalation_rules=escalation_rules,
            model_config=model_config,
            capabilities=capabilities,
            slo_targets=slo_targets,
            delegate_to=delegate_to,
        )
