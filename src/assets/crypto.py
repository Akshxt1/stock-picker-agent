"""Crypto data via CoinGecko, with yfinance as a fallback for major coins.

CoinGecko's public API is rate limited (~30 calls/min) and returns at most one
year of daily history, so everything is cached and quotes are fetched in batches.
Set COINGECKO_API_KEY (a free "demo" key) for higher, steadier limits.
"""

import os

import pandas as pd

from src.assets.http import KeyedLock, UpstreamError, build_session, get_json
from src.assets.types import period_days
from src.providers.cache import get_cached, set_cached

BASE = "https://api.coingecko.com/api/v3"
MAX_DAYS = 365  # public-API limit for daily history

# CoinGecko id -> Yahoo ticker, used only when CoinGecko is unavailable.
YF_FALLBACK = {
    "bitcoin": "BTC-USD", "ethereum": "ETH-USD", "tether": "USDT-USD", "binancecoin": "BNB-USD",
    "solana": "SOL-USD", "ripple": "XRP-USD", "usd-coin": "USDC-USD", "cardano": "ADA-USD",
    "dogecoin": "DOGE-USD", "tron": "TRX-USD", "avalanche-2": "AVAX-USD", "chainlink": "LINK-USD",
    "polkadot": "DOT-USD", "litecoin": "LTC-USD", "matic-network": "MATIC-USD",
}

_session = build_session()
_flight = KeyedLock()


def _headers() -> dict:
    key = os.getenv("COINGECKO_API_KEY")
    return {"x-cg-demo-api-key": key} if key else {}


def _get(path: str, params: dict | None = None):
    return get_json(_session, f"{BASE}{path}", params=params or {}, headers=_headers())


def search(query: str, limit: int = 10) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    key = f"crypto:search:{q}"
    with _flight(key):
        cached = get_cached(key)
        if cached is None:
            cached = {"coins": _get("/search", {"query": q}).get("coins", [])[:25]}
            set_cached(key, "coingecko", cached, 3600)
    return [{
        "symbol": f"CRYPTO:{c['id']}",
        "ticker": c.get("symbol", "").upper(),
        "name": c.get("name"),
        "asset_class": "CRYPTO",
        "market": "CRYPTO",
        "rank": c.get("market_cap_rank"),
    } for c in cached["coins"][:limit]]


def coin_name(coin_id: str) -> str | None:
    """Display name for a coin id, via the (cached) search endpoint."""
    try:
        for hit in search(coin_id, limit=25):
            if hit["symbol"] == f"CRYPTO:{coin_id}":
                return hit["name"]
    except UpstreamError:
        pass
    return None


def quotes(coin_ids: list[str], vs: str = "usd", ttl: int = 60) -> dict[str, dict]:
    """Batch quote for many coins in one upstream call. Missing coins are omitted."""
    vs = vs.lower()
    ids = sorted({c for c in coin_ids if c})
    out: dict[str, dict] = {}
    missing: list[str] = []
    for cid in ids:
        hit = get_cached(f"crypto:quote:{cid}:{vs}")
        if hit:
            out[cid] = hit
        else:
            missing.append(cid)
    if not missing:
        return out

    with _flight("quotes:" + ",".join(missing) + vs):
        return _fetch_quotes(missing, vs, ttl, out)


def _fetch_quotes(missing: list[str], vs: str, ttl: int, out: dict[str, dict]) -> dict[str, dict]:
    # Another request may have filled the cache while we waited for the lock.
    still = []
    for cid in missing:
        hit = get_cached(f"crypto:quote:{cid}:{vs}")
        if hit:
            out[cid] = hit
        else:
            still.append(cid)
    missing = still
    if not missing:
        return out

    try:
        data = _get("/simple/price", {
            "ids": ",".join(missing), "vs_currencies": vs,
            "include_24hr_change": "true", "include_market_cap": "true",
            "include_24hr_vol": "true",
        })
    except UpstreamError:
        data = {}
        for cid in missing:                       # fall back per coin to Yahoo
            q = _yf_quote(cid, vs)
            if q:
                data[cid] = q
                out[cid] = q
        return out

    for cid in missing:
        row = data.get(cid)
        if not row or vs not in row:
            continue
        q = {
            "price": float(row[vs]),
            "day_change_pct": row.get(f"{vs}_24h_change"),
            "market_cap": row.get(f"{vs}_market_cap"),
            "volume_24h": row.get(f"{vs}_24h_vol"),
            "currency": vs.upper(),
            "source": "coingecko",
        }
        set_cached(f"crypto:quote:{cid}:{vs}", "coingecko", q, ttl)
        out[cid] = q
    return out


def quote(coin_id: str, vs: str = "usd") -> dict:
    q = quotes([coin_id], vs).get(coin_id)
    if not q:
        raise UpstreamError(f"No quote for crypto '{coin_id}'")
    return q


def history(coin_id: str, period: str = "6mo", vs: str = "usd") -> pd.DataFrame:
    """Daily Close/Volume. Periods beyond 1y use Yahoo (known coins) or are capped at 1y."""
    days = period_days(period)
    if days > MAX_DAYS and coin_id in YF_FALLBACK:
        df = _yf_history(coin_id, period)
        if df is not None:
            return df
    days = min(days, MAX_DAYS)

    key = f"crypto:history:{coin_id}:{vs}:{days}"
    with _flight(key):
        cached = get_cached(key)
        if cached is None:
            try:
                raw = _get(f"/coins/{coin_id}/market_chart",
                           {"vs_currency": vs, "days": days, "interval": "daily"})
                cached = {"prices": raw.get("prices", []), "volumes": raw.get("total_volumes", [])}
                if cached["prices"]:
                    set_cached(key, "coingecko", cached, 3600)
            except UpstreamError:
                df = _yf_history(coin_id, period)
                if df is not None:
                    return df
                raise
    if not cached["prices"]:
        raise UpstreamError(f"No history for crypto '{coin_id}'")
    df = pd.DataFrame(cached["prices"], columns=["ts", "Close"])
    df.index = pd.to_datetime(df.pop("ts"), unit="ms").dt.normalize()
    vols = pd.Series({pd.Timestamp(t, unit="ms").normalize(): v for t, v in cached["volumes"]})
    df["Volume"] = vols.reindex(df.index).values
    return df[~df.index.duplicated(keep="last")]


# ── Yahoo fallback ────────────────────────────────────────────────────────────

def _yf_history(coin_id: str, period: str) -> pd.DataFrame | None:
    ticker = YF_FALLBACK.get(coin_id)
    if not ticker:
        return None
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(period=period if period != "max" else "10y")
        if df.empty:
            return None
        df.index = df.index.tz_localize(None).normalize()
        return df[["Close", "Volume"]]
    except Exception:
        return None


def _yf_quote(coin_id: str, vs: str) -> dict | None:
    if vs != "usd":
        return None
    df = _yf_history(coin_id, "5d")
    if df is None or df.empty:
        return None
    close = df["Close"].dropna()
    price = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) > 1 else price
    return {"price": price, "day_change_pct": (price - prev) / prev * 100 if prev else 0.0,
            "market_cap": None, "volume_24h": float(df["Volume"].iloc[-1]),
            "currency": "USD", "source": "yfinance"}
