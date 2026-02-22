# Shared page-object helpers for navigation and common expectations.
from __future__ import annotations

from playwright.sync_api import (
    Locator,
    Page,
    expect,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)


class BasePage:
    """Base class for page objects with consistent timeout-aware helpers."""

    def __init__(self, page: Page, base_url: str, timeout_ms: int = 10_000) -> None:
        self.page = page
        self.base_url = base_url
        self.timeout_ms = timeout_ms

    def goto(self, path: str = "") -> None:
        """Navigate to a path under base_url, retrying once for transient demo-site slowness."""

        url = f"{self.base_url}{path}"
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        except PlaywrightTimeoutError:
            # One retry handles transient demo-site/network hiccups.
            self.page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)

    def expect_visible(self, locator: Locator) -> None:
        """Assert visibility using the page object's configured timeout."""
        expect(locator).to_be_visible(timeout=self.timeout_ms)
