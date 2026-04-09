"""Tool-level result caching with TTL and deduplication."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    result: Any
    created_at: float
    ttl_seconds: float
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        return time.monotonic() - self.created_at > self.ttl_seconds


@dataclass
class CacheConfig:
    ttl_seconds: float = 300.0
    max_entries: int = 1000
    key_fn: str | None = None  # Custom key function name


class ToolCache:
    """In-memory cache for tool execution results."""

    def __init__(self, max_entries: int = 1000) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._tool_configs: dict[str, CacheConfig] = {}
        self._max = max_entries
        self._hits = 0
        self._misses = 0

    def configure_tool(self, tool_name: str, config: CacheConfig) -> None:
        self._tool_configs[tool_name] = config

    def get(self, tool_name: str, args: dict[str, Any]) -> Any | None:
        key = self._make_key(tool_name, args)
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired:
            del self._cache[key]
            self._misses += 1
            return None
        entry.hit_count += 1
        self._hits += 1
        return entry.result

    def put(self, tool_name: str, args: dict[str, Any], result: Any) -> None:
        config = self._tool_configs.get(tool_name, CacheConfig())
        if len(self._cache) >= self._max:
            self._evict()
        key = self._make_key(tool_name, args)
        self._cache[key] = CacheEntry(
            result=result, created_at=time.monotonic(), ttl_seconds=config.ttl_seconds,
        )

    def invalidate(self, tool_name: str, args: dict[str, Any] | None = None) -> int:
        if args:
            key = self._make_key(tool_name, args)
            if key in self._cache:
                del self._cache[key]
                return 1
            return 0
        prefix = f"{tool_name}:"
        keys = [k for k in self._cache if k.startswith(prefix)]
        for k in keys:
            del self._cache[k]
        return len(keys)

    def _make_key(self, tool_name: str, args: dict[str, Any]) -> str:
        args_json = json.dumps(args, sort_keys=True, default=str)
        args_hash = hashlib.sha256(args_json.encode()).hexdigest()[:16]
        return f"{tool_name}:{args_hash}"

    def _evict(self) -> None:
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for k in expired:
            del self._cache[k]
        if len(self._cache) >= self._max:
            oldest = min(self._cache, key=lambda k: self._cache[k].created_at)
            del self._cache[oldest]

    @property
    def stats(self) -> dict[str, int]:
        return {"size": len(self._cache), "hits": self._hits, "misses": self._misses,
                "hit_rate": round(self._hits / max(self._hits + self._misses, 1), 3)}
