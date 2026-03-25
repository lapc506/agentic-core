from __future__ import annotations

import json
import logging
from typing import Any

from agentic_core.application.ports.alert import AlertPort

logger = logging.getLogger(__name__)


class AlertManagerAdapter(AlertPort):
    """Pushes alerts to Prometheus Alertmanager via HTTP API.
    Gracefully degrades to logging when httpx is not installed or URL not configured."""

    def __init__(self, alertmanager_url: str | None = None) -> None:
        self._url = alertmanager_url
        self._client: Any = None

    async def initialize(self) -> None:
        if self._url is None:
            logger.info("AlertManager URL not configured, alerts will be logged only")
            return
        try:
            import httpx
            self._client = httpx.AsyncClient(timeout=10.0)
            logger.info("AlertManager adapter initialized: %s", self._url)
        except ImportError:
            logger.info("httpx not installed, alerts will be logged only")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def fire(self, severity: str, summary: str, details: dict[str, Any]) -> None:
        alert_payload = [{
            "labels": {
                "alertname": details.get("alert_name", "AgenticCoreAlert"),
                "severity": severity,
                "persona_id": details.get("persona_id", "unknown"),
                "service": "agentic-core",
            },
            "annotations": {
                "summary": summary,
                "description": details.get("description", ""),
                "runbook_url": details.get("runbook_url", ""),
            },
        }]

        if self._client is not None and self._url is not None:
            try:
                resp = await self._client.post(
                    f"{self._url}/api/v2/alerts",
                    json=alert_payload,
                )
                resp.raise_for_status()
                logger.info("Alert fired: %s (severity=%s)", summary, severity)
            except Exception:
                logger.exception("Failed to fire alert to AlertManager")
        else:
            logger.warning(
                "ALERT [%s]: %s — %s", severity, summary, json.dumps(details)
            )
