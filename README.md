# QA Automation Suite (Playwright + pytest)

[![CI](https://github.com/yourname/repo2-qa-playwright-pytest/actions/workflows/ci.yml/badge.svg)](https://github.com/yourname/repo2-qa-playwright-pytest/actions/workflows/ci.yml)

Small UI automation suite using Playwright + pytest against a stable demo site.

## Run in 60 seconds

```bash
python -m venv .venv
. .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m playwright install chromium
pytest --html=artifacts/report.html --self-contained-html
```

## Quickstart

```bash
pytest -q
```

## What this demonstrates

- Playwright UI automation with a simple Page Object
- Stable selectors and explicit expectations
- HTML reporting and artifacts in CI
- Clean test layout and configuration

## Configuration

- `BASE_URL` (default `https://demo.playwright.dev/todomvc/`)
- `HEADLESS` (default `1`)

## Notes

- Screenshots are saved to `artifacts/` on failure.
- CI uploads the HTML report artifact.
- Set `METRICS_PATH` to write Prometheus metrics after the test session (textfile).

