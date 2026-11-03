from datetime import timedelta

from src.database import models
from src.jobs import service


def _enqueue(kind="market_scan"):
    return service.enqueue(kind, "u1", "user", {"market": "US", "sector": "Tech", "size": "Large"})


def test_claim_is_exclusive_and_fifo():
    first, second = _enqueue(), _enqueue()
    a, b = service.claim_next(), service.claim_next()
    assert {a["id"], b["id"]} == {first, second}
    assert a["id"] == first
    assert service.claim_next() is None


def test_finish_emits_terminal_event():
    job = _enqueue()
    service.claim_next()
    service.finish(job, {"picks": []})
    assert service.get_job(job)["status"] == "done"
    events = service.events_after(job, 0)
    assert events[-1][1]["type"] == "done"


def test_fail_refunds_only_once():
    job = _enqueue()
    service.claim_next()
    assert service.fail(job, "boom") is True
    assert service.fail(job, "boom again") is False


def test_stale_job_is_requeued_then_failed_with_refund():
    models.upsert_user_profile("u1", email="u1@example.com", username="user")
    assert models.increment_run_count("u1")
    job = _enqueue()
    service.claim_next()

    def age():
        with models.Session() as s:
            j = s.get(models.Job, job)
            j.heartbeat_at = j.heartbeat_at - timedelta(hours=1)
            s.commit()

    age()
    assert service.recover_stale() == 1
    assert service.get_job(job)["status"] == "queued"

    service.claim_next()          # attempt 2
    age()
    service.recover_stale()
    assert service.get_job(job)["status"] == "error"
    with models.Session() as s:
        assert s.query(models.UserProfile).filter_by(user_id="u1").one().weekly_runs == 0
