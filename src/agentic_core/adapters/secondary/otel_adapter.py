from __future__ import annotations

import logging
from typing import Any

from agentic_core.application.ports.metrics import MetricsPort
from agentic_core.application.ports.tracing import TracingPort
from agentic_core.config.settings import ObservabilitySettings

logger = logging.getLogger(__name__)


class NoOpSpan:
    """Span placeholder when OTel SDK is not installed."""

    def __init__(self, name: str) -> None:
        self.name = name


class OTelAdapter(TracingPort, MetricsPort):
    """OpenTelemetry adapter for distributed tracing + Prometheus metrics.

    Gracefully degrades to no-op when OTel SDK is not installed (optional dep)."""

    def __init__(self, settings: ObservabilitySettings) -> None:
        self._settings = settings
        self._tracer: Any = None
        self._meter: Any = None
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}
        self._initialized = False

    def initialize(self) -> None:
        try:
            from opentelemetry import trace, metrics
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.metrics import MeterProvider

            resource = Resource.create({
                "service.name": "agentic-core",
            })

            tracer_provider = TracerProvider(resource=resource)
            if self._settings.otel_endpoint:
                exporter = OTLPSpanExporter(endpoint=self._settings.otel_endpoint)
                tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

            trace.set_tracer_provider(tracer_provider)
            self._tracer = trace.get_tracer("agentic_core")

            meter_provider = MeterProvider(resource=resource)
            metrics.set_meter_provider(meter_provider)
            self._meter = metrics.get_meter("agentic_core")

            self._register_metrics()
            self._initialized = True
            logger.info("OTel initialized: endpoint=%s", self._settings.otel_endpoint)

        except ImportError:
            logger.info("OTel SDK not installed, using no-op mode")
            self._initialized = False

    def _register_metrics(self) -> None:
        if self._meter is None:
            return

        self._counters["agent_requests_total"] = self._meter.create_counter(
            "agent_requests_total", description="Total agent requests",
        )
        self._counters["agent_errors_total"] = self._meter.create_counter(
            "agent_errors_total", description="Total agent errors",
        )
        self._counters["agent_tokens_total"] = self._meter.create_counter(
            "agent_tokens_total", description="Total LLM tokens consumed",
        )
        self._counters["agent_memory_operations_total"] = self._meter.create_counter(
            "agent_memory_operations_total", description="Memory store operations",
        )
        self._counters["agent_hitl_escalations_total"] = self._meter.create_counter(
            "agent_hitl_escalations_total", description="Human escalation count",
        )
        self._histograms["agent_request_duration_seconds"] = self._meter.create_histogram(
            "agent_request_duration_seconds", description="Agent request latency", unit="s",
        )
        self._histograms["agent_tool_execution_seconds"] = self._meter.create_histogram(
            "agent_tool_execution_seconds", description="Tool execution latency", unit="s",
        )

    # -- TracingPort --

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        if self._tracer is not None:
            return self._tracer.start_span(name, attributes=attributes or {})
        return NoOpSpan(name)

    def end_span(self, span: Any) -> None:
        if hasattr(span, "end"):
            span.end()

    # -- MetricsPort --

    def increment_counter(self, name: str, labels: dict[str, str], value: float = 1) -> None:
        counter = self._counters.get(name)
        if counter is not None:
            counter.add(value, attributes=labels)

    def observe_histogram(self, name: str, labels: dict[str, str], value: float) -> None:
        histogram = self._histograms.get(name)
        if histogram is not None:
            histogram.record(value, attributes=labels)
