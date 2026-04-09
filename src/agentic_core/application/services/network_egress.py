"""Network egress policy -- deny-by-default outbound access control."""
from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class EgressDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    PENDING_APPROVAL = "pending_approval"


@dataclass
class EgressRule:
    pattern: str  # Domain or URL pattern (glob)
    decision: EgressDecision
    reason: str = ""


@dataclass
class EgressRequest:
    url: str
    agent_id: str
    tool_name: str


class NetworkEgressPolicy:
    """Deny-by-default network egress control for agent processes.

    Agents cannot make arbitrary outbound requests. Each destination
    must be explicitly allowed or go through operator approval.
    """

    def __init__(self) -> None:
        self._rules: list[EgressRule] = []
        self._pending: list[EgressRequest] = []
        self._audit: list[dict] = []
        self._default_allowlist()

    def _default_allowlist(self) -> None:
        """Allow common safe destinations."""
        self._rules.extend(
            [
                EgressRule(
                    "https://api.openai.com/*",
                    EgressDecision.ALLOW,
                    "OpenAI API",
                ),
                EgressRule(
                    "https://api.anthropic.com/*",
                    EgressDecision.ALLOW,
                    "Anthropic API",
                ),
                EgressRule(
                    "https://openrouter.ai/*",
                    EgressDecision.ALLOW,
                    "OpenRouter",
                ),
                EgressRule(
                    "https://api.fireworks.ai/*",
                    EgressDecision.ALLOW,
                    "Fireworks AI",
                ),
                EgressRule(
                    "http://localhost:*",
                    EgressDecision.ALLOW,
                    "Local services",
                ),
                EgressRule(
                    "http://127.0.0.1:*",
                    EgressDecision.ALLOW,
                    "Local services",
                ),
            ]
        )

    def add_rule(
        self,
        pattern: str,
        decision: EgressDecision,
        reason: str = "",
    ) -> None:
        self._rules.insert(0, EgressRule(pattern, decision, reason))

    def evaluate(self, request: EgressRequest) -> EgressDecision:
        """Evaluate an outbound request against policy."""
        for rule in self._rules:
            if fnmatch.fnmatch(request.url, rule.pattern):
                self._log_audit(request, rule.decision, rule.reason)
                return rule.decision

        # Default deny
        self._log_audit(
            request,
            EgressDecision.DENY,
            "No matching rule (deny-by-default)",
        )
        self._pending.append(request)
        logger.warning(
            "Egress denied (no rule): %s from agent %s via %s",
            request.url,
            request.agent_id,
            request.tool_name,
        )
        return EgressDecision.DENY

    def approve_pending(self, url_pattern: str) -> int:
        """Operator approves a pending URL pattern."""
        self.add_rule(url_pattern, EgressDecision.ALLOW, "Operator approved")
        count = 0
        remaining: list[EgressRequest] = []
        for req in self._pending:
            if fnmatch.fnmatch(req.url, url_pattern):
                count += 1
            else:
                remaining.append(req)
        self._pending = remaining
        return count

    def get_pending(self) -> list[EgressRequest]:
        return list(self._pending)

    def _log_audit(
        self,
        request: EgressRequest,
        decision: EgressDecision,
        reason: str,
    ) -> None:
        import time

        self._audit.append(
            {
                "timestamp": time.time(),
                "url": request.url,
                "agent": request.agent_id,
                "tool": request.tool_name,
                "decision": decision.value,
                "reason": reason,
            }
        )

    @property
    def audit_log(self) -> list[dict]:
        return self._audit

    @property
    def rule_count(self) -> int:
        return len(self._rules)
