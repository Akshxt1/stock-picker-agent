import threading

from src.database import models
from src.database.models import ACCOUNT_LIMITS, upsert_user_profile


def _user(uid="u1", acct="trial"):
    upsert_user_profile(uid, email=f"{uid}@example.com", username=uid)
    models.update_account_type(uid, acct)


def test_quota_stops_at_limit():
    _user()
    limit = ACCOUNT_LIMITS["trial"]["crew_runs"]
    results = [models.increment_run_count("u1") for _ in range(limit + 3)]
    assert results.count(True) == limit
    assert not any(results[limit:])


def test_quota_is_atomic_under_concurrency():
    _user()
    limit = ACCOUNT_LIMITS["trial"]["portfolio_runs"]
    allowed = []

    def grab():
        allowed.append(models.increment_portfolio_run_count("u1"))

    threads = [threading.Thread(target=grab) for _ in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert allowed.count(True) == limit


def test_refund_restores_one_unit_and_never_goes_negative():
    _user()
    assert models.increment_run_count("u1")
    models.decrement_run_count("u1")
    models.decrement_run_count("u1")
    with models.Session() as s:
        assert s.query(models.UserProfile).filter_by(user_id="u1").one().weekly_runs == 0


def test_guest_has_no_quota():
    _user("g1", "guest")
    assert models.increment_run_count("g1") is False
