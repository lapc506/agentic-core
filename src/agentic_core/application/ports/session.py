from abc import ABC, abstractmethod

from agentic_core.domain.entities.session import Session


class SessionPort(ABC):
    @abstractmethod
    async def create(self, session: Session) -> None: ...

    @abstractmethod
    async def get(self, session_id: str) -> Session | None: ...

    @abstractmethod
    async def update(self, session: Session) -> None: ...

    @abstractmethod
    async def store_checkpoint(self, session_id: str, checkpoint_data: bytes) -> str: ...

    @abstractmethod
    async def load_checkpoint(self, checkpoint_id: str) -> bytes: ...
