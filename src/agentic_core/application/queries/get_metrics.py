from __future__ import annotations


class GetMetricsQuery:
    __slots__ = ("metric_type", "window")

    def __init__(self, metric_type: str, window: str = "1h") -> None:
        self.metric_type = metric_type
        self.window = window


class GetMetricsHandler:
    def __init__(self, metrics_store: dict | None = None) -> None:
        self._store: dict = metrics_store if metrics_store is not None else {}

    async def execute(self, query: GetMetricsQuery) -> dict:
        return {
            "metric_type": query.metric_type,
            "window": query.window,
            "data": self._store.get(query.metric_type),
        }
