import json

from agentic_core.domain.enums import (
    EmbeddingTaskType,
    GraphTemplate,
    PersonaCapability,
    SessionState,
)


def test_session_states():
    assert SessionState.ACTIVE == "active"
    assert SessionState.PAUSED == "paused"
    assert SessionState.ESCALATED == "escalated"
    assert SessionState.COMPLETED == "completed"
    assert len(SessionState) == 4


def test_graph_templates():
    assert GraphTemplate.REACT == "react"
    assert GraphTemplate.PLAN_EXECUTE == "plan-and-execute"
    assert GraphTemplate.ORCHESTRATOR == "orchestrator"
    assert len(GraphTemplate) == 6


def test_embedding_task_types():
    assert len(EmbeddingTaskType) == 8
    assert EmbeddingTaskType.CODE_RETRIEVAL_QUERY == "CODE_RETRIEVAL_QUERY"


def test_persona_capabilities():
    assert PersonaCapability.GSD == "gsd"
    assert len(PersonaCapability) == 3


def test_json_serializable():
    assert json.dumps(SessionState.ACTIVE) == '"active"'
    assert json.dumps(GraphTemplate.REACT) == '"react"'
