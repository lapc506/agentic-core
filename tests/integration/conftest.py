"""Integration test fixtures. Requires docker-compose.test.yaml running."""
from __future__ import annotations

import os

import pytest

REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6399")
POSTGRES_DSN = os.getenv("TEST_POSTGRES_DSN", "postgresql://agentic:agentic@localhost:5499/agentic_test")
FALKORDB_URL = os.getenv("TEST_FALKORDB_URL", "redis://localhost:6499")

# Mark all integration tests so they can be skipped without infra
integration = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION", "0") != "1",
    reason="Set RUN_INTEGRATION=1 and run docker-compose.test.yaml",
)
