"""EU AI Act compliance layer — opt-in long-term audit storage and risk classification."""
from __future__ import annotations
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    MINIMAL = "minimal"
    LIMITED = "limited"
    HIGH = "high"
    UNACCEPTABLE = "unacceptable"


@dataclass
class ComplianceConfig:
    enabled: bool = False
    retention_days: int = 180
    storage_backend: str = "file"  # file, postgresql, null
    storage_path: str = "logs/compliance"
    risk_level: str = "high"
    data_lineage: bool = False
    fria_enabled: bool = False


@dataclass
class ComplianceEvent:
    event_type: str
    timestamp: float = field(default_factory=time.time)
    agent_id: str = ""
    user_id: str = ""
    session_id: str = ""
    risk_level: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    data_lineage: dict[str, Any] | None = None


class ComplianceStore(ABC):
    @abstractmethod
    def record(self, event: ComplianceEvent) -> None: ...
    @abstractmethod
    def query(self, since: float = 0, until: float = 0, event_type: str = "", limit: int = 1000) -> list[dict]: ...
    @abstractmethod
    def check_retention(self) -> dict[str, Any]: ...


class NullComplianceStore(ComplianceStore):
    def record(self, event: ComplianceEvent) -> None:
        pass
    def query(self, **kwargs) -> list[dict]:
        return []
    def check_retention(self) -> dict[str, Any]:
        return {"status": "disabled"}


class FileComplianceStore(ComplianceStore):
    def __init__(self, path: str, retention_days: int = 180) -> None:
        self._dir = Path(path)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._retention = retention_days
        self._current_file = None
        self._current_date = ""

    def record(self, event: ComplianceEvent) -> None:
        date = time.strftime("%Y-%m-%d")
        if date != self._current_date:
            if self._current_file:
                self._current_file.close()
            path = self._dir / f"compliance-{date}.jsonl"
            self._current_file = open(path, "a")
            self._current_date = date
        line = json.dumps({
            "type": event.event_type, "ts": event.timestamp,
            "agent": event.agent_id, "user": event.user_id,
            "session": event.session_id, "risk": event.risk_level,
            "details": event.details, "lineage": event.data_lineage,
        })
        self._current_file.write(line + "\n")
        self._current_file.flush()

    def query(self, since: float = 0, until: float = 0, event_type: str = "", limit: int = 1000) -> list[dict]:
        results: list[dict] = []
        for path in sorted(self._dir.glob("compliance-*.jsonl")):
            with open(path) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if since and entry.get("ts", 0) < since:
                            continue
                        if until and entry.get("ts", 0) > until:
                            continue
                        if event_type and entry.get("type") != event_type:
                            continue
                        results.append(entry)
                        if len(results) >= limit:
                            return results
                    except json.JSONDecodeError:
                        continue
        return results

    def check_retention(self) -> dict[str, Any]:
        files = sorted(self._dir.glob("compliance-*.jsonl"))
        if not files:
            return {"status": "no_data", "files": 0, "retention_days": self._retention}
        oldest = files[0].name.replace("compliance-", "").replace(".jsonl", "")
        return {"status": "ok", "files": len(files), "oldest": oldest, "retention_days": self._retention}


class RiskClassifier:
    def classify_agent(self, tools: list[str], has_network: bool = False, has_file_access: bool = False) -> RiskLevel:
        if has_file_access and has_network:
            return RiskLevel.HIGH
        if has_file_access or has_network:
            return RiskLevel.LIMITED
        if tools:
            return RiskLevel.LIMITED
        return RiskLevel.MINIMAL


class ComplianceService:
    def __init__(self, config: ComplianceConfig | None = None) -> None:
        self._config = config or ComplianceConfig()
        self._store: ComplianceStore
        if not self._config.enabled:
            self._store = NullComplianceStore()
        elif self._config.storage_backend == "file":
            self._store = FileComplianceStore(self._config.storage_path, self._config.retention_days)
        else:
            self._store = NullComplianceStore()
        self._classifier = RiskClassifier()

    def record(self, event: ComplianceEvent) -> None:
        self._store.record(event)

    def record_tool_call(self, agent_id: str, user_id: str, tool_name: str, session_id: str = "") -> None:
        self.record(ComplianceEvent(
            event_type="tool_call", agent_id=agent_id, user_id=user_id,
            session_id=session_id, details={"tool": tool_name},
        ))

    def query(self, **kwargs) -> list[dict]:
        return self._store.query(**kwargs)

    def check_retention(self) -> dict[str, Any]:
        return self._store.check_retention()

    def classify_agent(self, tools: list[str], **kwargs) -> RiskLevel:
        return self._classifier.classify_agent(tools, **kwargs)

    @property
    def enabled(self) -> bool:
        return self._config.enabled
