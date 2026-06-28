"""
src/api/routes/market.py

India data → Upstox (primary, batch-capable, no rate limits).
US data    → yfinance / Finnhub (unchanged).
"""

import datetime
import logging
import time
import threading
import concurrent.futures

import requests as _requests
from dotenv import load_dotenv, find_dotenv
from fastapi import APIRouter, Query, HTTPException

# NOTE: Market-data endpoints below are intentionally PUBLIC (non-sensitive,
# cached) so the guest dashboard can render indices/news/movers/heatmap.

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

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


_NEWS_TTL = 180  # 3 minutes for news endpoints


def _get(key: str):
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
    if entry:
        val, ts = entry
        ttl = _NEWS_TTL if key.startswith("news:") else _TTL
        if time.time() - ts < ttl:
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
    # ── India ─────────────────────────────────────────────────────────────────
    {"key": "NIFTY",     "symbol": "^NSEI",    "label": "NIFTY 50",       "currency": "INR",
     "upstox_key": "NSE_INDEX|Nifty 50",      "group": "india"},
    {"key": "SENSEX",    "symbol": "^BSESN",   "label": "SENSEX",         "currency": "INR",
     "upstox_key": "BSE_INDEX|SENSEX",         "group": "india"},
    {"key": "BANKNIFTY", "symbol": "^NSEBANK", "label": "BANK NIFTY",     "currency": "INR",
     "upstox_key": "NSE_INDEX|Nifty Bank",     "group": "india"},
    {"key": "NIFTYIT",   "symbol": "^CNXIT",   "label": "NIFTY IT",       "currency": "INR",
     "upstox_key": "NSE_INDEX|Nifty IT",       "group": "india"},
    {"key": "MIDCAP",    "symbol": "^NSMIDCP", "label": "NIFTY MIDCAP",   "currency": "INR",
     "upstox_key": "NSE_INDEX|NIFTY Midcap 100","group": "india"},
    # ── US ────────────────────────────────────────────────────────────────────
    {"key": "SP500",  "symbol": "^GSPC",  "label": "S&P 500",   "currency": "USD", "group": "us"},
    {"key": "NASDAQ", "symbol": "^IXIC",  "label": "NASDAQ",    "currency": "USD", "group": "us"},
]


def _upstox_index(upstox_key: str) -> dict | None:
    """Fetch a single index quote from Upstox (no instrument mapping needed)."""
    import os
    token = os.getenv("UPSTOX_ANALYTICS_TOKEN", "")
    if not token:
        return None
    try:
        r = _requests.get(
            "https://api.upstox.com/v2/market-quote/quotes",
            params={"instrument_key": upstox_key},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=8,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("status") != "success":
            return None
        q = next(iter((body.get("data") or {}).values()), None)
        if not q:
            return None
        price = float(q.get("last_price") or 0)
        if not price:
            return None
        ohlc  = q.get("ohlc") or {}
        prev  = float(ohlc.get("close") or price)
        net   = float(q.get("net_change") or (price - prev))
        chg   = (net / prev * 100) if prev else 0.0
        return {"price": price, "prev": prev, "chg": chg}
    except Exception as exc:
        logger.debug("Upstox index %s: %s", upstox_key, exc)
        return None


@router.get("/indices")
def market_indices():
    """Live values + day change for the major indices shown on the dashboard."""
    cache_key = "indices"
    cached = _get(cache_key)
    if cached:
        return cached

    def _one(ix: dict):
        # India indices — try Upstox first
        upstox_key = ix.get("upstox_key")
        group = ix.get("group", "india")
        if upstox_key:
            data = _upstox_index(upstox_key)
            if data:
                return {
                    "key":        ix["key"],
                    "label":      ix["label"],
                    "currency":   ix["currency"],
                    "group":      group,
                    "value":      round(data["price"], 2),
                    "change_pct": round(data["chg"], 2),
                }

        # US indices (and India fallback) — yfinance
        t = yf.Ticker(ix["symbol"])
        price = prev = None
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
                    "group": group, "value": None, "change_pct": None}
        chg = ((price - prev) / prev * 100) if price and prev else None
        return {
            "key":        ix["key"],
            "label":      ix["label"],
            "currency":   ix["currency"],
            "group":      group,
            "value":      round(price, 2),
            "change_pct": round(chg, 2) if chg is not None else None,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as ex:
        out = list(ex.map(
            lambda i: _yf_safe(lambda ix=i: _one(ix), timeout=10,
                               fallback={**i, "value": None, "change_pct": None}),
            _INDICES,
        ))
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
    india = sym.endswith((".NS", ".BO"))
    display = sym.replace(".NS", "").replace(".BO", "")

    # India — use Upstox
    if india:
        try:
            from src.providers import market_data_client
            upstox = market_data_client().providers.get("upstox")
            if upstox and upstox.available():
                q = upstox.quote(sym)
                return {
                    "symbol":     sym,
                    "display":    display,
                    "price":      round(q["price"], 2),
                    "change_pct": q["day_change_pct"],
                    "currency":   "INR",
                }
        except Exception as exc:
            logger.debug("Upstox tick %s: %s", sym, exc)

    # US (or India fallback) — yfinance
    info  = yf.Ticker(sym).fast_info
    price = getattr(info, "last_price", None)
    prev  = getattr(info, "previous_close", None)
    chg   = ((price - prev) / prev * 100) if price and prev else None
    return {
        "symbol":     sym,
        "display":    display,
        "price":      round(price, 2) if price else None,
        "change_pct": round(chg, 2) if chg is not None else None,
        "currency":   "INR" if india else "USD",
    }


@router.get("/ticker")
def ticker_tape(
    symbols: str = Query(...),
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


def _parse_rss_feed(url: str, default_publisher: str = "", limit: int = 20) -> list:
    """Parse an RSS feed and return normalised news items."""
    import urllib.parse
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime

    try:
        resp = requests.get(
            url, timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (compatible; StockPickerBot/1.0)"},
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            return []
        out = []
        for item in (channel.findall("item") or [])[:limit]:
            title = item.findtext("title", "").strip()
            link  = item.findtext("link", "") or ""
            pub_date = item.findtext("pubDate", "")
            source_el = item.find("source")
            publisher = (source_el.text if source_el is not None else "") or default_publisher
            if not title:
                continue
            published = ""
            if pub_date:
                try:
                    published = parsedate_to_datetime(pub_date).strftime("%Y-%m-%d")
                except Exception:
                    published = pub_date[:10]
            out.append({"title": title, "publisher": publisher, "link": link, "published": published})
        return out
    except Exception:
        return []


def _google_news_rss(query: str, limit: int = 10) -> list:
    """Fetch latest headlines from Google News RSS."""
    import urllib.parse
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
    return _parse_rss_feed(url, limit=limit)


def _india_news_multi(limit: int = 12) -> list:
    """Fetch fresh India market news from multiple RSS sources in parallel, sorted newest-first."""
    feeds = [
        ("https://economictimes.indiatimes.com/markets/rss.cms",                      "Economic Times"),
        ("https://www.moneycontrol.com/rss/latestnews.xml",                            "Moneycontrol"),
        ("https://www.business-standard.com/rss/markets-106.rss",                     "Business Standard"),
        ("https://www.livemint.com/rss/markets",                                       "Livemint"),
        ("https://news.google.com/rss/search?q=NSE+Nifty+Sensex+India+stock&hl=en-IN&gl=IN&ceid=IN:en", ""),
    ]

    all_items: list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(feeds)) as ex:
        futures = [ex.submit(_parse_rss_feed, url, pub) for url, pub in feeds]
        for fut in concurrent.futures.as_completed(futures, timeout=12):
            try:
                all_items.extend(fut.result())
            except Exception:
                pass

    # Sort newest-first; items without a date go to the bottom
    all_items.sort(key=lambda x: x.get("published", ""), reverse=True)

    # Deduplicate by first 50 chars of title (case-insensitive)
    seen: set = set()
    unique: list = []
    for item in all_items:
        key = item["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique[:limit]


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
    if m == "US":
        result = _finnhub_general_news() or _yf_index_news("^GSPC")
    elif m == "BOTH":
        india = _india_news_multi(6)
        us    = _finnhub_general_news(6) or _yf_index_news("^GSPC", 6)
        result = india + us or _yf_index_news("^NSEI", 6) + _yf_index_news("^GSPC", 6)
    else:  # INDIA
        result = _india_news_multi(12) or _yf_index_news("^NSEI")

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

    india_syms = [s for s in universe if s.endswith((".NS", ".BO"))]
    us_syms    = [s for s in universe if not s.endswith((".NS", ".BO"))]
    all_quotes: list[dict] = []

    # India — single Upstox batch call
    if india_syms:
        fetched: set[str] = set()
        try:
            from src.providers import market_data_client
            upstox = market_data_client().providers.get("upstox")
            if upstox and upstox.available():
                batch = upstox.batch_quotes(india_syms)
                for q in batch:
                    ticker = q["ticker"]
                    if q.get("price") is not None:
                        all_quotes.append({
                            "symbol":     ticker,
                            "display":    ticker.replace(".NS", "").replace(".BO", ""),
                            "price":      round(q["price"], 2),
                            "change_pct": q["day_change_pct"],
                            "currency":   "INR",
                        })
                        fetched.add(ticker)
        except Exception as exc:
            logger.warning("Upstox movers batch failed: %s", exc)
            fetched = set()

        # yfinance fallback for any India tickers Upstox missed
        missed = [s for s in india_syms if s not in fetched]
        if missed:
            def _yf_india(sym: str):
                info  = yf.Ticker(sym).fast_info
                price = getattr(info, "last_price", None)
                prev  = getattr(info, "previous_close", None)
                if price and prev:
                    return {
                        "symbol": sym, "display": sym.replace(".NS", ""),
                        "price": round(price, 2),
                        "change_pct": round((price - prev) / prev * 100, 2),
                        "currency": "INR",
                    }
                return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                fb = list(ex.map(lambda s: _yf_safe(lambda sym=s: _yf_india(sym), timeout=5), missed))
            all_quotes.extend(r for r in fb if r)

    # US — yfinance / Finnhub via existing path
    if us_syms:
        def _yf_us(sym: str):
            info  = yf.Ticker(sym).fast_info
            price = getattr(info, "last_price", None)
            prev  = getattr(info, "previous_close", None)
            if price and prev:
                return {
                    "symbol": sym, "display": sym,
                    "price": round(price, 2),
                    "change_pct": round((price - prev) / prev * 100, 2),
                    "currency": "USD",
                }
            return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            us_res = list(ex.map(lambda s: _yf_safe(lambda sym=s: _yf_us(sym), timeout=5), us_syms))
        all_quotes.extend(r for r in us_res if r)

    movers = sorted(all_quotes, key=lambda x: x["change_pct"], reverse=True)
    out = {
        "gainers": movers[:5],
        "losers":  list(reversed(movers[-5:])),
    }
    _set(cache_key, out)
    return out


# ── Market holidays ──────────────────────────────────────────────────────────

@router.get("/holidays")
def market_holidays(exchange: str = Query("NSE")):
    """Upcoming market holidays for NSE or BSE (current year, today onwards)."""
    cache_key = f"holidays:{exchange}"
    cached = _get(cache_key)
    if cached is not None:
        return cached
    try:
        from src.providers import market_data_client
        upstox = market_data_client().providers.get("upstox")
        if upstox and upstox.available():
            result = upstox.market_holidays(exchange.upper())
            _set(cache_key, result)
            return result
    except Exception as exc:
        logger.debug("Holidays fetch failed: %s", exc)
    return []


# ── FII / DII institutional flows (India) ────────────────────────────────────

_NSE_HOME = "https://www.nseindia.com"
_NSE_FII_DII = "https://www.nseindia.com/api/fiidiiTradeReact"
_NSE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/reports/fii-dii",
}


def _fetch_fii_dii() -> list[dict]:
    """Daily FII/DII cash-market flows from NSE. Needs a session cookie first."""
    try:
        sess = _requests.Session()
        sess.headers.update(_NSE_HEADERS)
        # Prime cookies from the homepage / report page
        sess.get(_NSE_HOME, timeout=8)
        sess.get("https://www.nseindia.com/reports/fii-dii", timeout=8)
        r = sess.get(_NSE_FII_DII, timeout=10)
        r.raise_for_status()
        raw = r.json()
    except Exception as exc:
        logger.debug("FII/DII fetch failed: %s", exc)
        return []

    out = []
    for row in raw if isinstance(raw, list) else []:
        cat = str(row.get("category", "")).strip()
        # Normalize "FII/FPI **" / "DII **" → "FII" / "DII"
        if cat.upper().startswith("FII"):
            label = "FII"
        elif cat.upper().startswith("DII"):
            label = "DII"
        else:
            label = cat

        def _f(v):
            try:
                return round(float(str(v).replace(",", "")), 2)
            except (ValueError, TypeError):
                return None

        out.append({
            "category":  label,
            "date":      row.get("date", ""),
            "buy_value":  _f(row.get("buyValue")),
            "sell_value": _f(row.get("sellValue")),
            "net_value":  _f(row.get("netValue")),
        })
    return out


@router.get("/fii-dii")
def fii_dii():
    """Latest daily FII/DII cash-market net flows (₹ Cr), from NSE."""
    cache_key = "fii-dii"
    cached = _get(cache_key)
    if cached is not None:
        return cached
    result = _fetch_fii_dii()
    if result:
        _set(cache_key, result)
    return result


# ── Sector heatmap (India) ───────────────────────────────────────────────────

# Representative liquid constituents per sector — averaged to gauge sector breadth.
_SECTOR_CONSTITUENTS = {
    "IT":         ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "Banking":    ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
    "Auto":       ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS"],
    "Pharma":     ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "AUROPHARMA.NS"],
    "FMCG":       ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS"],
    "Energy":     ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "BPCL.NS"],
    "Metals":     ["TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", "COALINDIA.NS", "VEDL.NS"],
    "Financials": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS", "CHOLAFIN.NS"],
    "Realty":     ["DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS", "BRIGADE.NS"],
}


@router.get("/sector-heatmap")
def sector_heatmap():
    """Average intraday % change per India sector (color-coded breadth view)."""
    cache_key = "sector-heatmap"
    cached = _get(cache_key)
    if cached:
        return cached

    # Flatten all constituents, fetch in one batch
    all_syms = [s for syms in _SECTOR_CONSTITUENTS.values() for s in syms]
    quote_map: dict[str, float] = {}
    try:
        from src.providers import market_data_client
        upstox = market_data_client().providers.get("upstox")
        if upstox and upstox.available():
            for q in upstox.batch_quotes(all_syms):
                if q.get("day_change_pct") is not None:
                    quote_map[q["ticker"]] = q["day_change_pct"]
    except Exception as exc:
        logger.warning("Sector heatmap batch failed: %s", exc)

    sectors = []
    for sector, syms in _SECTOR_CONSTITUENTS.items():
        changes = [quote_map[s] for s in syms if s in quote_map]
        if changes:
            sectors.append({
                "sector":     sector,
                "change_pct": round(sum(changes) / len(changes), 2),
                "count":      len(changes),
            })

    sectors.sort(key=lambda x: x["change_pct"], reverse=True)
    out = {"sectors": sectors}
    if sectors:
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
