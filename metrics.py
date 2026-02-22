"""Prometheus textfile metrics export for pytest session summaries.

The writer intentionally builds a fresh registry per write to avoid leaking
global metric state across repeated local runs in the same Python process.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from prometheus_client import CollectorRegistry, Gauge, generate_latest


@dataclass(frozen=True)
class SessionMetrics:
    """Aggregate session counters exported at pytest session finish."""

    total: int
    passed: int
    failed: int
    skipped: int
    duration_seconds: float
    flaky: int = 0


def write_metrics(path: str, summary: SessionMetrics) -> None:
    """Write metrics atomically to the Prometheus textfile collector path."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    registry = CollectorRegistry()
    gauges = {
        "qa_tests_total": Gauge("qa_tests_total", "Total tests collected", registry=registry),
        "qa_tests_passed": Gauge("qa_tests_passed", "Passed tests", registry=registry),
        "qa_tests_failed": Gauge("qa_tests_failed", "Failed tests", registry=registry),
        "qa_tests_skipped": Gauge("qa_tests_skipped", "Skipped tests", registry=registry),
        "qa_tests_flaky": Gauge("qa_tests_flaky", "Tests that required reruns", registry=registry),
        "qa_test_session_duration_seconds": Gauge(
            "qa_test_session_duration_seconds",
            "Total pytest session duration in seconds",
            registry=registry,
        ),
    }

    gauges["qa_tests_total"].set(summary.total)
    gauges["qa_tests_passed"].set(summary.passed)
    gauges["qa_tests_failed"].set(summary.failed)
    gauges["qa_tests_skipped"].set(summary.skipped)
    gauges["qa_tests_flaky"].set(summary.flaky)
    gauges["qa_test_session_duration_seconds"].set(summary.duration_seconds)

    # Write-then-rename avoids partially written files being scraped by Prometheus.
    tmp_path = target.with_suffix(f"{target.suffix}.tmp")
    tmp_path.write_bytes(generate_latest(registry))
    tmp_path.replace(target)
