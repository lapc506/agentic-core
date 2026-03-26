from __future__ import annotations

import asyncio
import uuid

import pytest

from agentic_core.application.services.agent_comms import (
    AgentCommsBus,
    AgentMailbox,
    AgentMessage,
)


# ---------------------------------------------------------------------------
# AgentMessage construction & immutability
# ---------------------------------------------------------------------------


class TestAgentMessage:
    def test_defaults(self) -> None:
        msg = AgentMessage(from_agent="a", to_agent="b", content="hi")
        assert msg.from_agent == "a"
        assert msg.to_agent == "b"
        assert msg.content == "hi"
        # Auto-generated fields
        uuid.UUID(msg.correlation_id)  # valid uuid
        assert msg.timestamp is not None

    def test_frozen(self) -> None:
        msg = AgentMessage(from_agent="a", to_agent="b", content="hi")
        with pytest.raises(Exception):
            msg.content = "changed"  # type: ignore[misc]

    def test_explicit_correlation_id(self) -> None:
        cid = str(uuid.uuid4())
        msg = AgentMessage(
            from_agent="a", to_agent="b", content="x", correlation_id=cid,
        )
        assert msg.correlation_id == cid


# ---------------------------------------------------------------------------
# AgentMailbox
# ---------------------------------------------------------------------------


class TestAgentMailbox:
    async def test_put_and_get(self) -> None:
        mbox = AgentMailbox()
        msg = AgentMessage(from_agent="a", to_agent="b", content="hello")
        await mbox.put(msg)
        assert mbox.pending == 1
        got = await mbox.get(timeout=1.0)
        assert got is not None
        assert got.content == "hello"
        assert mbox.pending == 0

    async def test_timeout_returns_none(self) -> None:
        mbox = AgentMailbox()
        result = await mbox.get(timeout=0.05)
        assert result is None


# ---------------------------------------------------------------------------
# AgentCommsBus — registration & discovery
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_and_discover(self) -> None:
        bus = AgentCommsBus()
        bus.register("alpha")
        bus.register("beta")
        assert bus.discover() == ["alpha", "beta"]

    def test_register_duplicate_raises(self) -> None:
        bus = AgentCommsBus()
        bus.register("alpha")
        with pytest.raises(ValueError, match="already registered"):
            bus.register("alpha")

    def test_unregister(self) -> None:
        bus = AgentCommsBus()
        bus.register("alpha")
        bus.unregister("alpha")
        assert bus.discover() == []

    def test_unregister_unknown_raises(self) -> None:
        bus = AgentCommsBus()
        with pytest.raises(KeyError, match="not registered"):
            bus.unregister("ghost")


# ---------------------------------------------------------------------------
# AgentCommsBus — send / receive
# ---------------------------------------------------------------------------


class TestSendReceive:
    async def test_send_and_receive(self) -> None:
        bus = AgentCommsBus()
        bus.register("sender")
        bus.register("receiver")

        msg = AgentMessage(from_agent="sender", to_agent="receiver", content="ping")
        await bus.send(msg)

        got = await bus.receive("receiver", timeout=1.0)
        assert got is not None
        assert got.content == "ping"
        assert got.from_agent == "sender"

    async def test_send_to_unregistered_raises(self) -> None:
        bus = AgentCommsBus()
        bus.register("sender")
        msg = AgentMessage(from_agent="sender", to_agent="ghost", content="x")
        with pytest.raises(KeyError, match="Target agent not registered"):
            await bus.send(msg)

    async def test_receive_unregistered_raises(self) -> None:
        bus = AgentCommsBus()
        with pytest.raises(KeyError, match="Agent not registered"):
            await bus.receive("ghost")

    async def test_receive_timeout_empty(self) -> None:
        bus = AgentCommsBus()
        bus.register("lonely")
        result = await bus.receive("lonely", timeout=0.05)
        assert result is None

    async def test_fifo_ordering(self) -> None:
        bus = AgentCommsBus()
        bus.register("a")
        bus.register("b")

        for i in range(3):
            await bus.send(
                AgentMessage(from_agent="a", to_agent="b", content=f"msg-{i}"),
            )

        for i in range(3):
            got = await bus.receive("b", timeout=1.0)
            assert got is not None
            assert got.content == f"msg-{i}"


# ---------------------------------------------------------------------------
# AgentCommsBus — broadcast
# ---------------------------------------------------------------------------


class TestBroadcast:
    async def test_broadcast_to_others(self) -> None:
        bus = AgentCommsBus()
        bus.register("announcer")
        bus.register("listener1")
        bus.register("listener2")

        count = await bus.broadcast("announcer", "news")
        assert count == 2

        for name in ("listener1", "listener2"):
            got = await bus.receive(name, timeout=1.0)
            assert got is not None
            assert got.content == "news"
            assert got.from_agent == "announcer"

    async def test_broadcast_excludes_sender(self) -> None:
        bus = AgentCommsBus()
        bus.register("solo")

        count = await bus.broadcast("solo", "echo")
        assert count == 0
        result = await bus.receive("solo", timeout=0.05)
        assert result is None


# ---------------------------------------------------------------------------
# Correlation-ID tracking across a request-reply pair
# ---------------------------------------------------------------------------


class TestCorrelationTracking:
    async def test_reply_preserves_correlation_id(self) -> None:
        bus = AgentCommsBus()
        bus.register("client")
        bus.register("server")

        request = AgentMessage(
            from_agent="client", to_agent="server", content="request",
        )
        await bus.send(request)

        incoming = await bus.receive("server", timeout=1.0)
        assert incoming is not None

        reply = AgentMessage(
            from_agent="server",
            to_agent="client",
            content="response",
            correlation_id=incoming.correlation_id,
        )
        await bus.send(reply)

        got = await bus.receive("client", timeout=1.0)
        assert got is not None
        assert got.correlation_id == request.correlation_id
        assert got.content == "response"


# ---------------------------------------------------------------------------
# Multiple agents communicating concurrently
# ---------------------------------------------------------------------------


class TestMultiAgentCommunication:
    async def test_three_agents_exchange_messages(self) -> None:
        bus = AgentCommsBus()
        for name in ("alice", "bob", "carol"):
            bus.register(name)

        await bus.send(AgentMessage(from_agent="alice", to_agent="bob", content="a->b"))
        await bus.send(AgentMessage(from_agent="bob", to_agent="carol", content="b->c"))
        await bus.send(AgentMessage(from_agent="carol", to_agent="alice", content="c->a"))

        m1 = await bus.receive("bob", timeout=1.0)
        m2 = await bus.receive("carol", timeout=1.0)
        m3 = await bus.receive("alice", timeout=1.0)

        assert m1 is not None and m1.content == "a->b"
        assert m2 is not None and m2.content == "b->c"
        assert m3 is not None and m3.content == "c->a"
