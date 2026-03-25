import pytest

from agentic_core.domain.entities.session import InvalidTransitionError, Session
from agentic_core.domain.enums import SessionState


def test_create_active():
    s = Session.create("s1", "support", "u1")
    assert s.state == SessionState.ACTIVE
    assert s.checkpoint_id is None


def test_active_to_paused():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.PAUSED)
    assert s.state == SessionState.PAUSED


def test_active_to_escalated():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.ESCALATED)
    assert s.state == SessionState.ESCALATED


def test_active_to_completed():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.COMPLETED)
    assert s.state == SessionState.COMPLETED


def test_paused_to_active():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.PAUSED)
    s.transition_to(SessionState.ACTIVE)
    assert s.state == SessionState.ACTIVE


def test_paused_to_completed():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.PAUSED)
    s.transition_to(SessionState.COMPLETED)
    assert s.state == SessionState.COMPLETED


def test_escalated_to_active():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.ESCALATED)
    s.transition_to(SessionState.ACTIVE)
    assert s.state == SessionState.ACTIVE


def test_completed_is_terminal():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        s.transition_to(SessionState.ACTIVE)


def test_paused_to_escalated_invalid():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.PAUSED)
    with pytest.raises(InvalidTransitionError):
        s.transition_to(SessionState.ESCALATED)


def test_escalated_to_paused_invalid():
    s = Session.create("s1", "support", "u1")
    s.transition_to(SessionState.ESCALATED)
    with pytest.raises(InvalidTransitionError):
        s.transition_to(SessionState.PAUSED)


def test_updated_at_changes_on_transition():
    s = Session.create("s1", "support", "u1")
    original = s.updated_at
    s.transition_to(SessionState.PAUSED)
    assert s.updated_at >= original
