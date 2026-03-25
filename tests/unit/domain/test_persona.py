from agentic_core.domain.entities.persona import (
    DelegateConfig,
    EscalationRule,
    Persona,
    PersonaCapabilities,
)
from agentic_core.domain.enums import GraphTemplate, PersonaCapability
from agentic_core.domain.value_objects.model_config import ModelConfig


def test_persona_defaults():
    p = Persona(name="test", role="tester", description="A test persona")
    assert p.graph_template == GraphTemplate.REACT
    assert p.skills == []
    assert p.tools == []
    assert p.model_config is None
    assert p.graph_cls is None


def test_persona_with_escalation_rules():
    rules = [
        EscalationRule(condition="billing_amount > 500", target="billing-agent"),
        EscalationRule(condition="sentiment < -0.7", target="human", priority="urgent"),
    ]
    p = Persona(name="support", role="support", description="Support", escalation_rules=rules)
    assert len(p.escalation_rules) == 2
    assert p.escalation_rules[1].priority == "urgent"


def test_persona_capabilities():
    caps = PersonaCapabilities(gsd_enabled=True, auto_research=True)
    enabled = caps.enabled_list()
    assert PersonaCapability.GSD in enabled
    assert PersonaCapability.AUTO_RESEARCH in enabled
    assert PersonaCapability.SUPERPOWERS not in enabled


def test_delegate_model_config():
    p = Persona(
        name="orchestrator",
        role="orchestrator",
        description="Orchestrator",
        delegate_to=[
            DelegateConfig(name="researcher", model_config=ModelConfig(model="claude-opus-4-6")),
            DelegateConfig(name="writer"),
        ],
    )
    assert p.get_delegate_model_config("researcher") is not None
    assert p.get_delegate_model_config("researcher").model == "claude-opus-4-6"  # type: ignore[union-attr]
    assert p.get_delegate_model_config("writer") is None
    assert p.get_delegate_model_config("nonexistent") is None
