# QA Automation Suite (Playwright + pytest)

Small, production-style UI automation framework (kept intentionally readable) using:

- Python 3.11
- `pytest`
- Playwright sync API
- `pytest-html`
- Prometheus textfile metrics export

Target app: TodoMVC demo (`https://demo.playwright.dev/todomvc/`)

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m playwright install chromium
```

## Run tests

Quick run:

```bash
pytest
```

Typical local run with report output:

```bash
pytest \
  --browser=chromium \
  --pw-trace=on-failure \
  --video=on-failure \
  --screenshot=on-failure \
  --artifacts-dir=artifacts \
  --html=artifacts/report.html \
  --self-contained-html
```

## Debugging

Run headed with slow motion:

```bash
pytest --headed --slowmo-ms=250 -k smoke
```

Keep trace for every test:

```bash
pytest --pw-trace=on --artifacts-dir=artifacts
```

Open a saved trace:

```bash
python -m playwright show-trace artifacts/<test_nodeid_sanitized>/trace.zip
```

## Artifacts

Artifacts are stored per test in:

```text
artifacts/<test_nodeid_sanitized>/
```

Depending on options and test outcome, the framework can save:

- `screenshot.png`
- `trace.zip`
- `video.webm` (Playwright-generated filename, linked from report)
- `console-errors.txt` (console errors + page errors on failure)

Default policy is `on-failure` for trace/video/screenshot. Passing tests do not keep artifacts by
default to keep local runs and CI artifact uploads small.

`pytest-html` attaches screenshots and links to trace/video/log files in the HTML report.

## Configuration precedence

Configuration precedence is:

```text
pytest CLI options > environment variables > code defaults
```

## CLI options

- `--base-url`
- `--browser` (`chromium|firefox|webkit`)
- `--headed` / `--headless`
- `--slowmo-ms`
- `--viewport` (`WIDTHxHEIGHT`, example `1280x720`)
- `--artifacts-dir`
- `--timeout-ms`
- `--pw-trace` / `--playwright-trace` (`on|off|on-failure`)
- `--video` (`on|off|on-failure`)
- `--screenshot` (`on|off|on-failure`)
- `--locale`
- `--timezone-id`

## Environment variables

Equivalent environment variables are supported:

- `BASE_URL`
- `BROWSER`
- `HEADLESS`
- `SLOWMO_MS`
- `VIEWPORT`
- `ARTIFACTS_DIR`
- `TIMEOUT_MS`
- `TRACE`
- `VIDEO`
- `SCREENSHOT`
- `LOCALE`
- `TIMEZONE_ID`
- `METRICS_PATH` (Prometheus textfile output path, written at session end)

## Test organization

- `tests/` UI tests (`smoke`, `regression` markers)
- `pages/` page objects
- `conftest.py` pytest fixtures, reporting hooks, artifacts, logging
- `metrics.py` Prometheus textfile export

## CI

GitHub Actions runs:

- `ruff check .`
- `ruff format --check .`
- `pytest` with HTML report + JUnit XML
- artifact upload for the entire `artifacts/` directory

## Parallel runs (optional)

This repo does not require `pytest-xdist`, but if you install it you can run:

```bash
pytest -n auto
```

JSON logs include the xdist worker id when available.

Note: pytest's built-in debugging plugin defines `--trace` (different meaning). Because pytest may
accept long-option prefixes, this framework uses `--pw-trace` for Playwright trace retention policy.
