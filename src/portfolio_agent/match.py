"""Match extracted rows to real, tradable symbols the rest of the app understands.

Rows are matched by ticker and by name across Indian stocks/ETFs (Upstox instrument list, falling back
to the app's universe), US stocks/ETFs/funds (universe, then Yahoo search), crypto (CoinGecko) and
mutual funds (mfapi.in / Yahoo). Each row gets ranked candidates and a status. Only confident matches
are pre-selected; the rest are left for the user to pick, because a wrong symbol silently poisons the
whole analysis.
"""

import concurrent.futures
import difflib
import logging
import re

from src.assets import crypto, funds
from src.data.stock_universe import INDIAN_STOCKS, TICKER_NAMES, US_STOCKS

logger = logging.getLogger("stockpicker.portfolio_agent")

CONFIDENT = 0.85
MAX_CANDIDATES = 5

_NOISE = {"ltd", "limited", "inc", "incorporated", "corp", "corporation", "co", "company", "plc", "the", "and",
          "plan", "option", "regular", "direct", "growth", "idcw", "dividend", "payout", "fund", "scheme", "of",
          "class", "a", "adr", "nv", "sa", "ag"}


def _norm(name: str | None) -> str:
    toks = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower().replace("&", " and ")).split()
    return " ".join(t for t in toks if t not in _NOISE)


def similarity(a: str | None, b: str | None) -> float:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    contain = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0
    # name fully contained in the other (e.g. "infosys" in "infosys technologies") is a strong signal
    return max(ratio, 0.9 * contain if contain == 1.0 else 0.0)


def _bare(symbol: str | None) -> str:
    s = (symbol or "").upper().strip()
    return re.sub(r"[:.\-](NS|BO|NSE|BSE)$", "", s).replace("NSE:", "").replace("BSE:", "")


# ── candidate pools ──────────────────────────────────────────────────────────

def _india_names() -> dict[str, str]:
    """ticker -> company name for NSE equities/ETFs (Upstox list if available, else the app's universe)."""
    try:
        from src.providers import market_data_client
        up = market_data_client().providers.get("upstox")
        if up and up.available():
            up._ensure_instruments()
            names = {t: v.get("name") or t for t, v in up._instruments.items() if t.endswith(".NS")}
            if names:
                return names
    except Exception as e:
        logger.info("upstox instrument list unavailable for matching: %s", e)
    return {t: TICKER_NAMES.get(t, t) for sec in INDIAN_STOCKS.values() for tl in sec.values() for t in tl}


def _us_names() -> dict[str, str]:
    return {t: TICKER_NAMES.get(t, t) for sec in US_STOCKS.values() for tl in sec.values() for t in tl}


def _cand(symbol, name, asset_class, market, score) -> dict:
    return {"symbol": symbol, "name": name, "asset_class": asset_class, "market": market, "score": round(score, 3)}


def _score(row: dict, ticker: str, name: str) -> float:
    s = similarity(row.get("name"), name)
    if row.get("symbol") and _bare(row["symbol"]) == _bare(ticker):
        s = max(s, 0.97)
    elif row.get("name") and _bare(row["name"]) == _bare(ticker):
        s = max(s, 0.9)
    return s


def _stock_pool(row: dict, names: dict[str, str], market: str) -> list[dict]:
    out = [_cand(t, n, "EQUITY", market, _score(row, t, n)) for t, n in names.items()]
    return [c for c in out if c["score"] >= 0.45]


def _yahoo(row: dict) -> list[dict]:
    q = row.get("name") or row.get("symbol")
    if not q or len(q) < 2:
        return []
    try:
        import yfinance as yf
        quotes = yf.Search(q, max_results=8).quotes
    except Exception:
        return []
    out = []
    for x in quotes:
        kind, sym = x.get("quoteType"), x.get("symbol")
        if kind not in ("EQUITY", "ETF", "MUTUALFUND") or not sym or "." in sym and not sym.endswith((".NS", ".BO")):
            continue
        name = x.get("longname") or x.get("shortname") or sym
        market = "INDIA" if sym.endswith((".NS", ".BO")) else "US"
        out.append(_cand(sym, name, "EQUITY" if kind == "EQUITY" else "FUND", market, _score(row, sym, name)))
    return out


def candidates_for(row: dict, prefer: str | None = None) -> list[dict]:
    """Ranked candidate symbols for one extracted row. `prefer` ('INDIA'|'US') breaks ties by market."""
    klass = row.get("asset_class") or "other"
    exch = (row.get("exchange") or "").upper()
    q = row.get("name") or row.get("symbol") or ""
    cands: list[dict] = []

    want_stock = klass in ("stock", "etf", "other")
    if klass in ("crypto", "other"):
        try:
            for hit in crypto.search(q if len(q) > 1 else row.get("symbol") or "", 6):
                s = max(similarity(row.get("name"), hit["name"]),
                        0.97 if row.get("symbol") and row["symbol"].upper() == hit["ticker"] else 0.0)
                cands.append(_cand(hit["symbol"], hit["name"], "CRYPTO", "CRYPTO", s))
        except Exception:
            pass
    if klass in ("mutual_fund", "etf", "other"):
        for fn, market in ((funds.search_india, "INDIA"), (funds.search_us, "US")):
            try:
                for hit in fn(q, 6):
                    cands.append(_cand(hit["symbol"], hit["name"], "FUND", market, similarity(row.get("name"), hit["name"])))
            except Exception:
                pass
    if want_stock:
        india_ok = exch in ("", "NSE", "BSE", "OTHER") and prefer != "US" or exch in ("NSE", "BSE")
        us_ok = exch in ("", "NASDAQ", "NYSE", "OTHER") and prefer != "INDIA" or exch in ("NASDAQ", "NYSE")
        if india_ok:
            cands += _stock_pool(row, _india_names(), "INDIA")
        if us_ok:
            cands += _stock_pool(row, _us_names(), "US")
        if not any(c["score"] >= CONFIDENT for c in cands):
            cands += [c for c in _yahoo(row) if (c["market"] == "INDIA" and india_ok) or (c["market"] == "US" and us_ok)]

    best: dict[str, dict] = {}
    for c in cands:                                   # keep the best score per symbol
        if c["symbol"] not in best or c["score"] > best[c["symbol"]]["score"]:
            best[c["symbol"]] = c
    ranked = sorted(best.values(), key=lambda c: (-c["score"], c["market"] != (prefer or "INDIA")))
    return ranked[:MAX_CANDIDATES]


def match_rows(rows: list[dict], portfolio_currency: str | None = None) -> list[dict]:
    """Add `candidates`, `match` (symbol or None) and `status` ('matched'|'review'|'unmatched') to each row."""
    prefer = {"INR": "INDIA", "USD": "US"}.get((portfolio_currency or "").upper())

    def one(row):
        try:
            cands = candidates_for(row, prefer)
        except Exception:
            logger.exception("matching failed for %s", row.get("name"))
            cands = []
        top = cands[0] if cands else None
        runner_up = cands[1]["score"] if len(cands) > 1 else 0.0
        confident = bool(top and top["score"] >= CONFIDENT and top["score"] - runner_up >= 0.03)
        return {**row, "candidates": cands, "match": top["symbol"] if confident else None,
                "status": "matched" if confident else ("review" if cands else "unmatched")}

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(one, rows))
