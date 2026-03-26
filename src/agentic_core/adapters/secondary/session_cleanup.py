"""Session cleanup: TTL enforcement + expired session purge (#48)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from agentic_core.domain.enums import SessionState

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TTL_HOURS = 24
DEFAULT_CHECKPOINT_TTL_DAYS = 7


class SessionCleanupService:
    """Prevents unbounded disk/memory growth by purging expired sessions and checkpoints."""

    def __init__(
        self,
        pool: Any,
        session_ttl_hours: int = DEFAULT_SESSION_TTL_HOURS,
        checkpoint_ttl_days: int = DEFAULT_CHECKPOINT_TTL_DAYS,
    ) -> None:
        self._pool = pool
        self._session_ttl = timedelta(hours=session_ttl_hours)
        self._checkpoint_ttl = timedelta(days=checkpoint_ttl_days)

    async def cleanup_expired_sessions(self) -> int:
        cutoff = datetime.now(timezone.utc) - self._session_ttl
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE agent_sessions SET state = $1, updated_at = NOW()
                   WHERE state IN ($2, $3) AND updated_at < $4""",
                SessionState.COMPLETED.value,
                SessionState.PAUSED.value,
                SessionState.ACTIVE.value,
                cutoff,
            )
            count = int(result.split()[-1]) if result else 0
            if count > 0:
                logger.info("Cleaned up %d expired sessions (TTL=%s)", count, self._session_ttl)
            return count

    async def cleanup_orphan_checkpoints(self) -> int:
        cutoff = datetime.now(timezone.utc) - self._checkpoint_ttl
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """DELETE FROM agent_checkpoints
                   WHERE created_at < $1
                   AND session_id IN (
                       SELECT id FROM agent_sessions WHERE state = $2
                   )""",
                cutoff,
                SessionState.COMPLETED.value,
            )
            count = int(result.split()[-1]) if result else 0
            if count > 0:
                logger.info("Cleaned up %d orphan checkpoints (TTL=%s)", count, self._checkpoint_ttl)
            return count

    async def run_full_cleanup(self) -> dict[str, int]:
        sessions = await self.cleanup_expired_sessions()
        checkpoints = await self.cleanup_orphan_checkpoints()
        return {"sessions_cleaned": sessions, "checkpoints_cleaned": checkpoints}
