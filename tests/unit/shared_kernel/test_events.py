from datetime import UTC, datetime

from agentic_core.shared_kernel.events import DomainEvent, EventBus


class FakeEvent(DomainEvent):
    data: str


async def test_publish_calls_handler():
    bus = EventBus()
    received: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        received.append(event)

    bus.subscribe(FakeEvent, handler)
    evt = FakeEvent(data="hello", timestamp=datetime.now(UTC))
    await bus.publish(evt)
    assert len(received) == 1
    assert received[0].data == "hello"  # type: ignore[attr-defined]


async def test_multiple_subscribers():
    bus = EventBus()
    calls: list[str] = []

    async def h1(event: DomainEvent) -> None:
        calls.append("h1")

    async def h2(event: DomainEvent) -> None:
        calls.append("h2")

    bus.subscribe(FakeEvent, h1)
    bus.subscribe(FakeEvent, h2)
    await bus.publish(FakeEvent(data="x", timestamp=datetime.now(UTC)))
    assert calls == ["h1", "h2"]


async def test_error_does_not_block_next_handler():
    bus = EventBus()
    calls: list[str] = []

    async def bad(event: DomainEvent) -> None:
        raise RuntimeError("boom")

    async def good(event: DomainEvent) -> None:
        calls.append("ok")

    bus.subscribe(FakeEvent, bad)
    bus.subscribe(FakeEvent, good)
    await bus.publish(FakeEvent(data="x", timestamp=datetime.now(UTC)))
    assert calls == ["ok"]


async def test_no_subscribers():
    bus = EventBus()
    await bus.publish(FakeEvent(data="lonely", timestamp=datetime.now(UTC)))


async def test_unrelated_event_not_dispatched():
    class OtherEvent(DomainEvent):
        value: int

    bus = EventBus()
    received: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        received.append(event)

    bus.subscribe(FakeEvent, handler)
    await bus.publish(OtherEvent(value=42, timestamp=datetime.now(UTC)))
    assert len(received) == 0
