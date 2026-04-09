import pytest

from agentic_core.domain.value_objects.gate import Gate, GateAction


def test_gate_creation():
    gate = Gate(name="PII Filter", content="## PII Filter\nRedact personal information.", action=GateAction.BLOCK, order=0)
    assert gate.name == "PII Filter"
    assert gate.action == GateAction.BLOCK
    assert gate.order == 0


def test_gate_is_frozen():
    gate = Gate(name="Test", content="body", action=GateAction.WARN, order=0)
    with pytest.raises(Exception):
        gate.name = "changed"


def test_gate_missing_required_fields_raises():
    with pytest.raises(Exception):
        Gate(name="X", content="y", action=GateAction.BLOCK)  # missing order


def test_gate_action_enum():
    assert GateAction.BLOCK.value == "block"
    assert GateAction.WARN.value == "warn"
    assert GateAction.REWRITE.value == "rewrite"
    assert GateAction.HITL.value == "hitl"


def test_persona_with_gates():
    from agentic_core.domain.entities.persona import Persona
    from agentic_core.domain.value_objects.gate import Gate, GateAction

    gates = [
        Gate(name="PII", content="Filter PII", action=GateAction.BLOCK, order=0),
        Gate(name="Tone", content="Check tone", action=GateAction.REWRITE, order=1),
    ]
    persona = Persona(name="Test", role="assistant", description="test", gates=gates)
    assert len(persona.gates) == 2
    assert persona.gates[0].name == "PII"
    assert persona.gates[1].order == 1
