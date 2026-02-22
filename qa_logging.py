"""JSON logging helpers used by pytest hooks and fixtures.

The formatter preserves standard log fields and merges custom `extra` values so
test lifecycle events can be consumed by CI/log aggregation tools.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

_STANDARD_FIELDS = set(logging.makeLogRecord({}).__dict__.keys())


def setup_logging() -> None:
    """Configure root logging for one-line JSON output."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class JsonFormatter(logging.Formatter):
    """Serialize log records as compact JSON with support for `extra` fields."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Keep only caller-provided fields; stdlib logging internals stay out of payloads.
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_FIELDS and not key.startswith("_")
        }
        if extras:
            data.update(extras)
        return json.dumps(data, default=str)
