"""Pytest entrypoint for framework fixtures, artifacts, reporting, and metrics.

Main flow: resolve settings once, create session-scoped Playwright/browser,
create per-test contexts/pages, then publish artifacts/logs/metrics via hooks.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from config import BROWSER_CHOICES, MODE_CHOICES, Settings, get_settings
from metrics import SessionMetrics, write_metrics
from pages.todo_page import TodoPage
from qa_logging import setup_logging

try:
    from pytest_metadata.plugin import metadata_key
except Exception:  # pragma: no cover - optional plugin path
    metadata_key = None

LOGGER = logging.getLogger("qa")
_session_start: float | None = None
_session_results = {"passed": 0, "failed": 0, "skipped": 0}
_rerun_nodeids: set[str] = set()
_counted_nodeids: set[str] = set()


def _sanitize_nodeid(nodeid: str) -> str:
    """Convert pytest nodeids into filesystem-safe artifact directory names."""
    sanitized = re.sub(r"[^\w.-]+", "__", nodeid)
    return sanitized.strip("._") or "test"


def _safe_remove(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        LOGGER.exception("artifact_cleanup_failed", extra={"path": str(path)})


def _should_persist(mode: str, failed: bool) -> bool:
    """Apply on/off/on-failure artifact retention policy."""
    if mode == "on":
        return True
    if mode == "off":
        return False
    return failed


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register framework CLI options layered on top of env/default config."""
    group = parser.getgroup("qa-ui")
    group.addoption(
        "--base-url",
        action="store",
        dest="base_url",
        default=None,
        help="Target base URL",
    )
    group.addoption(
        "--browser",
        action="store",
        dest="browser",
        choices=sorted(BROWSER_CHOICES),
        default=None,
        help="Browser engine",
    )
    group.addoption(
        "--headed",
        action="store_const",
        const=False,
        dest="headless",
        default=None,
        help="Run headed (same as --headless=false)",
    )
    group.addoption(
        "--headless",
        action="store_const",
        const=True,
        dest="headless",
        help="Force headless mode",
    )
    group.addoption(
        "--slowmo-ms",
        action="store",
        type=int,
        dest="slowmo_ms",
        default=None,
        help="Playwright launch slow motion delay in milliseconds",
    )
    group.addoption(
        "--viewport",
        action="store",
        dest="viewport",
        default=None,
        help="Viewport size as WIDTHxHEIGHT (e.g. 1280x720)",
    )
    group.addoption(
        "--artifacts-dir",
        action="store",
        dest="artifacts_dir",
        default=None,
        help="Directory for per-test artifacts and reports",
    )
    group.addoption(
        "--pw-trace",
        "--playwright-trace",
        action="store",
        dest="pw_trace",
        choices=sorted(MODE_CHOICES),
        default=None,
        help="Playwright tracing policy: on|off|on-failure",
    )
    group.addoption(
        "--video",
        action="store",
        dest="video",
        choices=sorted(MODE_CHOICES),
        default=None,
        help="Video capture policy: on|off|on-failure",
    )
    group.addoption(
        "--screenshot",
        action="store",
        dest="screenshot",
        choices=sorted(MODE_CHOICES),
        default=None,
        help="Screenshot capture policy: on|off|on-failure",
    )
    group.addoption(
        "--timeout-ms",
        action="store",
        type=int,
        dest="timeout_ms",
        default=None,
        help="Default action/navigation timeout in milliseconds",
    )
    group.addoption(
        "--locale",
        action="store",
        dest="locale",
        default=None,
        help="Browser context locale (default en-US)",
    )
    group.addoption(
        "--timezone-id",
        action="store",
        dest="timezone_id",
        default=None,
        help="Browser context timezone (default UTC)",
    )


@pytest.fixture(scope="session", autouse=True)
def _init_logging() -> None:
    setup_logging()


@pytest.fixture(scope="session")
def settings(pytestconfig: pytest.Config) -> Settings:
    """Session-cached settings fixture used by all browser/page fixtures."""
    configured = get_settings(pytestconfig)
    configured.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return configured


def pytest_configure(config: pytest.Config) -> None:
    """Register markers and enrich pytest-html metadata when the plugin is present."""
    config.addinivalue_line("markers", "smoke: critical path UI tests")
    config.addinivalue_line("markers", "regression: broader functional UI coverage")

    if metadata_key is None:
        return

    settings = get_settings(config)
    metadata = config.stash.setdefault(metadata_key, {})
    metadata["base_url"] = settings.base_url
    metadata["browser"] = settings.browser_name
    metadata["headless"] = str(settings.headless)
    metadata["viewport"] = f"{settings.viewport_width}x{settings.viewport_height}"
    metadata["timeout_ms"] = str(settings.timeout_ms)
    metadata["commit_sha"] = os.getenv("GITHUB_SHA", "")[:12] or "local"


def pytest_sessionstart(session: pytest.Session) -> None:
    global _session_start
    _session_start = time.perf_counter()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Publish Prometheus textfile metrics if METRICS_PATH is configured."""
    if _session_start is None:
        return
    duration = time.perf_counter() - _session_start
    metrics_path = os.getenv("METRICS_PATH")
    if not metrics_path:
        return
    summary = SessionMetrics(
        total=session.testscollected or 0,
        passed=_session_results["passed"],
        failed=_session_results["failed"],
        skipped=_session_results["skipped"],
        flaky=len(_rerun_nodeids),
        duration_seconds=duration,
    )
    write_metrics(metrics_path, summary)


@pytest.fixture(scope="session")
def playwright_instance() -> Generator[Playwright, None, None]:
    """Session-scoped Playwright driver process."""
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(settings: Settings, playwright_instance: Playwright) -> Generator[Browser, None, None]:
    """Session-scoped browser reused across isolated per-test contexts."""
    browser_type = getattr(playwright_instance, settings.browser_name)
    browser = browser_type.launch(headless=settings.headless, slow_mo=settings.slowmo_ms)
    yield browser
    browser.close()


@pytest.fixture
def page(
    request: pytest.FixtureRequest,
    browser: Browser,
    settings: Settings,
) -> Generator[Page, None, None]:
    """Create a per-test browser context/page and manage failure diagnostics artifacts."""
    test_dir = settings.artifacts_dir / _sanitize_nodeid(request.node.nodeid)
    test_dir.mkdir(parents=True, exist_ok=True)
    # Hook state is stored on the pytest item so setup/call/teardown hooks can share it.
    request.node._qa_artifact_dir = test_dir  # type: ignore[attr-defined]

    context_kwargs: dict[str, object] = {
        "viewport": settings.viewport,
        "locale": settings.locale,
        "timezone_id": settings.timezone_id,
    }
    if settings.video != "off":
        # Playwright records videos per-context; writing to the test dir simplifies cleanup.
        context_kwargs["record_video_dir"] = str(test_dir)

    context = browser.new_context(**context_kwargs)
    context.set_default_timeout(settings.timeout_ms)
    context.set_default_navigation_timeout(settings.timeout_ms)
    if settings.trace != "off":
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()
    page.set_default_timeout(settings.timeout_ms)
    page.set_default_navigation_timeout(settings.timeout_ms)

    console_errors: list[str] = []
    page_errors: list[str] = []

    def on_console(msg) -> None:
        if msg.type == "error":
            console_errors.append(msg.text)

    def on_page_error(exc) -> None:
        page_errors.append(str(exc))

    page.on("console", on_console)
    page.on("pageerror", on_page_error)

    request.node._qa_console_errors = console_errors  # type: ignore[attr-defined]
    request.node._qa_page_errors = page_errors  # type: ignore[attr-defined]
    request.node._qa_artifacts = {}  # type: ignore[attr-defined]

    yield page

    rep_call = getattr(request.node, "rep_call", None)
    failed = bool(rep_call and rep_call.failed)
    artifacts: dict[str, str] = {}

    if _should_persist(settings.screenshot, failed):
        screenshot_path = test_dir / "screenshot.png"
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
            artifacts["screenshot"] = str(screenshot_path)
        except Exception:
            LOGGER.exception(
                "screenshot_capture_failed",
                extra={"test_nodeid": request.node.nodeid},
            )

    if settings.trace != "off":
        trace_path = test_dir / "trace.zip"
        try:
            if _should_persist(settings.trace, failed):
                context.tracing.stop(path=str(trace_path))
                artifacts["trace"] = str(trace_path)
            else:
                context.tracing.stop()
        except Exception:
            LOGGER.exception("trace_capture_failed", extra={"test_nodeid": request.node.nodeid})

    console_log_path = test_dir / "console-errors.txt"
    combined_errors = []
    if console_errors:
        combined_errors.extend([f"[console] {msg}" for msg in console_errors])
    if page_errors:
        combined_errors.extend([f"[pageerror] {msg}" for msg in page_errors])
    if failed and combined_errors:
        # Negative diagnostics are most useful on failures; skip noisier logs on passing tests.
        console_log_path.write_text("\n".join(combined_errors) + "\n", encoding="utf-8")
        artifacts["console_errors"] = str(console_log_path)

    video_path_to_delete: Path | None = None
    try:
        video = page.video
        if video is not None:
            video_path = Path(video.path())
            if _should_persist(settings.video, failed):
                artifacts["video"] = str(video_path)
            else:
                video_path_to_delete = video_path
    except Exception:
        LOGGER.exception("video_capture_failed", extra={"test_nodeid": request.node.nodeid})

    request.node._qa_artifacts = artifacts  # type: ignore[attr-defined]

    context.close()

    if video_path_to_delete is not None:
        _safe_remove(video_path_to_delete)

    # Drop empty directories so on-failure mode does not leave artifact folders for passing tests.
    if not artifacts and test_dir.exists():
        _safe_remove(test_dir)


@pytest.fixture
def todo_page(page: Page, settings: Settings) -> TodoPage:
    """Convenience fixture returning an already-open TodoMVC page object."""
    todo = TodoPage(page=page, base_url=settings.base_url, timeout_ms=settings.timeout_ms)
    todo.open()
    return todo


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Emit a structured start event for each test before fixture-heavy setup runs."""
    item._qa_test_started_at = time.perf_counter()  # type: ignore[attr-defined]
    settings = get_settings(item.config)
    artifact_dir = settings.artifacts_dir / _sanitize_nodeid(item.nodeid)
    LOGGER.info(
        "test_start",
        extra={
            "event": "test_start",
            "test_nodeid": item.nodeid,
            "browser": settings.browser_name,
            "base_url": settings.base_url,
            "headless": settings.headless,
            "worker": os.getenv("PYTEST_XDIST_WORKER", "master"),
            "artifact_dir": str(artifact_dir),
            "retries": max(getattr(item, "execution_count", 1) - 1, 0),
        },
    )


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    """Capture per-phase reports, attach artifacts, and emit structured end events."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    if report.when == "teardown":
        pytest_html = item.config.pluginmanager.getplugin("html")
        if pytest_html:
            # pytest-html changed `extra` -> `extras` across versions; support both.
            extras = list(getattr(report, "extras", getattr(report, "extra", [])))
            artifact_paths: dict[str, str] = getattr(item, "_qa_artifacts", {})
            if "screenshot" in artifact_paths:
                extras.append(pytest_html.extras.image(artifact_paths["screenshot"]))
            if "trace" in artifact_paths:
                extras.append(pytest_html.extras.url(artifact_paths["trace"], name="trace.zip"))
            if "video" in artifact_paths:
                extras.append(pytest_html.extras.url(artifact_paths["video"], name="video.webm"))
            if "console_errors" in artifact_paths:
                extras.append(
                    pytest_html.extras.url(
                        artifact_paths["console_errors"],
                        name="console-errors.txt",
                    )
                )
            report.extras = extras
            report.extra = extras

        started_at = getattr(item, "_qa_test_started_at", None)
        duration_ms = int((time.perf_counter() - started_at) * 1000) if started_at else None
        setup_report = getattr(item, "rep_setup", None)
        call_report = getattr(item, "rep_call", None)
        # Derive a single user-facing outcome from pytest's multi-phase reports.
        if setup_report is not None and setup_report.failed:
            outcome_name = "error"
        elif call_report is not None:
            outcome_name = call_report.outcome
        elif setup_report is not None and setup_report.skipped:
            outcome_name = "skipped"
        elif report.failed:
            outcome_name = "error"
        else:
            outcome_name = report.outcome
        settings = get_settings(item.config)
        artifact_dir = getattr(
            item,
            "_qa_artifact_dir",
            settings.artifacts_dir / _sanitize_nodeid(item.nodeid),
        )
        LOGGER.info(
            "test_end",
            extra={
                "event": "test_end",
                "test_nodeid": item.nodeid,
                "outcome": outcome_name,
                "duration_ms": duration_ms,
                "browser": settings.browser_name,
                "base_url": settings.base_url,
                "headless": settings.headless,
                "worker": os.getenv("PYTEST_XDIST_WORKER", "master"),
                "artifact_dir": str(artifact_dir),
                "retries": max(getattr(item, "execution_count", 1) - 1, 0),
            },
        )


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Track one aggregate outcome per test for session metrics export."""
    if report.outcome == "rerun":
        _rerun_nodeids.add(report.nodeid)
        return

    should_count = False
    if report.when == "call":
        should_count = True
    elif report.when == "setup" and report.skipped:
        should_count = True

    # Count each nodeid once to avoid double-counting setup/call/teardown phases.
    if not should_count or report.nodeid in _counted_nodeids:
        return

    _counted_nodeids.add(report.nodeid)
    if report.passed:
        _session_results["passed"] += 1
    elif report.failed:
        _session_results["failed"] += 1
    elif report.skipped:
        _session_results["skipped"] += 1


def pytest_html_report_title(report) -> None:
    report.title = "QA UI Automation Report"
