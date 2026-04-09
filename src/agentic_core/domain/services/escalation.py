from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from simpleeval import simple_eval

if TYPE_CHECKING:
    from agentic_core.domain.entities.persona import EscalationRule

logger = logging.getLogger(__name__)


class EscalationService:
    """Evaluates escalation rules using simpleeval (safe restricted expression evaluator).
    simpleeval disallows imports, attribute access, and arbitrary function calls.
    This is NOT Python's built-in eval — it is a sandboxed expression evaluator."""

    def evaluate(
        self, rules: list[EscalationRule], context: dict[str, object]
    ) -> EscalationRule | None:
        for rule in rules:
            try:
                if simple_eval(rule.condition, names=context):
                    return rule
            except Exception:
                logger.warning("Failed to evaluate rule: %s", rule.condition)
                continue
        return None
