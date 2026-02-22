"""Centralized runtime settings for pytest + Playwright execution.

This module resolves values from CLI options and environment variables, then
returns one immutable Settings object used across fixtures and hooks.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest import Config

DEFAULT_BASE_URL = "https://demo.playwright.dev/todomvc/"
DEFAULT_BROWSER = "chromium"
DEFAULT_VIEWPORT = "1280x720"
DEFAULT_ARTIFACTS_DIR = "artifacts"
DEFAULT_TIMEOUT_MS = 10_000
DEFAULT_TRACE_MODE = "on-failure"
DEFAULT_VIDEO_MODE = "on-failure"
DEFAULT_SCREENSHOT_MODE = "on-failure"
MODE_CHOICES = {"on", "off", "on-failure"}
BROWSER_CHOICES = {"chromium", "firefox", "webkit"}


@dataclass(frozen=True)
class Settings:
    """Resolved framework settings shared by fixtures and reporting hooks."""

    base_url: str
    browser_name: str
    headless: bool
    slowmo_ms: int
    viewport_width: int
    viewport_height: int
    artifacts_dir: Path
    timeout_ms: int
    trace: str
    video: str
    screenshot: str
    locale: str
    timezone_id: str

    @property
    def viewport(self) -> dict[str, int]:
        return {"width": self.viewport_width, "height": self.viewport_height}

    @property
    def headed(self) -> bool:
        return not self.headless


def _get_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _parse_bool(value: str, *, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean for {name}: {value!r}")


def _parse_int(value: str, *, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be >= 0, got {parsed}")
    return parsed


def parse_viewport(value: str) -> tuple[int, int]:
    """Parse a WIDTHxHEIGHT viewport string into integer dimensions."""

    normalized = value.lower().strip()
    width_str, sep, height_str = normalized.partition("x")
    if not sep:
        raise ValueError(f"Viewport must be WIDTHxHEIGHT, got {value!r}")
    width = _parse_int(width_str, name="viewport width")
    height = _parse_int(height_str, name="viewport height")
    if width == 0 or height == 0:
        raise ValueError(f"Viewport dimensions must be > 0, got {value!r}")
    return width, height


def _pick(cli_value, env_value, default_value):
    if cli_value is not None:
        return cli_value
    if env_value is not None:
        return env_value
    return default_value


def _build_settings_from_sources(*, cli: dict[str, object] | None) -> Settings:
    """Merge CLI/env/defaults with precedence CLI > env > defaults."""

    cli = cli or {}

    base_url = str(_pick(cli.get("base_url"), _get_env("BASE_URL"), DEFAULT_BASE_URL))
    browser_name = (
        str(_pick(cli.get("browser"), _get_env("BROWSER"), DEFAULT_BROWSER)).strip().lower()
    )
    if browser_name not in BROWSER_CHOICES:
        raise ValueError(
            f"Unsupported browser {browser_name!r}; expected one of {sorted(BROWSER_CHOICES)}"
        )

    headless_cli = cli.get("headless")
    headless_env = _get_env("HEADLESS")
    if isinstance(headless_cli, bool):
        headless = headless_cli
    elif headless_env is not None:
        headless = _parse_bool(headless_env, name="HEADLESS")
    else:
        headless = True

    slowmo_raw = _pick(cli.get("slowmo_ms"), _get_env("SLOWMO_MS"), 0)
    slowmo_ms = (
        slowmo_raw if isinstance(slowmo_raw, int) else _parse_int(str(slowmo_raw), name="SLOWMO_MS")
    )

    viewport_raw = str(_pick(cli.get("viewport"), _get_env("VIEWPORT"), DEFAULT_VIEWPORT))
    viewport_width, viewport_height = parse_viewport(viewport_raw)

    artifacts_raw = str(
        _pick(cli.get("artifacts_dir"), _get_env("ARTIFACTS_DIR"), DEFAULT_ARTIFACTS_DIR)
    )
    artifacts_dir = Path(artifacts_raw)

    timeout_raw = _pick(cli.get("timeout_ms"), _get_env("TIMEOUT_MS"), DEFAULT_TIMEOUT_MS)
    timeout_ms = (
        timeout_raw
        if isinstance(timeout_raw, int)
        else _parse_int(str(timeout_raw), name="TIMEOUT_MS")
    )

    trace = str(_pick(cli.get("trace"), _get_env("TRACE"), DEFAULT_TRACE_MODE)).lower()
    video = str(_pick(cli.get("video"), _get_env("VIDEO"), DEFAULT_VIDEO_MODE)).lower()
    screenshot = str(
        _pick(cli.get("screenshot"), _get_env("SCREENSHOT"), DEFAULT_SCREENSHOT_MODE)
    ).lower()
    for mode_name, mode_value in (("trace", trace), ("video", video), ("screenshot", screenshot)):
        if mode_value not in MODE_CHOICES:
            raise ValueError(
                f"Invalid {mode_name} mode {mode_value!r}; expected one of {sorted(MODE_CHOICES)}"
            )

    locale = str(_pick(cli.get("locale"), _get_env("LOCALE"), "en-US"))
    timezone_id = str(_pick(cli.get("timezone_id"), _get_env("TIMEZONE_ID"), "UTC"))

    return Settings(
        base_url=base_url,
        browser_name=browser_name,
        headless=headless,
        slowmo_ms=slowmo_ms,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        artifacts_dir=artifacts_dir,
        timeout_ms=timeout_ms,
        trace=trace,
        video=video,
        screenshot=screenshot,
        locale=locale,
        timezone_id=timezone_id,
    )


def get_settings(pytest_config: Config | None = None) -> Settings:
    """Return the cached Settings for a pytest session, or an env/default-only copy."""

    if pytest_config is None:
        return _build_settings_from_sources(cli=None)

    # Cache on pytest config so hooks/fixtures share one consistent view of options.
    cached = getattr(pytest_config, "_qa_settings_cache", None)
    if cached is not None:
        return cached

    cli_values: dict[str, object] = {
        "base_url": pytest_config.getoption("base_url"),
        "browser": pytest_config.getoption("browser"),
        "headless": pytest_config.getoption("headless"),
        "slowmo_ms": pytest_config.getoption("slowmo_ms"),
        "viewport": pytest_config.getoption("viewport"),
        "artifacts_dir": pytest_config.getoption("artifacts_dir"),
        "trace": pytest_config.getoption("pw_trace"),
        "video": pytest_config.getoption("video"),
        "screenshot": pytest_config.getoption("screenshot"),
        "timeout_ms": pytest_config.getoption("timeout_ms"),
        "locale": pytest_config.getoption("locale"),
        "timezone_id": pytest_config.getoption("timezone_id"),
    }
    settings = _build_settings_from_sources(cli=cli_values)
    pytest_config._qa_settings_cache = settings  # type: ignore[attr-defined]
    return settings
