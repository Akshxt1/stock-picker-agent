import json

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.auth import get_current_user
from src.database import models
from src.jobs import service


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "u1", "name": "user", "account_type": "trial"}
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_and_ready(client):
    assert client.get("/health").json() == {"status": "ok"}
    body = client.get("/ready").json()
    assert body["status"] == "ready"


def test_stream_enqueues_job_and_replays_events(client):
    models.upsert_user_profile("u1", email="u1@example.com", username="user")
    # Pre-seed a finished job's events by completing whatever the endpoint enqueues.
    import threading, time

    def fake_worker():
        for _ in range(100):
            job = service.claim_next()
            if job:
                service.add_event(job["id"], {"type": "step", "agent": "Researcher", "text": "hi"})
                service.finish(job["id"], {"picks": []})
                return
            time.sleep(0.05)

    t = threading.Thread(target=fake_worker)
    t.start()
    with client.stream("GET", "/api/crew/stream?market=US&sector=Tech&size=Large") as r:
        job_id = r.headers["x-job-id"]
        payloads = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    t.join()
    assert [p["type"] for p in payloads] == ["step", "done"]

    # Reconnecting replays the same events from the database.
    with client.stream("GET", f"/api/crew/jobs/{job_id}/stream") as r:
        again = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert again == payloads


def test_guest_cannot_start_runs(client):
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "g1", "name": "g", "account_type": "guest"}
    assert client.get("/api/crew/stream?market=US&sector=Tech&size=Large").status_code == 403


def test_quota_exhaustion_returns_429(client):
    models.upsert_user_profile("u1", email="u1@example.com", username="user")
    limit = models.ACCOUNT_LIMITS["trial"]["crew_runs"]
    for _ in range(limit):
        assert models.increment_run_count("u1")
    assert client.get("/api/crew/stream?market=US&sector=Tech&size=Large").status_code == 429
    assert service.claim_next() is None   # nothing was enqueued


def test_job_not_visible_to_other_users(client):
    other = service.enqueue("market_scan", "someone-else", "x", {})
    assert client.get(f"/api/crew/jobs/{other}").status_code == 404
