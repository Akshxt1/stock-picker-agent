"""Logging setup: plain text by default, JSON lines with LOG_FORMAT=json.

Containers should log to stdout only (the platform collects it). A rotating
file is added only when LOG_TO_FILE=true, e.g. for local debugging.
"""

import json
import logging
import logging.handlers
import os
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data)


def configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if os.getenv("LOG_TO_FILE", "").lower() in ("1", "true", "yes"):
        log_dir = Path(__file__).parents[2] / "logs"
        log_dir.mkdir(exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            log_dir / "app.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"))

    if os.getenv("LOG_FORMAT", "text").lower() == "json":
        fmt: logging.Formatter = JsonFormatter()
    else:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for h in handlers:
        h.setFormatter(fmt)
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), handlers=handlers, force=True)
