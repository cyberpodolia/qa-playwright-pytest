from __future__ import annotations

import logging
import json
from datetime import datetime, timezone
from typing import Any


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel("INFO")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(data)
