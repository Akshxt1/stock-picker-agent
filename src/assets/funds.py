"""Mutual funds.

India: AMFI scheme data via the free mfapi.in service (NAV is published once per
business day, so it is cached for hours). US funds and ETFs go through the
existing multi-provider market-data client like any other US ticker.
"""

import pandas as pd

from src.assets.http import KeyedLock, UpstreamError, build_session, get_json
from src.assets.types import period_days
from src.providers.cache import get_cached, set_cached

MFAPI = "https://api.mfapi.in/mf"

_session = build_session()
_flight = KeyedLock()


# ── India (mfapi.in) ──────────────────────────────────────────────────────────

def search_india(query: str, limit: int = 10) -> list[dict]:
    q = query.strip().lower()
    if len(q) < 2:
        return []
    key = f"mf:search:{q}"
    cached = get_cached(key)
    if cached is None:
        cached = {"schemes": get_json(_session, f"{MFAPI}/search", params={"q": q})}
        set_cached(key, "mfapi", cached, 6 * 3600)
    return [{
        "symbol": f"MF:{s['schemeCode']}",
        "ticker": str(s["schemeCode"]),
        "name": s.get("schemeName"),
        "asset_class": "FUND",
        "market": "INDIA",
    } for s in cached["schemes"][:limit]]


def _scheme(code: str) -> dict:
    """Full scheme payload (meta + entire NAV history), cached."""
    key = f"mf:scheme:{code}"
    with _flight(key):
        cached = get_cached(key)
        if cached is None:
            raw = get_json(_session, f"{MFAPI}/{code}")
            if raw.get("status") == "ERROR" or not raw.get("data"):
                raise UpstreamError(f"Unknown mutual fund scheme {code}")
            # Keep it compact: newest-first [[dd-mm-yyyy, nav], ...]
            cached = {"meta": raw.get("meta", {}), "data": [[d["date"], d["nav"]] for d in raw["data"]]}
            set_cached(key, "mfapi", cached, 6 * 3600)
        return cached


def india_meta(code: str) -> dict:
    m = _scheme(code)["meta"]
    return {
        "name": m.get("scheme_name"), "fund_house": m.get("fund_house"),
        "category": m.get("scheme_category"), "type": m.get("scheme_type"),
        "isin": m.get("isin_growth"),
    }


def india_history(code: str, period: str = "1y") -> pd.DataFrame:
    rows = _scheme(code)["data"]
    df = pd.DataFrame(rows, columns=["date", "Close"])
    df.index = pd.to_datetime(df.pop("date"), format="%d-%m-%Y")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna().sort_index()
    if period != "max":
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=period_days(period))]
    return df


def india_quote(code: str) -> dict:
    df = india_history(code, "1mo")
    if df.empty:
        raise UpstreamError(f"No NAV for scheme {code}")
    nav = float(df["Close"].iloc[-1])
    prev = float(df["Close"].iloc[-2]) if len(df) > 1 else nav
    return {
        "price": nav, "previous_close": prev,
        "day_change_pct": (nav - prev) / prev * 100 if prev else 0.0,
        "as_of": df.index[-1].strftime("%Y-%m-%d"), "currency": "INR", "source": "mfapi",
    }


# ── US funds / ETFs ───────────────────────────────────────────────────────────

def search_us(query: str, limit: int = 10) -> list[dict]:
    """Search US mutual funds and ETFs by name/ticker via Yahoo."""
    q = query.strip()
    if len(q) < 2:
        return []
    key = f"usfund:search:{q.lower()}"
    cached = get_cached(key)
    if cached is None:
        try:
            import yfinance as yf
            quotes = yf.Search(q, max_results=25).quotes
        except Exception as e:
            raise UpstreamError(f"US fund search failed: {e}") from e
        cached = {"quotes": [
            {"symbol": x.get("symbol"), "name": x.get("longname") or x.get("shortname"),
             "type": x.get("quoteType")}
            for x in quotes if x.get("quoteType") in ("ETF", "MUTUALFUND") and x.get("symbol")
        ]}
        set_cached(key, "yahoo", cached, 3600)
    return [{
        "symbol": x["symbol"], "ticker": x["symbol"], "name": x["name"],
        "asset_class": "FUND", "market": "US", "fund_type": x["type"],
    } for x in cached["quotes"][:limit]]
