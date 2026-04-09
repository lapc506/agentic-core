from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from agentic_core.domain.enums import GraphTemplate, PersonaCapability

if TYPE_CHECKING:
    from agentic_core.application.services.context_loader import PersonalityConfig
    from agentic_core.domain.value_objects.gate import Gate
    from agentic_core.domain.value_objects.model_config import ModelConfig
    from agentic_core.domain.value_objects.slo import SLOTargets
    from agentic_core.graph_templates.base import BaseAgentGraph


@dataclass
class EscalationRule:
    condition: str
    target: str
    priority: str = "normal"


@dataclass
class PersonaCapabilities:
    gsd_enabled: bool = False
    superpowers_flow: bool = False
    auto_research: bool = False

    def enabled_list(self) -> list[PersonaCapability]:
        result: list[PersonaCapability] = []
        if self.gsd_enabled:
            result.append(PersonaCapability.GSD)
        if self.superpowers_flow:
            result.append(PersonaCapability.SUPERPOWERS)
        if self.auto_research:
            result.append(PersonaCapability.AUTO_RESEARCH)
        return result


@dataclass
class DelegateConfig:
    name: str
    model_config: ModelConfig | None = None


@dataclass
class Persona:
    name: str
    role: str
    description: str
    graph_template: GraphTemplate = GraphTemplate.REACT
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    escalation_rules: list[EscalationRule] = field(default_factory=list)
    model_config: ModelConfig | None = None
    capabilities: PersonaCapabilities = field(default_factory=PersonaCapabilities)
    slo_targets: SLOTargets | None = None
    delegate_to: list[DelegateConfig] = field(default_factory=list)
    graph_cls: type[BaseAgentGraph] | None = None
    personality: PersonalityConfig | None = None
    gates: list[Gate] = field(default_factory=list)

    def get_delegate_model_config(self, delegate_name: str) -> ModelConfig | None:
        for d in self.delegate_to:
            if d.name == delegate_name:
                return d.model_config
        return None
