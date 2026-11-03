"""Logging setup: plain text by default, JSON lines with LOG_FORMAT=json.

Containers should log to stdout only (the platform collects it). A rotating
file is added only when LOG_TO_FILE=true, e.g. for local debugging.
"""

import json
import logging
import logging.handlers
import os
from collections import deque
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


class RingBufferHandler(logging.Handler):
    """Keeps the last N formatted log lines in memory so the admin page can show recent
    logs even where there is no log file (containers, ephemeral disks)."""

    def __init__(self, capacity: int = 1000):
        super().__init__()
        self.lines: deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.lines.append(self.format(record))
        except Exception:
            self.handleError(record)


_ring = RingBufferHandler()


def recent_logs(n: int = 100) -> list[str]:
    return list(_ring.lines)[-n:]


def configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(), _ring]
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
