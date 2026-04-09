from __future__ import annotations

from agentic_core.domain.value_objects.eval import BinaryEvalRule, EvalResult


class EvalScoring:
    def evaluate(
        self, rules: list[BinaryEvalRule], actuals: list[bool]
    ) -> list[EvalResult]:
        if len(rules) != len(actuals):
            raise ValueError("rules and actuals must have the same length")
        results: list[EvalResult] = []
        for rule, actual in zip(rules, actuals, strict=False):
            results.append(
                EvalResult(
                    rule_name=rule.name,
                    passed=actual == rule.expected,
                    actual=actual,
                )
            )
        return results

    def score(self, results: list[EvalResult]) -> float:
        if not results:
            return 0.0
        passed = sum(1 for r in results if r.passed)
        return passed / len(results)
