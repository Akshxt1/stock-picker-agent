"""Execute one claimed job and record its progress."""

import logging
import threading

from src.jobs import service
from src.jobs.events import make_callbacks

logger = logging.getLogger("stockpicker.jobs")

HEARTBEAT_EVERY = 30  # seconds


def _persist_picks(result: dict, user_id: str, username: str | None) -> None:
    try:
        from src.database.paper_trading import save_picks
        saved = save_picks(result, run_by_user_id=user_id, run_by_username=username)
        if saved:
            result["picks"] = saved
    except Exception:
        logger.exception("save_picks failed")


def _execute(job: dict, sink) -> dict:
    from src.agents.crew import run_stock_picker, run_single_stock_analysis
    step_cb, task_cb = make_callbacks(sink)
    p = job["params"]
    if job["kind"] == "market_scan":
        return run_stock_picker(p["market"], p["sector"], p["size"],
                                user_id=job["user_id"], username=job["username"],
                                step_callback=step_cb, task_callback=task_cb)
    if job["kind"] == "deep_analysis":
        return run_single_stock_analysis(p["ticker"],
                                         user_id=job["user_id"], username=job["username"],
                                         step_callback=step_cb, task_callback=task_cb)
    if job["kind"] == "portfolio_strategy":
        from src.portfolio_agent import job as strategy_job
        return strategy_job.run(p, sink)
    raise ValueError(f"Unknown job kind: {job['kind']}")


def run_job(job: dict) -> None:
    job_id = job["id"]
    stop = threading.Event()

    def beat():
        while not stop.wait(HEARTBEAT_EVERY):
            try:
                service.heartbeat(job_id)
            except Exception:
                logger.exception("heartbeat failed for %s", job_id)

    threading.Thread(target=beat, daemon=True).start()
    try:
        result = _execute(job, lambda payload: service.add_event(job_id, payload))
        if result.get("error") and not result.get("picks"):
            raise RuntimeError(result["error"])
        if job["kind"] in ("market_scan", "deep_analysis"):
            _persist_picks(result, job["user_id"], job["username"])
        service.finish(job_id, result)
    except Exception as e:
        logger.exception("job %s failed", job_id)
        if service.fail(job_id, str(e)):
            service.refund_quota(job["user_id"], job["kind"])
    finally:
        stop.set()
