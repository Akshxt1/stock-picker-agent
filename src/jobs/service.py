"""Durable job queue on top of the application database.

Works on SQLite and Postgres. Claiming is a compare-and-set UPDATE, so several
workers (threads or processes) can poll the same table without double-running.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from src.database.models import Session, Job, JobEvent

STALE_AFTER = timedelta(minutes=10)    # running job with no heartbeat for this long is dead
MAX_ATTEMPTS = 2


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def enqueue(kind: str, user_id: str, username: str | None, params: dict) -> str:
    job_id = uuid.uuid4().hex
    with Session() as sess:
        sess.add(Job(id=job_id, user_id=user_id, username=username, kind=kind,
                     params=params, status="queued", created_at=_now()))
        sess.commit()
    return job_id


def claim_next() -> dict | None:
    """Atomically move the oldest queued job to 'running' and return it."""
    with Session() as sess:
        for _ in range(5):
            row = (sess.query(Job).filter(Job.status == "queued")
                   .order_by(Job.created_at).first())
            if not row:
                return None
            now = _now()
            res = sess.execute(
                update(Job)
                .where(Job.id == row.id, Job.status == "queued")
                .values(status="running", started_at=now, heartbeat_at=now,
                        attempts=Job.attempts + 1)
            )
            sess.commit()
            if res.rowcount == 1:
                return {"id": row.id, "user_id": row.user_id, "username": row.username,
                        "kind": row.kind, "params": row.params or {},
                        "attempts": (row.attempts or 0) + 1}
            sess.expire_all()
    return None


def heartbeat(job_id: str) -> None:
    with Session() as sess:
        sess.execute(update(Job).where(Job.id == job_id, Job.status == "running")
                     .values(heartbeat_at=_now()))
        sess.commit()


def add_event(job_id: str, payload: dict) -> None:
    with Session() as sess:
        sess.add(JobEvent(job_id=job_id, payload=payload, created_at=_now()))
        sess.commit()


def finish(job_id: str, result: dict) -> None:
    with Session() as sess:
        sess.execute(update(Job).where(Job.id == job_id)
                     .values(status="done", result=result, finished_at=_now()))
        sess.commit()
    add_event(job_id, {"type": "done", "result": result})


def fail(job_id: str, message: str) -> bool:
    """Mark failed. Returns True the first time only, i.e. when the caller should refund quota."""
    with Session() as sess:
        sess.execute(update(Job).where(Job.id == job_id)
                     .values(status="error", error=message[:2000], finished_at=_now()))
        res = sess.execute(update(Job).where(Job.id == job_id, Job.refunded == False)  # noqa: E712
                           .values(refunded=True))
        sess.commit()
        refund = res.rowcount == 1
    add_event(job_id, {"type": "error", "text": message[:500]})
    return refund


def recover_stale() -> int:
    """Re-queue (or fail) running jobs whose worker stopped heartbeating.

    Returns how many jobs were touched. Jobs that exhausted their attempts are
    failed and their quota refunded.
    """
    cutoff = _now() - STALE_AFTER
    with Session() as sess:
        stale = sess.query(Job).filter(Job.status == "running", Job.heartbeat_at < cutoff).all()
        ids = [(j.id, j.attempts or 0, j.user_id, j.kind) for j in stale]
    for job_id, attempts, user_id, kind in ids:
        if attempts >= MAX_ATTEMPTS:
            if fail(job_id, "Worker stopped responding; run abandoned."):
                refund_quota(user_id, kind)
        else:
            with Session() as sess:
                sess.execute(update(Job).where(Job.id == job_id, Job.status == "running")
                             .values(status="queued"))
                sess.commit()
    return len(ids)


def refund_quota(user_id: str, kind: str) -> None:
    from src.database.models import decrement_run_count, decrement_portfolio_run_count
    if kind == "market_scan":
        decrement_run_count(user_id)
    elif kind in ("deep_analysis", "portfolio_strategy"):
        decrement_portfolio_run_count(user_id)


def get_job(job_id: str) -> dict | None:
    with Session() as sess:
        j = sess.get(Job, job_id)
        if not j:
            return None
        return {"id": j.id, "user_id": j.user_id, "kind": j.kind, "status": j.status,
                "result": j.result, "error": j.error,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "finished_at": j.finished_at.isoformat() if j.finished_at else None}


def events_after(job_id: str, last_id: int, limit: int = 200) -> list[tuple[int, dict]]:
    with Session() as sess:
        rows = (sess.query(JobEvent).filter(JobEvent.job_id == job_id, JobEvent.id > last_id)
                .order_by(JobEvent.id).limit(limit).all())
        return [(r.id, r.payload) for r in rows]
