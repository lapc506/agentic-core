from __future__ import annotations

import pytest

from agentic_core.application.services.persona_router import PersonaRouter, RoutingRule

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def router() -> PersonaRouter:
    return PersonaRouter()


# ---------------------------------------------------------------------------
# 1. Explicit persona override
# ---------------------------------------------------------------------------


def test_explicit_persona_overrides_all(router: PersonaRouter) -> None:
    router.add_channel_rule("#support", "support-agent")
    router.add_keyword_rule("billing", "billing-agent")
    router.set_default("default-agent")

    result = router.route(
        channel="#support",
        content="billing issue",
        explicit_persona="vip-agent",
    )
    assert result == "vip-agent"


def test_explicit_persona_returned_without_any_rules(router: PersonaRouter) -> None:
    result = router.route(explicit_persona="custom-agent")
    assert result == "custom-agent"


# ---------------------------------------------------------------------------
# 2. Channel-based routing – exact match
# ---------------------------------------------------------------------------


def test_channel_exact_match_routes_correctly(router: PersonaRouter) -> None:
    router.add_channel_rule("#support", "support-agent")
    router.add_channel_rule("#sales", "sales-agent")

    assert router.route(channel="#support") == "support-agent"
    assert router.route(channel="#sales") == "sales-agent"


def test_channel_exact_match_is_case_insensitive(router: PersonaRouter) -> None:
    router.add_channel_rule("#Support", "support-agent")

    assert router.route(channel="#SUPPORT") == "support-agent"
    assert router.route(channel="#support") == "support-agent"


def test_unknown_channel_falls_through_to_default(router: PersonaRouter) -> None:
    router.add_channel_rule("#support", "support-agent")
    router.set_default("fallback-agent")

    assert router.route(channel="#unknown") == "fallback-agent"


# ---------------------------------------------------------------------------
# 3. Channel-based routing – glob pattern
# ---------------------------------------------------------------------------


def test_channel_glob_prefix_pattern(router: PersonaRouter) -> None:
    router.add_channel_rule("#sales-*", "sales-agent")

    assert router.route(channel="#sales-emea") == "sales-agent"
    assert router.route(channel="#sales-apac") == "sales-agent"


def test_channel_glob_does_not_match_unrelated_channel(router: PersonaRouter) -> None:
    router.add_channel_rule("#sales-*", "sales-agent")
    router.set_default("default-agent")

    assert router.route(channel="#support") == "default-agent"


def test_channel_glob_wildcard_matches_any(router: PersonaRouter) -> None:
    router.add_channel_rule("*", "catch-all-agent")

    assert router.route(channel="#anything") == "catch-all-agent"
    assert router.route(channel="general") == "catch-all-agent"


# ---------------------------------------------------------------------------
# 4. Keyword-based fallback
# ---------------------------------------------------------------------------


def test_keyword_match_routes_when_no_channel_rule(router: PersonaRouter) -> None:
    router.add_keyword_rule("billing", "billing-agent")

    assert router.route(content="I have a billing question") == "billing-agent"


def test_keyword_match_is_case_insensitive(router: PersonaRouter) -> None:
    router.add_keyword_rule("invoice", "billing-agent")

    assert router.route(content="Please send my INVOICE") == "billing-agent"


def test_keyword_channel_miss_falls_to_keyword(router: PersonaRouter) -> None:
    router.add_channel_rule("#support", "support-agent")
    router.add_keyword_rule("refund", "billing-agent")
    router.set_default("default-agent")

    # Channel does not match → keyword should fire
    result = router.route(channel="#general", content="I need a refund")
    assert result == "billing-agent"


def test_keyword_not_present_falls_to_default(router: PersonaRouter) -> None:
    router.add_keyword_rule("billing", "billing-agent")
    router.set_default("default-agent")

    assert router.route(content="just a regular message") == "default-agent"


# ---------------------------------------------------------------------------
# 5. Default persona
# ---------------------------------------------------------------------------


def test_default_persona_when_nothing_matches(router: PersonaRouter) -> None:
    router.set_default("my-default-agent")
    assert router.route() == "my-default-agent"


def test_default_persona_initial_value(router: PersonaRouter) -> None:
    # Without calling set_default the built-in fallback is "default"
    assert router.route() == "default"


# ---------------------------------------------------------------------------
# 6. Priority ordering for channel rules
# ---------------------------------------------------------------------------


def test_higher_priority_rule_wins_over_lower(router: PersonaRouter) -> None:
    # Both patterns match "#support", but the higher-priority one should win.
    router.add_channel_rule("#support", "generic-agent", priority=0)
    router.add_channel_rule("#support", "specialist-agent", priority=10)

    assert router.route(channel="#support") == "specialist-agent"


def test_lower_priority_rule_used_when_higher_does_not_match(router: PersonaRouter) -> None:
    router.add_channel_rule("#vip-*", "vip-agent", priority=10)
    router.add_channel_rule("#*", "general-agent", priority=1)

    assert router.route(channel="#vip-gold") == "vip-agent"
    assert router.route(channel="#support") == "general-agent"


def test_rules_remain_sorted_after_multiple_additions(router: PersonaRouter) -> None:
    router.add_channel_rule("#a", "a-agent", priority=5)
    router.add_channel_rule("#b", "b-agent", priority=20)
    router.add_channel_rule("#c", "c-agent", priority=1)

    priorities = [r.priority for r in router._channel_rules]
    assert priorities == sorted(priorities, reverse=True)


def test_same_priority_preserves_insertion_order_for_first_match(router: PersonaRouter) -> None:
    # When priorities are equal the first-registered matching rule should win
    # because list.sort() is stable.
    router.add_channel_rule("#support", "first-agent", priority=0)
    router.add_channel_rule("#support", "second-agent", priority=0)

    assert router.route(channel="#support") == "first-agent"


# ---------------------------------------------------------------------------
# 7. RoutingRule dataclass
# ---------------------------------------------------------------------------


def test_routing_rule_default_priority() -> None:
    rule = RoutingRule(channel_pattern="#support", persona_id="support-agent")
    assert rule.priority == 0


def test_routing_rule_stores_values() -> None:
    rule = RoutingRule(channel_pattern="#sales-*", persona_id="sales-agent", priority=5)
    assert rule.channel_pattern == "#sales-*"
    assert rule.persona_id == "sales-agent"
    assert rule.priority == 5
