from agentic_core.domain.entities.persona import EscalationRule
from agentic_core.domain.services.escalation import EscalationService


def test_billing_amount_match():
    rules = [EscalationRule(condition="billing_amount > 500", target="billing-agent")]
    svc = EscalationService()
    result = svc.evaluate(rules, context={"billing_amount": 600})
    assert result is not None
    assert result.target == "billing-agent"


def test_billing_amount_no_match():
    rules = [EscalationRule(condition="billing_amount > 500", target="billing-agent")]
    svc = EscalationService()
    result = svc.evaluate(rules, context={"billing_amount": 100})
    assert result is None


def test_sentiment_match():
    rules = [EscalationRule(condition="sentiment < -0.7", target="human", priority="urgent")]
    svc = EscalationService()
    result = svc.evaluate(rules, context={"sentiment": -0.9})
    assert result is not None
    assert result.target == "human"
    assert result.priority == "urgent"


def test_first_matching_rule_wins():
    rules = [
        EscalationRule(condition="x > 10", target="first"),
        EscalationRule(condition="x > 5", target="second"),
    ]
    svc = EscalationService()
    result = svc.evaluate(rules, context={"x": 15})
    assert result is not None
    assert result.target == "first"


def test_invalid_expression_skipped():
    rules = [
        EscalationRule(condition="invalid!!!", target="bad"),
        EscalationRule(condition="x > 0", target="good"),
    ]
    svc = EscalationService()
    result = svc.evaluate(rules, context={"x": 1})
    assert result is not None
    assert result.target == "good"


def test_empty_rules():
    svc = EscalationService()
    assert svc.evaluate([], context={"x": 1}) is None
