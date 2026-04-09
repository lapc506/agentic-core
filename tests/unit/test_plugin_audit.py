"""Tests for plugin integrity verification and security audit trail."""
from __future__ import annotations

import json
import time
from pathlib import Path

from agentic_core.application.services.plugin_integrity import (
    IntegrityResult,
    PluginIntegrityVerifier,
)
from agentic_core.application.middleware.audit_trail import (
    AuditEvent,
    AuditEventType,
    AuditTrail,
)


# ── Plugin Integrity Tests ──────────────────────────────────────────


def _make_plugin_dir(tmp_path: Path, name: str, files: dict[str, str] | None = None) -> Path:
    """Helper: create a fake plugin directory with optional files."""
    plugin_dir = tmp_path / "plugins" / name
    plugin_dir.mkdir(parents=True)
    if files:
        for fname, content in files.items():
            (plugin_dir / fname).write_text(content)
    return plugin_dir


def test_compute_hash_deterministic(tmp_path: Path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, "alpha", {
        "manifest.json": '{"name": "alpha"}',
        "main.py": "print('hello')",
    })
    verifier = PluginIntegrityVerifier(plugins_dir=str(tmp_path / "plugins"))
    h1 = verifier.compute_hash(plugin_dir)
    h2 = verifier.compute_hash(plugin_dir)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_compute_hash_changes_on_modification(tmp_path: Path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, "beta", {
        "manifest.json": '{"name": "beta"}',
        "main.py": "x = 1",
    })
    verifier = PluginIntegrityVerifier(plugins_dir=str(tmp_path / "plugins"))
    h1 = verifier.compute_hash(plugin_dir)
    # Tamper with a file
    (plugin_dir / "main.py").write_text("x = 2")
    h2 = verifier.compute_hash(plugin_dir)
    assert h1 != h2


def test_verify_first_time_registration(tmp_path: Path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, "gamma", {
        "manifest.json": '{"name": "gamma"}',
        "core.py": "pass",
    })
    verifier = PluginIntegrityVerifier(plugins_dir=str(tmp_path / "plugins"))
    result = verifier.verify("gamma", plugin_dir)
    assert result.valid is True
    assert "first-time registration" in result.warnings[0]
    assert result.expected_hash == result.actual_hash


def test_verify_match_after_registration(tmp_path: Path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, "delta", {
        "manifest.json": '{"name": "delta"}',
        "run.py": "run()",
    })
    verifier = PluginIntegrityVerifier(plugins_dir=str(tmp_path / "plugins"))
    verifier.register("delta", plugin_dir)
    result = verifier.verify("delta", plugin_dir)
    assert result.valid is True
    assert len(result.warnings) == 0


def test_verify_detects_tampering(tmp_path: Path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, "epsilon", {
        "manifest.json": '{"name": "epsilon"}',
        "app.py": "safe_code()",
    })
    verifier = PluginIntegrityVerifier(plugins_dir=str(tmp_path / "plugins"))
    verifier.register("epsilon", plugin_dir)
    # Tamper
    (plugin_dir / "app.py").write_text("malicious_code()")
    result = verifier.verify("epsilon", plugin_dir)
    assert result.valid is False
    assert "hash mismatch" in result.warnings[0]
    assert result.expected_hash != result.actual_hash


def test_lockfile_persistence(tmp_path: Path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, "zeta", {
        "manifest.json": '{"name": "zeta"}',
        "lib.py": "import os",
    })
    plugins_root = str(tmp_path / "plugins")
    v1 = PluginIntegrityVerifier(plugins_dir=plugins_root)
    v1.register("zeta", plugin_dir)
    # New verifier instance reads from disk
    v2 = PluginIntegrityVerifier(plugins_dir=plugins_root)
    assert v2.known_count == 1
    result = v2.verify("zeta", plugin_dir)
    assert result.valid is True


def test_lockfile_json_structure(tmp_path: Path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, "eta", {
        "manifest.json": '{"name": "eta"}',
    })
    plugins_root = str(tmp_path / "plugins")
    verifier = PluginIntegrityVerifier(plugins_dir=plugins_root)
    verifier.register("eta", plugin_dir)
    lockfile = Path(plugins_root) / "plugin-lock.json"
    data = json.loads(lockfile.read_text())
    assert data["version"] == 1
    assert "eta" in data["plugins"]
    assert len(data["plugins"]["eta"]) == 64


# ── Audit Trail Tests ───────────────────────────────────────────────


def test_audit_log_event(tmp_path: Path) -> None:
    trail = AuditTrail(log_dir=str(tmp_path / "audit"))
    trail.log(AuditEvent(
        event_type=AuditEventType.TOOL_CALL,
        user_id="u1",
        session_id="s1",
        tool_name="shell",
    ))
    assert trail.event_count == 1
    trail.close()


def test_audit_query_by_type(tmp_path: Path) -> None:
    trail = AuditTrail(log_dir=str(tmp_path / "audit"))
    trail.log(AuditEvent(event_type=AuditEventType.TOOL_CALL, user_id="u1"))
    trail.log(AuditEvent(event_type=AuditEventType.AUTH_FAILURE, user_id="u2"))
    trail.log(AuditEvent(event_type=AuditEventType.TOOL_CALL, user_id="u3"))
    results = trail.query(event_type=AuditEventType.TOOL_CALL)
    assert len(results) == 2
    trail.close()


def test_audit_query_by_user(tmp_path: Path) -> None:
    trail = AuditTrail(log_dir=str(tmp_path / "audit"))
    trail.log(AuditEvent(event_type=AuditEventType.TOOL_CALL, user_id="alice"))
    trail.log(AuditEvent(event_type=AuditEventType.TOOL_CALL, user_id="bob"))
    trail.log(AuditEvent(event_type=AuditEventType.AUTH_FAILURE, user_id="alice"))
    results = trail.query(user_id="alice")
    assert len(results) == 2
    assert all(e.user_id == "alice" for e in results)
    trail.close()


def test_audit_critical_count(tmp_path: Path) -> None:
    trail = AuditTrail(log_dir=str(tmp_path / "audit"))
    trail.log(AuditEvent(event_type=AuditEventType.INJECTION_DETECTED, severity="critical"))
    trail.log(AuditEvent(event_type=AuditEventType.TOOL_CALL, severity="info"))
    trail.log(AuditEvent(event_type=AuditEventType.SANDBOX_VIOLATION, severity="critical"))
    assert trail.critical_count == 2
    assert trail.event_count == 3
    trail.close()


def test_audit_jsonl_file_output(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    trail = AuditTrail(log_dir=str(audit_dir))
    trail.log(AuditEvent(
        event_type=AuditEventType.PLUGIN_LOADED,
        user_id="admin",
        tool_name="my-plugin",
        details={"version": "1.0"},
    ))
    trail.close()
    # Find the JSONL file
    jsonl_files = list(audit_dir.glob("audit-*.jsonl"))
    assert len(jsonl_files) == 1
    lines = jsonl_files[0].read_text().strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["type"] == "plugin_loaded"
    assert record["user"] == "admin"
    assert record["tool"] == "my-plugin"
    assert record["details"]["version"] == "1.0"


def test_audit_log_tool_call_helper(tmp_path: Path) -> None:
    trail = AuditTrail(log_dir=str(tmp_path / "audit"))
    trail.log_tool_call(user_id="u1", session_id="s1", tool_name="exec", args_hash="abc123")
    events = trail.query(event_type=AuditEventType.TOOL_CALL)
    assert len(events) == 1
    assert events[0].details["args_hash"] == "abc123"
    trail.close()


def test_audit_log_injection_critical(tmp_path: Path) -> None:
    trail = AuditTrail(log_dir=str(tmp_path / "audit"))
    trail.log_injection(user_id="attacker", session_id="s9", score=0.85, patterns=["ignore previous"])
    assert trail.critical_count == 1
    events = trail.query(event_type=AuditEventType.INJECTION_DETECTED)
    assert len(events) == 1
    assert events[0].severity == "critical"
    assert events[0].details["score"] == 0.85
    trail.close()


def test_audit_log_injection_warning(tmp_path: Path) -> None:
    trail = AuditTrail(log_dir=str(tmp_path / "audit"))
    trail.log_injection(user_id="u1", session_id="s1", score=0.3, patterns=["suspicious"])
    assert trail.critical_count == 0
    events = trail.query(event_type=AuditEventType.INJECTION_DETECTED)
    assert events[0].severity == "warning"
    trail.close()


def test_audit_log_auth_failure(tmp_path: Path) -> None:
    trail = AuditTrail(log_dir=str(tmp_path / "audit"))
    trail.log_auth_failure(reason="invalid_token", ip="192.168.1.1")
    events = trail.query(event_type=AuditEventType.AUTH_FAILURE)
    assert len(events) == 1
    assert events[0].details["reason"] == "invalid_token"
    assert events[0].details["ip"] == "192.168.1.1"
    assert events[0].severity == "warning"
    trail.close()
