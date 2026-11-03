import os
import tempfile

# Must be set before any src.* import: models.py reads the environment at import time.
_db_dir = tempfile.mkdtemp(prefix="stockpicker-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_dir}/test.db"
os.environ["APP_ENV"] = "development"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["JOB_WORKER_MODE"] = "external"
os.environ["PROVIDER_MONITOR"] = "false"

import pytest

from src.database import models
from src.database.models import init_db


@pytest.fixture(scope="session", autouse=True)
def _schema():
    init_db()


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with models.Session() as s:
        for table in (models.JobEvent, models.Job, models.UserProfile):
            s.query(table).delete()
        s.commit()
