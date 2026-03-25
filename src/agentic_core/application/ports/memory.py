from abc import ABC, abstractmethod

from agentic_core.domain.value_objects.messages import AgentMessage


class MemoryPort(ABC):
    @abstractmethod
    async def store_message(self, message: AgentMessage) -> None: ...

    @abstractmethod
    async def get_messages(self, session_id: str, limit: int = 50) -> list[AgentMessage]: ...

    @abstractmethod
    async def get_context_window(self, session_id: str, max_tokens: int) -> list[AgentMessage]: ...
