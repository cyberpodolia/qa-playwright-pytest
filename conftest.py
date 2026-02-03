from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from config import get_settings
from metrics import write_metrics
from pages.todo_page import TodoPage
from qa_logging import setup_logging

_session_start: float | None = None


@pytest.fixture(scope="session", autouse=True)
def _init_logging() -> None:
    setup_logging()


def pytest_sessionstart(session):
    global _session_start
    _session_start = time.perf_counter()


def pytest_sessionfinish(session, exitstatus):
    if _session_start is None:
        return
    duration = time.perf_counter() - _session_start
    metrics_path = os.getenv("METRICS_PATH")
    if metrics_path:
        write_metrics(metrics_path, session.testscollected or 0, session.testsfailed, duration)


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    settings = get_settings()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.headless)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser) -> Generator[Page, None, None]:
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def todo_page(page: Page) -> TodoPage:
    settings = get_settings()
    todo = TodoPage(page, settings.base_url)
    todo.open()
    return todo


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or report.passed:
        return

    page = item.funcargs.get("page")
    if page is None:
        return

    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    screenshot_path = artifacts / f"{item.name}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)

    pytest_html = item.config.pluginmanager.getplugin("html")
    if pytest_html:
        extra = getattr(report, "extra", [])
        extra.append(pytest_html.extras.image(str(screenshot_path)))
        report.extra = extra
