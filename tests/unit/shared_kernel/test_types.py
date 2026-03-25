from agentic_core.shared_kernel.types import SessionId, PersonaId, TraceId


def test_session_id_is_str():
    sid = SessionId("sess_123")
    assert isinstance(sid, str)
    assert sid == "sess_123"


def test_persona_id_is_str():
    pid = PersonaId("support-agent")
    assert isinstance(pid, str)


def test_trace_id_is_str():
    tid = TraceId("abc123def456")
    assert isinstance(tid, str)
