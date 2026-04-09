"""Security audit trail — logs all security-relevant events."""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    TOOL_CALL = "tool_call"
    TOOL_DENIED = "tool_denied"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    INJECTION_DETECTED = "injection_detected"
    POLICY_VIOLATION = "policy_violation"
    EGRESS_DENIED = "egress_denied"
    EGRESS_ALLOWED = "egress_allowed"
    SANDBOX_VIOLATION = "sandbox_violation"
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_INTEGRITY_FAIL = "plugin_integrity_fail"
    SESSION_CREATED = "session_created"
    SESSION_CLOSED = "session_closed"
    HITL_REQUESTED = "hitl_requested"
    HITL_APPROVED = "hitl_approved"
    HITL_DENIED = "hitl_denied"
    SECRET_ACCESS = "secret_access"
    PII_REDACTED = "pii_redacted"
    OUTPUT_FILTERED = "output_filtered"


@dataclass
class AuditEvent:
    event_type: AuditEventType
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    session_id: str = ""
    agent_id: str = ""
    tool_name: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    severity: str = "info"  # info, warning, critical
    trace_id: str = ""


class AuditTrail:
    """Persistent security audit trail for compliance and forensics."""

    def __init__(self, log_dir: str = "logs/audit", max_memory_events: int = 10000) -> None:
        self._dir = Path(log_dir)
        self._memory: list[AuditEvent] = []
        self._max = max_memory_events
        self._file = None
        self._init_file()

    def _init_file(self) -> None:
        """Initialize audit log file."""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            date = time.strftime("%Y-%m-%d")
            path = self._dir / f"audit-{date}.jsonl"
            self._file = open(path, "a")
        except Exception:
            logger.warning("Failed to open audit log file — using memory only")

    def log(self, event: AuditEvent) -> None:
        """Record an audit event."""
        # Memory
        self._memory.append(event)
        if len(self._memory) > self._max:
            self._memory = self._memory[-self._max:]

        # File (JSONL)
        if self._file:
            try:
                line = json.dumps({
                    "type": event.event_type.value,
                    "ts": event.timestamp,
                    "user": event.user_id,
                    "session": event.session_id,
                    "agent": event.agent_id,
                    "tool": event.tool_name,
                    "severity": event.severity,
                    "trace": event.trace_id,
                    "details": event.details,
                })
                self._file.write(line + "\n")
                self._file.flush()
            except Exception:
                pass

        # Log critical events to stderr
        if event.severity == "critical":
            logger.critical("AUDIT [%s] user=%s tool=%s: %s",
                          event.event_type.value, event.user_id, event.tool_name,
                          json.dumps(event.details))

    def log_tool_call(self, user_id: str, session_id: str, tool_name: str, args_hash: str = "", trace_id: str = "") -> None:
        self.log(AuditEvent(
            event_type=AuditEventType.TOOL_CALL,
            user_id=user_id, session_id=session_id, tool_name=tool_name,
            details={"args_hash": args_hash}, trace_id=trace_id,
        ))

    def log_injection(self, user_id: str, session_id: str, score: float, patterns: list[str]) -> None:
        self.log(AuditEvent(
            event_type=AuditEventType.INJECTION_DETECTED,
            user_id=user_id, session_id=session_id,
            details={"score": score, "patterns": patterns},
            severity="critical" if score > 0.6 else "warning",
        ))

    def log_auth_failure(self, reason: str, ip: str = "") -> None:
        self.log(AuditEvent(
            event_type=AuditEventType.AUTH_FAILURE,
            details={"reason": reason, "ip": ip},
            severity="warning",
        ))

    def query(self, event_type: AuditEventType | None = None, user_id: str = "",
              since: float = 0, limit: int = 100) -> list[AuditEvent]:
        """Query audit events from memory."""
        results = self._memory
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results[-limit:]

    def close(self) -> None:
        if self._file:
            self._file.close()

    @property
    def event_count(self) -> int:
        return len(self._memory)

    @property
    def critical_count(self) -> int:
        return sum(1 for e in self._memory if e.severity == "critical")
