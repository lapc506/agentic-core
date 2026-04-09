"""Security auditor — proactive scan for misconfigurations (agentic-core doctor)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

@dataclass
class AuditFinding:
    check: str
    severity: Severity
    message: str
    recommendation: str

class SecurityAuditor:
    def audit(self, config: dict) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        self._check_auth(config, findings)
        self._check_network(config, findings)
        self._check_rate_limits(config, findings)
        self._check_pii(config, findings)
        self._check_secrets(config, findings)
        self._check_websocket_origins(config, findings)
        return findings

    def _check_auth(self, config: dict, findings: list[AuditFinding]) -> None:
        if config.get("mode") == "standalone" and not config.get("auth_enabled"):
            findings.append(AuditFinding("auth", Severity.WARNING, "Authentication disabled in standalone mode", "Enable auth for production demos"))

    def _check_network(self, config: dict, findings: list[AuditFinding]) -> None:
        host = config.get("ws_host", "0.0.0.0")
        if host == "0.0.0.0" and config.get("mode") != "sidecar":
            findings.append(AuditFinding("network", Severity.INFO, "Binding to all interfaces (0.0.0.0)", "Use 127.0.0.1 for local-only access"))

    def _check_rate_limits(self, config: dict, findings: list[AuditFinding]) -> None:
        rpm = config.get("rate_limit_rpm", 0)
        if rpm == 0 or rpm > 1000:
            findings.append(AuditFinding("rate_limit", Severity.WARNING, f"Rate limit is {rpm} RPM (too high or disabled)", "Set rate_limit_rpm to 60 or lower"))

    def _check_pii(self, config: dict, findings: list[AuditFinding]) -> None:
        if not config.get("pii_redaction_enabled", True):
            findings.append(AuditFinding("pii", Severity.CRITICAL, "PII redaction is disabled", "Enable pii_redaction_enabled for compliance"))

    def _check_secrets(self, config: dict, findings: list[AuditFinding]) -> None:
        for key in ["postgres_dsn", "redis_url"]:
            val = config.get(key, "")
            if "password" in val.lower() and "@" in val:
                findings.append(AuditFinding("secrets", Severity.INFO, f"Credentials in {key} connection string", "Use environment variables for secrets"))

    def _check_websocket_origins(self, config: dict, findings: list[AuditFinding]) -> None:
        if not config.get("allowed_origins"):
            findings.append(AuditFinding(
                "websocket_origins", Severity.WARNING,
                "No custom allowed origins configured for WebSocket",
                "Set AGENTIC_ALLOWED_ORIGINS for production deployments",
            ))
