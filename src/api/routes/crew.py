"""
src/api/routes/crew.py

GET /api/crew/stream?market=INDIA&sector=Telecom&size=Mid
GET /api/crew/stock-stream?ticker=RELIANCE.NS
  → enqueue a durable job and stream its progress as Server-Sent Events.

GET /api/crew/jobs/{id}          → job status/result (poll this if SSE drops)
GET /api/crew/jobs/{id}/stream   → re-attach to a running job's event stream

The analysis itself runs in a worker (see src/jobs), not in the request, so a
dropped connection or an API restart no longer kills the run. Events are
replayed from the database, so reconnecting resumes where the client left off.

Each SSE event is a JSON object:
  { "type": "step",  "agent": "Researcher", "kind": "tool", "text": "..." }
  { "type": "task",  "agent": "Researcher", "text": "Researcher finished." }
  { "type": "done",  "result": {...} }
  { "type": "error", "text": "Something went wrong" }
"""

import json
import time
import logging

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse

from src.api.routes.auth import get_current_user
from src.jobs import service

logger = logging.getLogger("stockpicker.crew")

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",   # tells nginx NOT to buffer SSE
}
POLL_SECONDS = 0.5
KEEPALIVE_SECONDS = 15
MAX_STREAM_SECONDS = 20 * 60


def _sse(payload: dict) -> str:
    return "data: " + json.dumps(payload) + "\n\n"


def _job_event_stream(job_id: str):
    """Tail a job's events until it finishes. Safe to call again after a disconnect."""
    last_id = 0
    started = last_ping = time.monotonic()
    while time.monotonic() - started < MAX_STREAM_SECONDS:
        events = service.events_after(job_id, last_id)
        for event_id, payload in events:
            last_id = event_id
            yield _sse(payload)
            if payload.get("type") in ("done", "error"):
                return
        if not events:
            job = service.get_job(job_id)
            if job and job["status"] in ("done", "error") and not service.events_after(job_id, last_id):
                # Terminal job whose final event is missing (e.g. pre-migration): synthesize it.
                if job["status"] == "done":
                    yield _sse({"type": "done", "result": job["result"] or {}})
                else:
                    yield _sse({"type": "error", "text": job["error"] or "Run failed"})
                return
            if time.monotonic() - last_ping > KEEPALIVE_SECONDS:
                last_ping = time.monotonic()
                yield ": keepalive\n\n"
            time.sleep(POLL_SECONDS)
    yield _sse({"type": "error", "text": "Timed out waiting for the run to finish"})


def _guard_and_claim(user: dict, claim, limit_key: str, label: str) -> None:
    """Reject guests, then atomically take one unit of the weekly quota."""
    from src.database.models import ACCOUNT_LIMITS
    account_type = user.get("account_type", "trial")
    if account_type == "guest":
        raise HTTPException(status_code=403, detail="Guest accounts cannot run analysis. Please sign up.")
    try:
        allowed = claim(user["user_id"])
    except Exception:
        # Fail closed: a broken quota check must not become unlimited free LLM spend.
        logger.exception("Quota check failed for %s", user.get("user_id"))
        raise HTTPException(status_code=503, detail="Could not verify your usage quota. Please retry shortly.")
    if not allowed:
        limit = ACCOUNT_LIMITS.get(account_type, {}).get(limit_key, 0)
        raise HTTPException(
            status_code=429,
            detail=f"Weekly {label} limit reached ({limit} for {account_type} plan). Resets next Monday.",
        )


def _enqueue_or_refund(user: dict, kind: str, params: dict) -> str:
    try:
        return service.enqueue(kind, user["user_id"], user.get("name"), params)
    except Exception:
        logger.exception("Could not enqueue %s job", kind)
        service.refund_quota(user["user_id"], kind)
        raise HTTPException(status_code=503, detail="Could not start the run. Please retry shortly.")


@router.get("/stream")
def stream_crew(
    market: str = Query(...),
    sector: str = Query(...),
    size:   str = Query(...),
    user = Depends(get_current_user),
):
    """Run a market scan. Enforces per-account weekly run limits before starting."""
    from src.database.models import increment_run_count
    _guard_and_claim(user, increment_run_count, "crew_runs", "run")
    job_id = _enqueue_or_refund(user, "market_scan",
                                {"market": market, "sector": sector, "size": size})
    return StreamingResponse(_job_event_stream(job_id), media_type="text/event-stream",
                             headers={**SSE_HEADERS, "X-Job-Id": job_id})


@router.get("/stock-stream")
def stream_single_stock(
    ticker: str = Query(...),
    user = Depends(get_current_user),
):
    """Run a full 4-agent Deep Analysis on one ticker (1 unit of the weekly deep quota)."""
    from src.database.models import increment_portfolio_run_count
    _guard_and_claim(user, increment_portfolio_run_count, "portfolio_runs", "analysis")
    job_id = _enqueue_or_refund(user, "deep_analysis", {"ticker": ticker})
    return StreamingResponse(_job_event_stream(job_id), media_type="text/event-stream",
                             headers={**SSE_HEADERS, "X-Job-Id": job_id})


def _owned_job(job_id: str, user: dict) -> dict:
    job = service.get_job(job_id)
    if not job or (job["user_id"] != user["user_id"] and user.get("account_type") != "admin"):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}")
def get_job(job_id: str, user = Depends(get_current_user)):
    job = _owned_job(job_id, user)
    job.pop("user_id", None)
    return job


@router.get("/jobs/{job_id}/stream")
def stream_job(job_id: str, user = Depends(get_current_user)):
    _owned_job(job_id, user)
    return StreamingResponse(_job_event_stream(job_id), media_type="text/event-stream",
                             headers={**SSE_HEADERS, "X-Job-Id": job_id})
