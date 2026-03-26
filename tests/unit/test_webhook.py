from __future__ import annotations

import hashlib
import hmac

from agentic_core.adapters.primary.webhook import (
    WebhookResult,
    WebhookRoute,
    WebhookRouter,
    render_template,
    verify_signature,
)


# --- verify_signature ---


def test_verify_valid_sha256():
    secret = "my_secret"
    payload = b'{"action":"push"}'
    sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_signature(payload, sig, secret) is True


def test_verify_invalid_signature():
    assert verify_signature(b"data", "sha256=bad", "secret") is False


def test_verify_no_prefix():
    secret = "s"
    payload = b"data"
    raw_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_signature(payload, raw_sig, secret) is True


# --- render_template ---


def test_render_basic():
    t = "Push to {payload[repo]}: {payload[msg]}"
    result = render_template(t, {"repo": "core", "msg": "fix bug"})
    assert result == "Push to core: fix bug"


def test_render_nested():
    t = "Repo: {payload[repository][name]}"
    result = render_template(t, {"repository": {"name": "agentic-core"}})
    assert result == "Repo: agentic-core"


def test_render_missing_key_fallback():
    t = "Value: {payload[missing]}"
    result = render_template(t, {"other": 1})
    assert result == t  # returns template unchanged


# --- WebhookRouter basics ---


def test_empty_router():
    r = WebhookRouter()
    assert r.list_routes() == []


def test_add_remove_route():
    r = WebhookRouter()
    route = WebhookRoute(name="gh", persona_id="p", template="t")
    r.add_route(route)
    assert len(r.list_routes()) == 1
    assert r.get_route("gh") is route
    r.remove_route("gh")
    assert r.list_routes() == []


# --- handle() ---


async def test_handle_unknown_route():
    r = WebhookRouter()
    result = await r.handle("nope", {})
    assert not result.accepted
    assert result.error is not None
    assert "Unknown" in result.error


async def test_handle_disabled_route():
    r = WebhookRouter()
    r.add_route(WebhookRoute(
        name="gh", persona_id="p", template="t", enabled=False,
    ))
    result = await r.handle("gh", {})
    assert not result.accepted
    assert result.error == "Route is disabled"


async def test_handle_ip_not_allowed():
    r = WebhookRouter()
    r.add_route(WebhookRoute(
        name="gh", persona_id="p", template="t",
        allowed_sources=["10.0.0.1"],
    ))
    result = await r.handle("gh", {}, source_ip="192.168.1.1")
    assert not result.accepted
    assert result.error == "Source IP not allowed"


async def test_handle_ip_allowed():
    fired: list[str] = []

    async def cb(persona_id: str, message: str, route_name: str) -> None:
        fired.append(route_name)

    r = WebhookRouter(callback=cb)
    r.add_route(WebhookRoute(
        name="gh", persona_id="p", template="event",
        allowed_sources=["10.0.0.1"],
    ))
    result = await r.handle("gh", {}, source_ip="10.0.0.1")
    assert result.accepted
    assert fired == ["gh"]


async def test_handle_invalid_signature():
    r = WebhookRouter()
    r.add_route(WebhookRoute(
        name="stripe", persona_id="billing", template="t",
        secret="whsec_123",
    ))
    result = await r.handle(
        "stripe", {},
        payload_bytes=b"data", signature="sha256=wrong",
    )
    assert not result.accepted
    assert result.error == "Invalid signature"


async def test_handle_valid_signature():
    secret = "whsec_123"
    payload_bytes = b'{"type":"payment_intent.succeeded"}'
    sig = "sha256=" + hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256,
    ).hexdigest()

    fired: list[str] = []

    async def cb(persona_id: str, message: str, route_name: str) -> None:
        fired.append(route_name)

    r = WebhookRouter(callback=cb)
    r.add_route(WebhookRoute(
        name="stripe", persona_id="billing", template="Payment received",
        secret=secret,
    ))
    result = await r.handle(
        "stripe", {}, payload_bytes=payload_bytes, signature=sig,
    )
    assert result.accepted
    assert result.message == "Payment received"


async def test_handle_renders_template():
    r = WebhookRouter()
    r.add_route(WebhookRoute(
        name="gh", persona_id="devops",
        template="Push to {payload[repo]}: {payload[msg]}",
    ))
    result = await r.handle("gh", {"repo": "core", "msg": "fix"})
    assert result.accepted
    assert result.message == "Push to core: fix"


async def test_handle_callback_invoked():
    calls: list[tuple[str, str, str]] = []

    async def cb(persona_id: str, message: str, route_name: str) -> None:
        calls.append((persona_id, message, route_name))

    r = WebhookRouter(callback=cb)
    r.add_route(WebhookRoute(
        name="gh", persona_id="devops", template="event: {payload[action]}",
    ))
    await r.handle("gh", {"action": "push"})
    assert calls == [("devops", "event: push", "gh")]


async def test_handle_callback_error():
    async def bad_cb(persona_id: str, message: str, route_name: str) -> None:
        raise RuntimeError("oops")

    r = WebhookRouter(callback=bad_cb)
    r.add_route(WebhookRoute(name="gh", persona_id="p", template="t"))
    result = await r.handle("gh", {})
    assert not result.accepted
    assert result.error == "Callback failed"


async def test_handle_no_callback_still_accepts():
    r = WebhookRouter()
    r.add_route(WebhookRoute(name="gh", persona_id="p", template="t"))
    result = await r.handle("gh", {})
    assert result.accepted


# --- WebhookRoute defaults ---


def test_route_defaults():
    route = WebhookRoute(name="test", persona_id="p", template="t")
    assert route.secret is None
    assert route.enabled is True
    assert route.allowed_sources == []
