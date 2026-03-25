from __future__ import annotations

from agentic_core.adapters.secondary.otel_adapter import NoOpSpan, OTelAdapter
from agentic_core.adapters.secondary.structlog_adapter import StructlogAdapter
from agentic_core.config.settings import ObservabilitySettings


def test_otel_noop_mode():
    settings = ObservabilitySettings(otel_endpoint=None)
    adapter = OTelAdapter(settings)
    # Don't call initialize() — stays in no-op mode
    span = adapter.start_span("test", {"key": "val"})
    assert isinstance(span, NoOpSpan)
    adapter.end_span(span)  # Should not raise


def test_otel_increment_counter_noop():
    settings = ObservabilitySettings()
    adapter = OTelAdapter(settings)
    # No-op: counter doesn't exist, should not raise
    adapter.increment_counter("agent_requests_total", {"persona_id": "test"})


def test_otel_observe_histogram_noop():
    settings = ObservabilitySettings()
    adapter = OTelAdapter(settings)
    adapter.observe_histogram("agent_request_duration_seconds", {"persona_id": "test"}, 1.5)


def test_structlog_adapter():
    adapter = StructlogAdapter()
    adapter.bind_context(trace_id="t123", session_id="s1")
    # Should not raise
    adapter.log("info", "test_event", extra_field="value")
    adapter.log("WARNING", "another_event")
