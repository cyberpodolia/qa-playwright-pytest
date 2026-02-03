from __future__ import annotations

from pathlib import Path
from prometheus_client import CollectorRegistry, Gauge, generate_latest

REGISTRY = CollectorRegistry()
TESTS_TOTAL = Gauge("tests_total", "Total tests", registry=REGISTRY)
TESTS_FAILED = Gauge("tests_failed", "Failed tests", registry=REGISTRY)
TEST_DURATION = Gauge("test_duration_seconds", "Test duration in seconds", registry=REGISTRY)


def write_metrics(path: str, total: int, failed: int, duration: float) -> None:
    TESTS_TOTAL.set(total)
    TESTS_FAILED.set(failed)
    TEST_DURATION.set(duration)
    Path(path).write_bytes(generate_latest(REGISTRY))
