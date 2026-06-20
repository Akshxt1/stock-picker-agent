"""
src/api/routes/market.py

All yfinance calls are:
  1. Wrapped in a timeout (won't hang forever)
  2. Cached for 15 minutes (subsequent loads are instant)
  3. Movers use ThreadPoolExecutor (parallel, not sequential)
"""

import datetime
import time
import threading
import concurrent.futures

from dotenv import load_dotenv, find_dotenv
from fastapi import APIRouter, Query, Depends, HTTPException
from src.api.routes.auth import get_current_user

load_dotenv(find_dotenv())

try:
    import yfinance as yf
    _YF = True
except ImportError:
    _YF = False

try:
    import pytz
    _PYTZ = True
except ImportError:
    _PYTZ = False

router = APIRouter()

# ── Simple TTL cache ──────────────────────────────────────────────────────────

_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()
_TTL = 900  # 15 minutes


def _get(key: str):
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
    if entry:
        val, ts = entry
        if time.time() - ts < _TTL:
            return val
    return None


def _set(key: str, val):
    with _CACHE_LOCK:
        _CACHE[key] = (val, time.time())


def _yf_safe(fn, timeout: float = 5.0, fallback=None):
    """Run a yfinance call with a hard timeout so one slow ticker can't stall everything."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return ex.submit(fn).result(timeout=timeout)
        except Exception:
            return fallback


# ── Market hours ──────────────────────────────────────────────────────────────

def _nse_is_open() -> bool:
    if not _PYTZ:
        return False
    now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
    if now.weekday() >= 5:
        return False
    open_t  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now <= close_t


def _nyse_is_open() -> bool:
    if not _PYTZ:
        return False
    now = datetime.datetime.now(pytz.timezone("America/New_York"))
    if now.weekday() >= 5:
        return False
    open_t  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_t = now.replace(hour=16, minute=0,  second=0, microsecond=0)
    return open_t <= now <= close_t


@router.get("/status")
def market_status():
    return {
        "NSE":  {"open": _nse_is_open(),  "tz": "Asia/Kolkata",     "hours": "09:15–15:30"},
        "NYSE": {"open": _nyse_is_open(), "tz": "America/New_York", "hours": "09:30–16:00"},
    }


# ── Live index values (for dashboard stat cards) ──────────────────────────────

_INDICES = [
    {"key": "NIFTY",  "symbol": "^NSEI",  "label": "NIFTY 50",  "currency": "INR"},
    {"key": "SENSEX", "symbol": "^BSESN", "label": "SENSEX",    "currency": "INR"},
    {"key": "SP500",  "symbol": "^GSPC",  "label": "S&P 500",   "currency": "USD"},
    {"key": "NASDAQ", "symbol": "^IXIC",  "label": "NASDAQ",    "currency": "USD"},
]


@router.get("/indices")
def market_indices(_user=Depends(get_current_user)):
    """Live values + day change for the major indices shown on the dashboard."""
    cache_key = "indices"
    cached = _get(cache_key)
    if cached:
        return cached

    def _one(ix: dict):
        t = yf.Ticker(ix["symbol"])
        price = prev = None
        # fast_info first (cheap); fall back to history (^BSESN/^IXIC often need it)
        try:
            info  = t.fast_info
            price = getattr(info, "last_price", None)
            prev  = getattr(info, "previous_close", None)
        except Exception:
            pass
        if price is None:
            try:
                hist = t.history(period="5d")["Close"].dropna()
                if len(hist):
                    price = float(hist.iloc[-1])
                    prev  = float(hist.iloc[-2]) if len(hist) > 1 else price
            except Exception:
                pass
        if price is None:
            return {"key": ix["key"], "label": ix["label"], "currency": ix["currency"],
                    "value": None, "change_pct": None}
        chg = ((price - prev) / prev * 100) if price and prev else None
        return {
            "key": ix["key"], "label": ix["label"], "currency": ix["currency"],
            "value": round(price, 2),
            "change_pct": round(chg, 2) if chg is not None else None,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        out = list(ex.map(lambda i: _yf_safe(lambda ix=i: _one(ix), timeout=5,
                                             fallback={**i, "value": None, "change_pct": None}), _INDICES))
    _set(cache_key, out)
    return out


# ── Ticker symbols — smart market switching ───────────────────────────────────

_INDIA_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "WIPRO.NS", "BHARTIARTL.NS", "SBIN.NS", "BAJFINANCE.NS", "HCLTECH.NS",
    "MARUTI.NS", "NTPC.NS", "AXISBANK.NS", "LT.NS", "SUNPHARMA.NS",
]
_US_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
    "BRK-B", "UNH", "LLY", "XOM", "MA",
]


@router.get("/active-symbols")
def active_symbols():
    """Returns which symbols + currency to show based on which markets are open."""
    nse  = _nse_is_open()
    nyse = _nyse_is_open()
    if nse and not nyse:
        return {"symbols": _INDIA_SYMBOLS, "market": "INDIA",  "currency": "INR"}
    if nyse and not nse:
        return {"symbols": _US_SYMBOLS,    "market": "US",     "currency": "USD"}
    # Both open or both closed — show both
    return {"symbols": _INDIA_SYMBOLS + _US_SYMBOLS, "market": "BOTH", "currency": "MIXED"}


# ── Live ticker tape ──────────────────────────────────────────────────────────

def _fetch_tick(sym: str):
    info  = yf.Ticker(sym).fast_info
    price = getattr(info, "last_price", None)
    prev  = getattr(info, "previous_close", None)
    chg   = ((price - prev) / prev * 100) if price and prev else None
    india = sym.endswith(".NS")
    return {
        "symbol":     sym,
        "display":    sym.replace(".NS", ""),
        "price":      round(price, 2) if price else None,
        "change_pct": round(chg, 2) if chg is not None else None,
        "currency":   "INR" if india else "USD",
    }


@router.get("/ticker")
def ticker_tape(
    symbols: str = Query(...),
    _user   = Depends(get_current_user),
):
    cache_key = f"ticker:{symbols}"
    cached = _get(cache_key)
    if cached:
        return cached

    tickers = [s.strip() for s in symbols.split(",") if s.strip()][:25]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(
            lambda s: _yf_safe(lambda sym=s: _fetch_tick(sym), timeout=5),
            tickers
        ))
    out = [r for r in results if r and r["price"] is not None]
    _set(cache_key, out)
    return out


# ── News ──────────────────────────────────────────────────────────────────────

_NEWS_TICKERS = {"INDIA": "^NSEI", "US": "^GSPC"}


def _finnhub_general_news(limit: int = 10) -> list:
    """Multi-source general market news from Finnhub (fixes the single-source feel)."""
    import os, requests
    key = os.getenv("FINNHUB_API_KEY")
    if not key:
        return []
    try:
        resp = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": key}, timeout=8,
        )
        resp.raise_for_status()
        out = []
        for it in resp.json()[:limit]:
            headline = it.get("headline")
            if not headline:
                continue
            ts = it.get("datetime")
            published = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
            out.append({
                "title": headline,
                "publisher": it.get("source") or "",
                "link": it.get("url") or "",
                "published": published,
            })
        return out
    except Exception:
        return []


def _yf_index_news(sym: str, limit: int = 10) -> list:
    def _fetch():
        raw = yf.Ticker(sym).news or []
        out = []
        for item in raw[:limit]:
            content  = item.get("content", {})
            title    = content.get("title") or item.get("title", "")
            provider = (content.get("provider") or {}).get("displayName", "") or item.get("publisher", "")
            link     = (content.get("canonicalUrl") or {}).get("url", "") or item.get("link", "")
            pub_date = content.get("pubDate", "") or ""
            if title:
                out.append({
                    "title": title, "publisher": provider,
                    "link": link, "published": pub_date[:10] if pub_date else "",
                })
        return out
    return _yf_safe(_fetch, timeout=8, fallback=[]) or []


@router.get("/news")
def market_news(market: str = Query("INDIA")):
    cache_key = f"news:{market}"
    cached = _get(cache_key)
    if cached is not None:
        return cached

    m = market.upper()
    # US / Both → Finnhub general (multi-source, fresh). India → yfinance NIFTY feed.
    if m == "US":
        result = _finnhub_general_news() or _yf_index_news("^GSPC")
    elif m == "BOTH":
        result = (_yf_index_news("^NSEI", 6) + _finnhub_general_news(6))
    else:
        result = _yf_index_news("^NSEI")

    _set(cache_key, result)
    return result


# ── Movers (parallel fetch) ───────────────────────────────────────────────────

_MOVER_UNIVERSE = {
    "INDIA": _INDIA_SYMBOLS + [
        "KOTAKBANK.NS", "POWERGRID.NS", "TITAN.NS", "NESTLEIND.NS", "ULTRACEMCO.NS",
    ],
    "US": _US_SYMBOLS + [
        "GOOGL", "AMD", "INTC", "CRM", "PYPL",
    ],
}


@router.get("/movers")
def market_movers(market: str = Query("INDIA")):
    cache_key = f"movers:{market}"
    cached = _get(cache_key)
    if cached:
        return cached

    m = market.upper()
    if m == "BOTH":
        universe = _MOVER_UNIVERSE["INDIA"] + _MOVER_UNIVERSE["US"]
    else:
        universe = _MOVER_UNIVERSE.get(m, _MOVER_UNIVERSE["INDIA"])

    def _one(sym: str):
        info  = yf.Ticker(sym).fast_info
        price = getattr(info, "last_price", None)
        prev  = getattr(info, "previous_close", None)
        if price and prev:
            return {
                "symbol":     sym,
                "display":    sym.replace(".NS", ""),
                "price":      round(price, 2),
                "change_pct": round((price - prev) / prev * 100, 2),
                "currency":   "INR" if sym.endswith(".NS") else "USD",
            }
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(lambda s: _yf_safe(lambda sym=s: _one(sym), timeout=5), universe))

    movers = sorted([r for r in results if r], key=lambda x: x["change_pct"], reverse=True)
    out = {
        "gainers": movers[:5],
        "losers":  list(reversed(movers[-5:])),
    }
    _set(cache_key, out)
    return out


# ── Live FX rate ──────────────────────────────────────────────────────────────

_FX_SYMBOLS = {
    "USDINR": "USDINR=X",
    "INRUSD": "INR=X",   # USD per 1 INR is 1/USDINR; we fetch USDINR and invert
}


@router.get("/fx")
def fx_rate(pair: str = Query("USDINR")):
    """Live FX rate. Returns the rate for `pair` (default USDINR — INR per 1 USD).

    Used by the portfolio 'All' tab to convert between ₹ and $ with real, not
    estimated, numbers. Cached briefly so it stays live without hammering yfinance.
    """
    pair = pair.upper()
    cache_key = f"fx:{pair}"
    cached = _get(cache_key)
    if cached:
        return cached

    def _fetch_usdinr() -> float:
        from src.providers import market_data_client
        q = market_data_client().quote("USDINR=X", ttl_seconds=300).data
        return float(q["price"])

    rate = _yf_safe(_fetch_usdinr, timeout=6)
    if not rate:
        raise HTTPException(status_code=502, detail="FX rate unavailable")

    if pair == "INRUSD":
        value = round(1.0 / rate, 6)
    else:  # USDINR (default)
        value = round(rate, 4)

    out = {"pair": pair, "rate": value, "usd_inr": round(rate, 4)}
    _set(cache_key, out)
    return out
