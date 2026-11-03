import base64
import json
import time

import pytest
import requests
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.auth import get_current_user
from src.providers import health


def _jwt(exp: float) -> str:
    def enc(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{enc({'alg': 'HS256'})}.{enc({'exp': exp})}.sig"


class _Resp:
    def __init__(self, code):
        self.status_code = code


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    health._cache.clear()
    health._last_status.clear()
    health._last_warned.clear()
    monkeypatch.delenv("UPSTOX_ANALYTICS_TOKEN", raising=False)


def test_not_configured():
    assert health.check_upstox()["status"] == "not_configured"


def test_expired_token_detected_without_network(monkeypatch):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", _jwt(time.time() - 86400))
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("should not call network"))
    assert health.check_upstox()["status"] == "token_expired"


@pytest.mark.parametrize("code,status", [(200, "ok"), (401, "token_invalid"),
                                         (403, "token_invalid"), (500, "degraded")])
def test_probe_status_mapping(monkeypatch, code, status):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", _jwt(time.time() + 200 * 86400))
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(code))
    assert health.check_upstox()["status"] == status


def test_expiring_soon_warns(monkeypatch):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", _jwt(time.time() + 10 * 86400 + 60))
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(200))
    r = health.check_upstox()
    assert r["status"] == "expiring_soon" and r["days_until_expiry"] == 10


def test_network_error_is_unreachable_and_hides_token(monkeypatch):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", "opaque-secret-token")

    def boom(*a, **k):
        raise requests.ConnectionError("opaque-secret-token in url")

    monkeypatch.setattr(requests, "get", boom)
    r = health.check_upstox()
    assert r["status"] == "unreachable" and "opaque-secret-token" not in json.dumps(r)


def test_failure_is_logged_once_not_every_check(monkeypatch, caplog):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", _jwt(time.time() + 200 * 86400))
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(401))
    with caplog.at_level("ERROR", logger="stockpicker.health"):
        health.provider_health(refresh=True)
        health.provider_health(refresh=True)
    assert len([r for r in caplog.records if "token_invalid" in r.getMessage()]) == 1


def test_ready_reports_providers_but_stays_ready(monkeypatch):
    monkeypatch.setenv("UPSTOX_ANALYTICS_TOKEN", _jwt(time.time() + 200 * 86400))
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(401))
    with TestClient(app) as c:
        resp = c.get("/ready")
    assert resp.status_code == 200
    j = resp.json()
    assert j["status"] == "ready" and j["data_status"] == "degraded"
    assert j["providers"]["upstox"]["status"] == "token_invalid"


def test_admin_provider_health_requires_admin():
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "u", "account_type": "trial", "email": "x@y.z"}
    with TestClient(app) as c:
        assert c.get("/api/admin/provider-health").status_code == 403
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "a", "account_type": "admin"}
        assert c.get("/api/admin/provider-health?refresh=true").json()["status"] == "ok"
        assert "lines" in c.get("/api/admin/logs?lines=5").json()
    app.dependency_overrides.clear()
