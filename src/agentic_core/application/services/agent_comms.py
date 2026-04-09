from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentMessage(BaseModel, frozen=True):
    """Immutable message exchanged between agents."""

    from_agent: str
    to_agent: str
    content: str
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


class AgentMailbox:
    """Per-agent async inbox backed by an :class:`asyncio.Queue`."""

    def __init__(self) -> None:
        self._inbox: asyncio.Queue[AgentMessage] = asyncio.Queue()

    async def put(self, msg: AgentMessage) -> None:
        await self._inbox.put(msg)

    async def get(self, timeout: float | None = None) -> AgentMessage | None:
        """Return the next message, or ``None`` if *timeout* expires."""
        try:
            return await asyncio.wait_for(self._inbox.get(), timeout=timeout)
        except TimeoutError:
            return None

    @property
    def pending(self) -> int:
        return self._inbox.qsize()


class AgentCommsBus:
    """Central message bus that routes :class:`AgentMessage` objects
    between registered agents via per-agent mailboxes."""

    def __init__(self) -> None:
        self._mailboxes: dict[str, AgentMailbox] = {}

    # -- registration -------------------------------------------------------

    def register(self, agent_name: str) -> None:
        """Register an agent for messaging.

        Raises :class:`ValueError` if the name is already registered.
        """
        if agent_name in self._mailboxes:
            raise ValueError(f"Agent already registered: {agent_name}")
        self._mailboxes[agent_name] = AgentMailbox()
        logger.info("Agent registered: %s", agent_name)

    def unregister(self, agent_name: str) -> None:
        """Remove an agent from the bus.

        Raises :class:`KeyError` if the agent is not registered.
        """
        if agent_name not in self._mailboxes:
            raise KeyError(f"Agent not registered: {agent_name}")
        del self._mailboxes[agent_name]
        logger.info("Agent unregistered: %s", agent_name)

    # -- discovery ----------------------------------------------------------

    def discover(self) -> list[str]:
        """Return a sorted list of currently registered agent names."""
        return sorted(self._mailboxes)

    # -- messaging ----------------------------------------------------------

    async def send(self, msg: AgentMessage) -> None:
        """Route *msg* to the target agent's mailbox.

        Raises :class:`KeyError` if the target agent is not registered.
        """
        mailbox = self._mailboxes.get(msg.to_agent)
        if mailbox is None:
            raise KeyError(f"Target agent not registered: {msg.to_agent}")
        await mailbox.put(msg)

    async def receive(
        self,
        agent_name: str,
        timeout: float | None = None,
    ) -> AgentMessage | None:
        """Get the next message for *agent_name*.

        Returns ``None`` if *timeout* expires before a message arrives.

        Raises :class:`KeyError` if the agent is not registered.
        """
        mailbox = self._mailboxes.get(agent_name)
        if mailbox is None:
            raise KeyError(f"Agent not registered: {agent_name}")
        return await mailbox.get(timeout=timeout)

    async def broadcast(self, from_agent: str, content: str) -> int:
        """Send a message to every registered agent *except* the sender.

        Returns the number of agents the message was delivered to.
        """
        targets = [
            name for name in self._mailboxes if name != from_agent
        ]
        for name in targets:
            msg = AgentMessage(
                from_agent=from_agent,
                to_agent=name,
                content=content,
            )
            await self._mailboxes[name].put(msg)
        return len(targets)
