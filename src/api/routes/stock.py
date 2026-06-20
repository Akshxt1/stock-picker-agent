"""
src/api/routes/stock.py

Per-ticker detail endpoints powering the stock detail page
(chart + AI Analysis / Technicals / News / Events tabs).

All read-only and served through the cached `market_data_client`, so repeated
loads are cheap.

GET /api/stock/{ticker}/quote       — live price, day change, key fundamentals
GET /api/stock/{ticker}/history     — OHLC series for the chart (?period=6mo)
GET /api/stock/{ticker}/technicals  — RSI / MACD / EMA / Bollinger / ATR
GET /api/stock/{ticker}/news        — recent headlines + sentiment label
GET /api/stock/{ticker}/events      — dividends + upcoming earnings/ex-div dates
GET /api/stock/{ticker}/ai          — latest saved AI pick (why buy / why not)
"""

import math

from fastapi import APIRouter, Depends, Query, HTTPException

from src.api.routes.auth import get_current_user
from src.providers import market_data_client

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_indian(ticker: str) -> bool:
    return ticker.upper().endswith((".NS", ".BO"))


def _currency(ticker: str) -> str:
    return "INR" if _is_indian(ticker) else "USD"


def _clean(v):
    """Make a value JSON-safe (NaN/inf → None)."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def _fmt_pct(v) -> str | None:
    return f"{v * 100:.2f}%" if isinstance(v, (int, float)) else None


def _fmt_de(v) -> str | None:
    # yfinance debtToEquity is a ratio×100 (335.5 → 3.36)
    return f"{v / 100:.2f}" if isinstance(v, (int, float)) else None


# ── Quote + fundamentals ──────────────────────────────────────────────────────

@router.get("/{ticker}/quote")
def quote(ticker: str, _user=Depends(get_current_user)):
    client = market_data_client()
    out: dict = {"ticker": ticker, "currency": _currency(ticker)}

    try:
        q = client.quote(ticker).data
        out["price"]          = _clean(q.get("price"))
        out["previous_close"] = _clean(q.get("previous_close"))
        out["day_change_pct"] = _clean(q.get("day_change_pct"))
    except Exception as e:
        out["price_error"] = str(e)

    try:
        info = client.fundamentals(ticker).data or {}
        out["company_name"] = info.get("shortName") or info.get("longName") or ticker
        out["sector"]       = info.get("sector")
        out["industry"]     = info.get("industry")
        out["market_cap"]   = _clean(info.get("marketCap"))
        out["pe_ratio"]     = _clean(info.get("trailingPE"))
        out["pb_ratio"]     = _clean(info.get("priceToBook"))
        out["eps"]          = _clean(info.get("trailingEps"))
        out["roe"]          = _fmt_pct(info.get("returnOnEquity"))
        out["debt_to_equity"] = _fmt_de(info.get("debtToEquity"))
        out["revenue_growth"] = _fmt_pct(info.get("revenueGrowth"))
        out["dividend_yield"] = _fmt_pct(info.get("dividendYield"))
        out["fifty_two_week_high"] = _clean(info.get("fiftyTwoWeekHigh"))
        out["fifty_two_week_low"]  = _clean(info.get("fiftyTwoWeekLow"))
    except Exception as e:
        out["fundamentals_error"] = str(e)
        out.setdefault("company_name", ticker)

    return out


# ── Price history for the chart ───────────────────────────────────────────────

@router.get("/{ticker}/history")
def history(ticker: str, period: str = Query("6mo"), _user=Depends(get_current_user)):
    try:
        df = market_data_client().history(ticker, period=period).data
        if df is None or df.empty:
            return {"ticker": ticker, "period": period, "candles": []}
        candles = []
        for idx, row in df.iterrows():
            candles.append({
                "date":   str(idx)[:10],
                "open":   _clean(round(float(row["Open"]), 2))   if "Open"   in row else None,
                "high":   _clean(round(float(row["High"]), 2))   if "High"   in row else None,
                "low":    _clean(round(float(row["Low"]), 2))    if "Low"    in row else None,
                "close":  _clean(round(float(row["Close"]), 2))  if "Close"  in row else None,
                "volume": _clean(int(row["Volume"]))             if "Volume" in row and not math.isnan(row["Volume"]) else None,
            })
        return {"ticker": ticker, "period": period, "currency": _currency(ticker), "candles": candles}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"History unavailable: {e}")


# ── Technical indicators ──────────────────────────────────────────────────────

@router.get("/{ticker}/technicals")
def technicals(ticker: str, _user=Depends(get_current_user)):
    try:
        import pandas_ta as ta
        df = market_data_client().history(ticker, period="6mo").data
        if df is None or len(df) < 30:
            raise HTTPException(status_code=422, detail="Not enough price history for technicals")

        close, high, low = df["Close"], df["High"], df["Low"]

        def _last(series):
            try:
                v = float(series.dropna().iloc[-1])
                return _clean(round(v, 2))
            except Exception:
                return None

        rsi = _last(ta.rsi(close, length=14))
        macd_df = ta.macd(close)
        macd_line   = _last(macd_df.iloc[:, 0]) if macd_df is not None else None
        macd_signal = _last(macd_df.iloc[:, 2]) if macd_df is not None else None
        macd_hist   = _last(macd_df.iloc[:, 1]) if macd_df is not None else None
        ema20 = _last(ta.ema(close, length=20))
        ema50 = _last(ta.ema(close, length=50))
        atr   = _last(ta.atr(high, low, close, length=14))
        bb = ta.bbands(close, length=20)
        bb_lower = _last(bb.iloc[:, 0]) if bb is not None else None
        bb_mid   = _last(bb.iloc[:, 1]) if bb is not None else None
        bb_upper = _last(bb.iloc[:, 2]) if bb is not None else None

        price = _last(close)

        # human-readable classifications
        rsi_label = (
            "Oversold" if rsi is not None and rsi < 30 else
            "Weak"     if rsi is not None and rsi < 45 else
            "Neutral"  if rsi is not None and rsi < 55 else
            "Strong"   if rsi is not None and rsi < 70 else
            "Overbought" if rsi is not None else None
        )
        trend = None
        if ema20 is not None and ema50 is not None:
            trend = "Uptrend" if ema20 > ema50 else "Downtrend"
        macd_label = None
        if macd_hist is not None:
            macd_label = "Bullish" if macd_hist > 0 else "Bearish"

        return {
            "ticker": ticker,
            "price": price,
            "rsi": rsi, "rsi_label": rsi_label,
            "macd": macd_line, "macd_signal": macd_signal, "macd_hist": macd_hist, "macd_label": macd_label,
            "ema20": ema20, "ema50": ema50, "trend": trend,
            "atr": atr,
            "bb_lower": bb_lower, "bb_mid": bb_mid, "bb_upper": bb_upper,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Technicals unavailable: {e}")


# ── News ──────────────────────────────────────────────────────────────────────

def _finnhub_news_items(ticker: str) -> list[dict]:
    """Rich company news from Finnhub (US): title, source, link, date. Last 21 days."""
    import os, requests
    from datetime import datetime, timedelta

    key = os.getenv("FINNHUB_API_KEY")
    if not key:
        return []
    sym = ticker.split(".")[0]
    today = datetime.today()
    frm = (today - timedelta(days=21)).strftime("%Y-%m-%d")
    to = today.strftime("%Y-%m-%d")
    try:
        resp = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={"symbol": sym, "from": frm, "to": to, "token": key},
            timeout=10,
        )
        resp.raise_for_status()
        out = []
        for it in resp.json()[:15]:
            headline = it.get("headline")
            if not headline:
                continue
            ts = it.get("datetime")
            published = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
            out.append({
                "title": headline,
                "publisher": it.get("source") or "",
                "link": it.get("url") or "",
                "published": published,
            })
        return out
    except Exception:
        return []


def _yfinance_news_items(ticker: str) -> list[dict]:
    """News via yfinance (used for Indian tickers Finnhub can't cover)."""
    import yfinance as yf
    items = []
    try:
        raw = yf.Ticker(ticker).news or []
        for it in raw[:15]:
            content = it.get("content", {}) if isinstance(it, dict) else {}
            title = it.get("title") or content.get("title") or ""
            if not title:
                continue
            link = (
                it.get("link")
                or (content.get("canonicalUrl") or {}).get("url")
                or (content.get("clickThroughUrl") or {}).get("url")
                or ""
            )
            publisher = (
                it.get("publisher")
                or (content.get("provider") or {}).get("displayName")
                or ""
            )
            published = content.get("pubDate") or it.get("providerPublishTime") or ""
            items.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "published": str(published)[:10] if published else "",
            })
    except Exception:
        pass
    return items


@router.get("/{ticker}/news")
def news(ticker: str, _user=Depends(get_current_user)):
    from src.tools.news_sentiment import _score_sentiment

    # US → Finnhub (fresh, many sources). India → yfinance. Each falls back to the other.
    if _is_indian(ticker):
        items = _yfinance_news_items(ticker) or _finnhub_news_items(ticker)
    else:
        items = _finnhub_news_items(ticker) or _yfinance_news_items(ticker)

    titles = [it["title"] for it in items]
    return {"ticker": ticker, "sentiment": _score_sentiment(titles), "items": items}


# ── Events (dividends / earnings) ─────────────────────────────────────────────

@router.get("/{ticker}/events")
def events(ticker: str, _user=Depends(get_current_user)):
    import yfinance as yf
    from datetime import datetime

    out: dict = {"ticker": ticker, "dividends": [], "upcoming": []}
    try:
        t = yf.Ticker(ticker)

        # Historical dividends (last 8)
        try:
            divs = t.dividends
            if divs is not None and len(divs):
                for idx, amount in list(divs.items())[-8:]:
                    out["dividends"].append({
                        "date": str(idx)[:10],
                        "amount": round(float(amount), 2),
                    })
                out["dividends"].reverse()
        except Exception:
            pass

        # Upcoming events from calendar / info
        try:
            info = t.info or {}
        except Exception:
            info = {}

        ex_div = info.get("exDividendDate")
        if ex_div:
            try:
                out["upcoming"].append({
                    "label": "Ex-Dividend Date",
                    "date": datetime.utcfromtimestamp(ex_div).strftime("%Y-%m-%d"),
                })
            except Exception:
                pass
        div_rate = info.get("dividendRate")
        if div_rate:
            out["dividend_rate"] = round(float(div_rate), 2)

        try:
            cal = t.calendar
            if isinstance(cal, dict):
                ed = cal.get("Earnings Date")
                if ed:
                    dates = ed if isinstance(ed, list) else [ed]
                    for d in dates[:2]:
                        out["upcoming"].append({"label": "Earnings Date", "date": str(d)[:10]})
        except Exception:
            pass
    except Exception as e:
        out["error"] = str(e)

    return out


# ── AI analysis (latest saved pick) ───────────────────────────────────────────

@router.get("/{ticker}/ai")
def ai_analysis(ticker: str, user=Depends(get_current_user)):
    try:
        from src.database.models import Session, Pick, Portfolio, _pick_to_dict
        with Session() as sess:
            # 1) Prefer THIS user's own latest crew pick (richest: why_buy /
            #    why_not_buy). Scoped to the user so one account never sees
            #    another's analysis.
            row = (
                sess.query(Pick)
                .filter(Pick.ticker == ticker, Pick.run_by_user_id == user["user_id"])
                .order_by(Pick.created_at.desc())
                .first()
            )
            if row:
                data = _pick_to_dict(row)
                data["has_pick"] = True
                data["source"] = "crew"
                return data

            # 2) Fall back to this user's saved per-holding "Run Analysis" verdict.
            holding = (
                sess.query(Portfolio)
                .filter(
                    Portfolio.ticker == ticker,
                    Portfolio.user_id == user["user_id"],
                    Portfolio.recommendation.isnot(None),
                )
                .order_by(Portfolio.analyzed_at.desc().nullslast()
                          if hasattr(Portfolio.analyzed_at, "desc") else Portfolio.id.desc())
                .first()
            )
            if holding and holding.recommendation:
                why_buy = list(holding.why_buy) if getattr(holding, "why_buy", None) else []
                why_not = list(holding.why_not_buy) if getattr(holding, "why_not_buy", None) else []
                return {
                    "ticker": ticker,
                    "has_pick": True,
                    "source": "holding",
                    "recommendation": holding.recommendation,
                    "technical_signal": holding.recommendation,
                    "confidence": None,
                    "sentiment": None,
                    "why_buy": why_buy,
                    "why_not_buy": why_not,
                    "analysis_summary": holding.analysis_summary,
                    "target_price": holding.target_price,
                    "stop_loss": holding.stop_loss,
                    "analysis_date": holding.analyzed_at.strftime("%Y-%m-%d") if holding.analyzed_at else None,
                }

            return {"ticker": ticker, "has_pick": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
