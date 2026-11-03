"""Job worker loop.

Two ways to run it:
  * embedded  — `start_embedded_workers()` spawns daemon threads inside the API
                process (default; one container, nothing else to operate).
  * external  — `python -m src.jobs.worker` in its own process/container, with the
                API started with JOB_WORKER_MODE=external. Scale by adding replicas.
"""

import logging
import os
import threading
import time

from src.jobs import service
from src.jobs.runner import run_job

logger = logging.getLogger("stockpicker.jobs")

POLL_SECONDS = 1.0
RECOVER_EVERY = 60


def worker_loop(stop: threading.Event | None = None) -> None:
    stop = stop or threading.Event()
    last_recover = 0.0
    while not stop.is_set():
        try:
            if time.monotonic() - last_recover > RECOVER_EVERY:
                last_recover = time.monotonic()
                service.recover_stale()
            job = service.claim_next()
        except Exception:
            logger.exception("worker poll failed")
            stop.wait(5)
            continue
        if job is None:
            stop.wait(POLL_SECONDS)
            continue
        logger.info("running job %s (%s)", job["id"], job["kind"])
        run_job(job)


def start_embedded_workers() -> threading.Event:
    stop = threading.Event()
    n = max(1, int(os.getenv("JOB_WORKER_THREADS", "2")))
    for i in range(n):
        threading.Thread(target=worker_loop, args=(stop,), daemon=True,
                         name=f"job-worker-{i}").start()
    logger.info("started %d embedded job workers", n)
    return stop


if __name__ == "__main__":
    from src.database.models import init_db
    logging.basicConfig(level=logging.INFO)
    init_db()
    worker_loop()
