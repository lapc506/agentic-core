import pytest
from datetime import datetime, timezone

import uuid_utils

from agentic_core.domain.value_objects.messages import AgentMessage


def _make_msg(**overrides: object) -> AgentMessage:
    defaults: dict = {
        "id": str(uuid_utils.uuid7()),
        "session_id": "sess_1",
        "persona_id": "support",
        "role": "user",
        "content": "hello",
        "metadata": {"key": "val"},
        "timestamp": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return AgentMessage(**defaults)


def test_valid_message():
    msg = _make_msg()
    assert msg.role == "user"
    assert msg.content == "hello"
    assert isinstance(msg.metadata, dict)


def test_metadata_field_reassignment_blocked():
    msg = _make_msg(metadata={"a": 1})
    with pytest.raises(Exception):
        msg.metadata = {"b": 2}  # type: ignore[misc]


def test_invalid_uuid_rejected():
    with pytest.raises(ValueError):
        _make_msg(id="not-a-uuid-v7")


def test_uuid_v4_rejected():
    import uuid

    with pytest.raises(ValueError, match="Expected UUID v7"):
        _make_msg(id=str(uuid.uuid4()))


def test_invalid_role_rejected():
    with pytest.raises(Exception):
        _make_msg(role="invalid_role")


def test_frozen_immutability():
    msg = _make_msg()
    with pytest.raises(Exception):
        msg.content = "changed"  # type: ignore[misc]


def test_trace_id_optional():
    msg = _make_msg()
    assert msg.trace_id is None

    msg_with_trace = _make_msg(trace_id="abc123")
    assert msg_with_trace.trace_id == "abc123"


def test_all_valid_roles():
    for role in ("user", "assistant", "system", "tool", "human_escalation"):
        msg = _make_msg(role=role)
        assert msg.role == role
