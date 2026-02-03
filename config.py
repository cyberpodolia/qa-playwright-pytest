from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    base_url: str
    headless: bool


def get_settings() -> Settings:
    base_url = os.getenv("BASE_URL", "https://demo.playwright.dev/todomvc/")
    headless = os.getenv("HEADLESS", "1") != "0"
    return Settings(base_url=base_url, headless=headless)
