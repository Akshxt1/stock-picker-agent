"""Run Alembic migrations programmatically (used at API/worker startup)."""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]


def _config() -> Config:
    cfg = Config(str(_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_ROOT / "alembic"))
    return cfg


def upgrade_to_head() -> None:
    logger.info("Applying database migrations")
    command.upgrade(_config(), "head")
