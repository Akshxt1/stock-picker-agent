import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.auth import get_current_user
from src.assets import crypto, funds, service
from src.assets.http import UpstreamError
from src.assets.metrics import compute_metrics
from src.assets.types import AssetClass, parse_symbol
from src.database import models


# ── symbols ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sym,cls,market,cur,pid", [
    ("RELIANCE.ns", AssetClass.EQUITY, "INDIA", "INR", "RELIANCE.NS"),
    ("aapl", AssetClass.EQUITY, "US", "USD", "AAPL"),
    ("CRYPTO:Bitcoin", AssetClass.CRYPTO, "CRYPTO", "USD", "bitcoin"),
    ("MF:118989", AssetClass.FUND, "INDIA", "INR", "118989"),
])
def test_parse_symbol(sym, cls, market, cur, pid):
    ref = parse_symbol(sym)
    assert (ref.asset_class, ref.market, ref.currency, ref.provider_id) == (cls, market, cur, pid)


def test_us_fund_needs_explicit_class():
    assert parse_symbol("VTSAX").asset_class == AssetClass.EQUITY
    assert parse_symbol("VTSAX", "FUND").asset_class == AssetClass.FUND


@pytest.mark.parametrize("bad", ["", "MF:abc", "CRYPTO:", "CRYPTO:bit coin", "FOO:1", "A B", "x;drop"])
def test_parse_symbol_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_symbol(bad)


# ── metrics ───────────────────────────────────────────────────────────────────

def _series(values, start="2025-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"))


def test_metrics_drawdown_and_return():
    m = compute_metrics(_series([100, 120, 90, 110]))
    assert m["total_return"] == pytest.approx(0.10)
    assert m["max_drawdown"] == pytest.approx(-0.25)          # 120 -> 90
    assert m["current_drawdown"] == pytest.approx(110 / 120 - 1, abs=1e-4)
    assert m["cagr"] is None                                   # < 180 days: too noisy to report


def test_metrics_handles_garbage_and_short_series():
    assert compute_metrics(_series([100]))["observations"] == 1
    m = compute_metrics(_series([100, float("nan"), -5, 110]))
    assert m["observations"] == 2
    assert all(v is None or math.isfinite(v) for v in [m["sharpe"], m["annual_volatility"]])


def test_crypto_annualises_with_365_days():
    flat_then_jump = _series([100, 101] * 40)
    a = compute_metrics(flat_then_jump, "EQUITY")["annual_volatility"]
    b = compute_metrics(flat_then_jump, "CRYPTO")["annual_volatility"]
    assert b / a == pytest.approx(math.sqrt(365 / 252), rel=1e-3)


# ── crypto adapter (HTTP mocked) ──────────────────────────────────────────────

def test_crypto_quotes_batches_into_one_call(monkeypatch):
    calls = []

    def fake_get(path, params=None):
        calls.append((path, params))
        return {"coin-a": {"usd": 2.0, "usd_24h_change": 1.5, "usd_market_cap": 10, "usd_24h_vol": 5},
                "coin-b": {"usd": 3.0}}

    monkeypatch.setattr(crypto, "_get", fake_get)
    out = crypto.quotes(["coin-a", "coin-b", "coin-missing"])
    assert len(calls) == 1 and calls[0][1]["ids"] == "coin-a,coin-b,coin-missing"
    assert out["coin-a"]["price"] == 2.0 and out["coin-b"]["price"] == 3.0
    assert "coin-missing" not in out
    crypto.quotes(["coin-a"])                                  # served from cache
    assert len(calls) == 1


def test_crypto_history_parses_market_chart(monkeypatch):
    day = 86_400_000
    monkeypatch.setattr(crypto, "_get", lambda path, params=None: {
        "prices": [[1_700_000_000_000 + i * day, 100 + i] for i in range(5)],
        "total_volumes": [[1_700_000_000_000 + i * day, 1000] for i in range(5)],
    })
    df = crypto.history("coin-hist", "1mo")
    assert list(df["Close"]) == [100, 101, 102, 103, 104]
    assert df["Volume"].notna().all()


def test_crypto_quote_failure_without_fallback_raises(monkeypatch):
    def boom(*a, **k):
        raise UpstreamError("down")
    monkeypatch.setattr(crypto, "_get", boom)
    with pytest.raises(UpstreamError):
        crypto.quote("unknown-coin")


# ── india funds adapter (HTTP mocked) ─────────────────────────────────────────

def test_india_fund_history_and_quote(monkeypatch):
    monkeypatch.setattr(funds, "get_json", lambda *a, **k: {
        "status": "SUCCESS",
        "meta": {"scheme_name": "Test Fund", "fund_house": "X MF", "scheme_category": "Equity"},
        "data": [{"date": "03-01-2025", "nav": "12.0"}, {"date": "02-01-2025", "nav": "10.0"},
                 {"date": "01-01-2025", "nav": "11.0"}],
    })
    df = funds.india_history("999001", "max")
    assert list(df["Close"]) == [11.0, 10.0, 12.0]            # sorted ascending
    q = funds.india_quote("999001")
    assert q["price"] == 12.0 and q["previous_close"] == 10.0 and q["currency"] == "INR"
    assert funds.india_meta("999001")["fund_house"] == "X MF"


def test_unknown_scheme_raises(monkeypatch):
    monkeypatch.setattr(funds, "get_json", lambda *a, **k: {"status": "ERROR", "data": []})
    with pytest.raises(UpstreamError):
        funds.india_quote("999002")


def test_search_degrades_when_one_source_fails(monkeypatch):
    def boom(*a, **k):
        raise UpstreamError("down")
    monkeypatch.setattr(crypto, "search", boom)
    monkeypatch.setattr(funds, "search_india", lambda q, n: [{"symbol": "MF:1"}])
    monkeypatch.setattr(funds, "search_us", boom)
    assert service.search("x", limit=5) == [{"symbol": "MF:1"}]


# ── routes ────────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "u1", "name": "user", "account_type": "trial"}
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_routes_validate_input(client):
    assert client.get("/api/assets/quote?symbol=MF:abc").status_code == 400
    assert client.get("/api/assets/history?symbol=CRYPTO:bitcoin&period=forever").status_code == 400
    assert client.get("/api/assets/search?q=x&asset_class=STOCK").status_code == 422


def test_metrics_route(client, monkeypatch):
    monkeypatch.setattr(service, "history", lambda ref, period: pd.DataFrame(
        {"Close": [100.0, 110.0, 99.0]}, index=pd.date_range("2025-01-01", periods=3)))
    body = client.get("/api/assets/metrics?symbol=CRYPTO:bitcoin&period=1y").json()
    assert body["asset_class"] == "CRYPTO" and body["max_drawdown"] == pytest.approx(-0.1)


def test_upstream_failure_is_502_without_internals(client, monkeypatch):
    def boom(ref):
        raise UpstreamError("https://secret-host/?key=abc: timeout")
    monkeypatch.setattr(service, "quote", boom)
    r = client.get("/api/assets/quote?symbol=CRYPTO:bitcoin")
    assert r.status_code == 502 and "secret-host" not in r.text


# ── portfolio ─────────────────────────────────────────────────────────────────

def test_portfolio_stores_asset_class():
    models.add_portfolio_position("u1", "crypto:Bitcoin", 0.5, 60000)
    models.add_portfolio_position("u1", "MF:118989", 100, 200, name="  HDFC Mid Cap  ")
    models.add_portfolio_position("u1", "vtsax", 3, 100, asset_class="FUND")
    models.add_portfolio_position("u1", "TCS.NS", 2, 3500)
    by_ticker = {h["ticker"]: h for h in models.get_portfolio("u1")}
    assert by_ticker["CRYPTO:bitcoin"]["asset_class"] == "CRYPTO"
    assert by_ticker["MF:118989"]["asset_class"] == "FUND"
    assert by_ticker["MF:118989"]["name"] == "HDFC Mid Cap" and by_ticker["TCS.NS"]["name"] is None
    assert by_ticker["VTSAX"]["asset_class"] == "FUND"
    assert by_ticker["TCS.NS"]["asset_class"] == "EQUITY"
    with pytest.raises(ValueError):
        models.add_portfolio_position("u1", "MF:xyz", 1, 1)
    with models.Session() as s:
        s.query(models.Portfolio).delete()
        s.commit()


# ── concurrency / names ───────────────────────────────────────────────────────

def test_concurrent_history_requests_make_one_upstream_call(monkeypatch):
    import threading
    import time

    calls = []
    day = 86_400_000

    def slow_get(path, params=None):
        calls.append(path)
        time.sleep(0.2)
        return {"prices": [[1_700_000_000_000 + i * day, 10 + i] for i in range(3)], "total_volumes": []}

    monkeypatch.setattr(crypto, "_get", slow_get)
    threads = [threading.Thread(target=crypto.history, args=("coin-flight", "1mo")) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(calls) == 1


def test_crypto_info_includes_coin_name(monkeypatch):
    monkeypatch.setattr(crypto, "_get", lambda path, params=None: {"coins": [
        {"id": "coin-named", "name": "Named Coin", "symbol": "NMC", "market_cap_rank": 9}]})
    assert service.info(parse_symbol("CRYPTO:coin-named"))["name"] == "Named Coin"


def test_rolling_one_year_window_with_365_points():
    s = _series([100 + i for i in range(365)])
    assert compute_metrics(s, "CRYPTO")["rolling_returns"]["1y"] is not None
