"""Policy engine — TOML-based fine-grained tool access control."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


class Priority(IntEnum):
    DEFAULT = 1
    EXTENSION = 2
    WORKSPACE = 3
    USER = 4
    ADMIN = 5


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"


@dataclass
class PolicyRule:
    tool_pattern: str  # glob pattern for tool name
    args_pattern: str = ""  # regex for serialized args
    decision: Decision = Decision.ASK_USER
    priority: Priority = Priority.DEFAULT
    modes: list[str] = field(default_factory=list)  # empty = all modes
    reason: str = ""


class PolicyEngine:
    def __init__(self) -> None:
        self._rules: list[PolicyRule] = []

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(
        self, tool_name: str, args: dict[str, Any], mode: str = "default"
    ) -> tuple[Decision, str]:
        import json

        args_str = json.dumps(args, sort_keys=True)
        for rule in self._rules:
            if not fnmatch.fnmatch(tool_name, rule.tool_pattern):
                continue
            if rule.modes and mode not in rule.modes:
                continue
            if rule.args_pattern:
                if not re.search(rule.args_pattern, args_str):
                    continue
            return rule.decision, rule.reason
        return Decision.ALLOW, "No matching policy rule"

    def load_rules(self, rules_data: list[dict]) -> None:
        for r in rules_data:
            self._rules.append(
                PolicyRule(
                    tool_pattern=r.get("tool", "*"),
                    args_pattern=r.get("args_pattern", ""),
                    decision=Decision(r.get("decision", "allow")),
                    priority=Priority(r.get("priority", 1)),
                    modes=r.get("modes", []),
                    reason=r.get("reason", ""),
                )
            )
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    @property
    def rule_count(self) -> int:
        return len(self._rules)
