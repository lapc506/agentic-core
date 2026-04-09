from __future__ import annotations

from datetime import datetime

from agentic_core.adapters.primary.gateway import (
    GatewayAdapter,
    GatewayConfig,
    GatewayPlatform,
    GatewayRegistry,
    InboundMessage,
    OutboundMessage,
)

# --- Config / message construction ---


def test_gateway_config_defaults() -> None:
    cfg = GatewayConfig(platform=GatewayPlatform.TELEGRAM)
    assert cfg.token is None
    assert cfg.webhook_url is None
    assert cfg.enabled is True


def test_gateway_config_with_values() -> None:
    cfg = GatewayConfig(
        platform=GatewayPlatform.SLACK,
        token="xoxb-123",
        webhook_url="https://hooks.slack.com/x",
        enabled=False,
    )
    assert cfg.platform == GatewayPlatform.SLACK
    assert cfg.token == "xoxb-123"
    assert cfg.webhook_url == "https://hooks.slack.com/x"
    assert cfg.enabled is False


def test_inbound_message_frozen() -> None:
    msg = InboundMessage(
        platform=GatewayPlatform.DISCORD,
        channel_id="ch-1",
        user_id="u-1",
        content="hello",
    )
    assert msg.platform == GatewayPlatform.DISCORD
    assert msg.media_url is None
    assert isinstance(msg.timestamp, datetime)


def test_outbound_message_frozen() -> None:
    msg = OutboundMessage(
        platform=GatewayPlatform.WHATSAPP,
        channel_id="ch-2",
        content="reply",
    )
    assert msg.reply_to is None
    assert msg.content == "reply"


def test_inbound_message_with_media() -> None:
    msg = InboundMessage(
        platform=GatewayPlatform.TELEGRAM,
        channel_id="ch-3",
        user_id="u-2",
        content="photo",
        media_url="https://cdn.example.com/photo.jpg",
    )
    assert msg.media_url == "https://cdn.example.com/photo.jpg"


# --- GatewayAdapter lifecycle ---


async def test_start_stop_lifecycle() -> None:
    adapter = GatewayAdapter(
        configs=[GatewayConfig(platform=GatewayPlatform.TELEGRAM)],
    )
    assert not adapter.is_running
    await adapter.start()
    assert adapter.is_running
    await adapter.stop()
    assert not adapter.is_running


# --- Active platforms ---


def test_active_platforms_filters_disabled() -> None:
    adapter = GatewayAdapter(
        configs=[
            GatewayConfig(platform=GatewayPlatform.TELEGRAM, enabled=True),
            GatewayConfig(platform=GatewayPlatform.DISCORD, enabled=False),
            GatewayConfig(platform=GatewayPlatform.SLACK, enabled=True),
        ],
    )
    active = adapter.active_platforms()
    assert GatewayPlatform.TELEGRAM in active
    assert GatewayPlatform.SLACK in active
    assert GatewayPlatform.DISCORD not in active


def test_active_platforms_empty() -> None:
    adapter = GatewayAdapter(configs=[])
    assert adapter.active_platforms() == []


# --- Handle inbound ---


async def test_handle_inbound_with_callback() -> None:
    received: list[InboundMessage] = []

    async def cb(msg: InboundMessage) -> OutboundMessage | None:
        received.append(msg)
        return OutboundMessage(
            platform=msg.platform,
            channel_id=msg.channel_id,
            content=f"echo: {msg.content}",
        )

    adapter = GatewayAdapter(
        configs=[GatewayConfig(platform=GatewayPlatform.TELEGRAM)],
        callback=cb,
    )
    inbound = InboundMessage(
        platform=GatewayPlatform.TELEGRAM,
        channel_id="ch-1",
        user_id="u-1",
        content="ping",
    )
    result = await adapter.handle_inbound(inbound)
    assert result is not None
    assert result.content == "echo: ping"
    assert len(received) == 1


async def test_handle_inbound_without_callback() -> None:
    adapter = GatewayAdapter(
        configs=[GatewayConfig(platform=GatewayPlatform.TELEGRAM)],
    )
    inbound = InboundMessage(
        platform=GatewayPlatform.TELEGRAM,
        channel_id="ch-1",
        user_id="u-1",
        content="ping",
    )
    result = await adapter.handle_inbound(inbound)
    assert result is None


async def test_handle_inbound_disabled_platform() -> None:
    async def cb(msg: InboundMessage) -> OutboundMessage | None:
        return OutboundMessage(
            platform=msg.platform, channel_id=msg.channel_id, content="ok",
        )

    adapter = GatewayAdapter(
        configs=[GatewayConfig(platform=GatewayPlatform.DISCORD, enabled=False)],
        callback=cb,
    )
    inbound = InboundMessage(
        platform=GatewayPlatform.DISCORD,
        channel_id="ch-1",
        user_id="u-1",
        content="hi",
    )
    result = await adapter.handle_inbound(inbound)
    assert result is None


async def test_handle_inbound_callback_error() -> None:
    async def bad_cb(msg: InboundMessage) -> OutboundMessage | None:
        raise RuntimeError("boom")

    adapter = GatewayAdapter(
        configs=[GatewayConfig(platform=GatewayPlatform.SLACK)],
        callback=bad_cb,
    )
    inbound = InboundMessage(
        platform=GatewayPlatform.SLACK,
        channel_id="ch-1",
        user_id="u-1",
        content="test",
    )
    result = await adapter.handle_inbound(inbound)
    assert result is None


# --- Send placeholder ---


async def test_send_enabled_platform() -> None:
    adapter = GatewayAdapter(
        configs=[GatewayConfig(platform=GatewayPlatform.WHATSAPP)],
    )
    msg = OutboundMessage(
        platform=GatewayPlatform.WHATSAPP,
        channel_id="ch-1",
        content="hello",
    )
    assert await adapter.send(msg) is True


async def test_send_disabled_platform() -> None:
    adapter = GatewayAdapter(
        configs=[GatewayConfig(platform=GatewayPlatform.WHATSAPP, enabled=False)],
    )
    msg = OutboundMessage(
        platform=GatewayPlatform.WHATSAPP,
        channel_id="ch-1",
        content="hello",
    )
    assert await adapter.send(msg) is False


async def test_send_unconfigured_platform() -> None:
    adapter = GatewayAdapter(configs=[])
    msg = OutboundMessage(
        platform=GatewayPlatform.SIGNAL,
        channel_id="ch-1",
        content="hello",
    )
    assert await adapter.send(msg) is False


# --- GatewayRegistry ---


def test_registry_register_and_get() -> None:
    registry = GatewayRegistry()
    adapter = GatewayAdapter(configs=[])
    registry.register(GatewayPlatform.TELEGRAM, adapter)
    assert registry.get(GatewayPlatform.TELEGRAM) is adapter


def test_registry_get_missing() -> None:
    registry = GatewayRegistry()
    assert registry.get(GatewayPlatform.DISCORD) is None


def test_registry_list_all() -> None:
    registry = GatewayRegistry()
    a1 = GatewayAdapter(configs=[])
    a2 = GatewayAdapter(configs=[])
    registry.register(GatewayPlatform.SLACK, a1)
    registry.register(GatewayPlatform.SIGNAL, a2)
    all_adapters = registry.list_all()
    assert len(all_adapters) == 2
    assert GatewayPlatform.SLACK in all_adapters
    assert GatewayPlatform.SIGNAL in all_adapters


def test_registry_singleton() -> None:
    GatewayRegistry.reset()
    r1 = GatewayRegistry.get_instance()
    r2 = GatewayRegistry.get_instance()
    assert r1 is r2
    GatewayRegistry.reset()


# --- Multiple platforms ---


async def test_multiple_platforms_adapter() -> None:
    configs = [
        GatewayConfig(platform=GatewayPlatform.TELEGRAM, token="tg-tok"),
        GatewayConfig(platform=GatewayPlatform.DISCORD, token="dc-tok"),
        GatewayConfig(platform=GatewayPlatform.SLACK, token="sl-tok"),
        GatewayConfig(platform=GatewayPlatform.WHATSAPP, enabled=False),
    ]
    adapter = GatewayAdapter(configs=configs)
    await adapter.start()

    assert len(adapter.active_platforms()) == 3
    assert GatewayPlatform.WHATSAPP not in adapter.active_platforms()

    await adapter.stop()
    assert not adapter.is_running
