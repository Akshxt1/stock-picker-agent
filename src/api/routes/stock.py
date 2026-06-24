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
        # Upstox-only fields (India tickers)
        out["upper_circuit"]  = _clean(q.get("upper_circuit"))
        out["lower_circuit"]  = _clean(q.get("lower_circuit"))
        out["vwap"]           = _clean(q.get("average_price"))
        out["oi"]             = _clean(q.get("oi"))
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

def _google_news_rss_stock(ticker: str, limit: int = 10) -> list[dict]:
    """Google News RSS search for a specific stock (no API key, always fresh)."""
    import urllib.parse
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime

    base = ticker.split(".")[0]  # strip .NS / .BO
    query = f"{base} NSE stock India" if _is_indian(ticker) else f"{base} stock"
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        import requests as _req
        resp = _req.get(
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
            title = item.findtext("title", "")
            link  = item.findtext("link", "") or ""
            pub_date = item.findtext("pubDate", "")
            source_el = item.find("source")
            publisher = source_el.text if source_el is not None else ""
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


def _upstox_news_items(ticker: str) -> list[dict]:
    """News via Upstox News API (India tickers only)."""
    try:
        upstox = market_data_client().providers.get("upstox")
        if upstox and upstox.available():
            return upstox.news(ticker)
    except Exception:
        pass
    return []


def _yfinance_news_items(ticker: str) -> list[dict]:
    """News via yfinance — fallback for tickers not covered by Upstox/Finnhub."""
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

    if _is_indian(ticker):
        # Upstox first (direct per-instrument news), then Google RSS, then yfinance
        items = (
            _upstox_news_items(ticker)
            or _google_news_rss_stock(ticker)
            or _yfinance_news_items(ticker)
            or _finnhub_news_items(ticker)
        )
    else:
        items = _finnhub_news_items(ticker) or _yfinance_news_items(ticker)

    titles = [it["title"] for it in items]
    return {"ticker": ticker, "sentiment": _score_sentiment(titles), "items": items}


# ── Events (dividends / earnings / corporate actions) ─────────────────────────

@router.get("/{ticker}/events")
def events(ticker: str, _user=Depends(get_current_user)):
    from datetime import datetime

    out: dict = {"ticker": ticker, "dividends": [], "upcoming": [], "corporate_actions": []}

    # ── India: use Upstox Corporate Actions (richer than yfinance) ────────────
    if _is_indian(ticker):
        try:
            upstox = market_data_client().providers.get("upstox")
            if upstox and upstox.available():
                actions = upstox.corporate_actions(ticker)
                today = datetime.today()
                label_map = {"Bonus": "Bonus Issue", "Split": "Stock Split", "Rights": "Rights Issue"}

                for action in actions:
                    name    = action.get("name", "")
                    ex_date = action.get("expiry_date", "")
                    amount  = action.get("amount")
                    ratio   = action.get("ratio")

                    # Parse ex-date string like "05 Jun 2026"
                    parsed_date = ""
                    is_future   = False
                    if ex_date:
                        try:
                            dt = datetime.strptime(ex_date, "%d %b %Y")
                            parsed_date = dt.strftime("%Y-%m-%d")
                            is_future   = dt >= today
                        except ValueError:
                            parsed_date = ex_date

                    if name == "Dividend" and amount is not None:
                        out["dividends"].append({
                            "date":   parsed_date,
                            "amount": round(float(amount), 2),
                        })
                        if is_future:
                            out["upcoming"].append({
                                "label": "Ex-Dividend Date",
                                "date":  parsed_date,
                            })
                        # Full history entry
                        out["corporate_actions"].append({
                            "type":    "Dividend",
                            "label":   "Dividend",
                            "date":    parsed_date,
                            "details": f"₹{round(float(amount), 2)}/share",
                            "upcoming": is_future,
                        })
                    elif name in ("Bonus", "Split", "Rights"):
                        detail = label_map.get(name, name)
                        if ratio:
                            detail += f" ({ratio})"
                        if is_future:
                            out["upcoming"].append({"label": detail, "date": parsed_date})
                        out["corporate_actions"].append({
                            "type":    name,
                            "label":   label_map.get(name, name),
                            "date":    parsed_date,
                            "details": ratio or "",
                            "upcoming": is_future,
                        })

                out["dividends"] = out["dividends"][:8]
                # Sort full history newest-first; cap at 15 entries
                out["corporate_actions"].sort(key=lambda a: a.get("date", ""), reverse=True)
                out["corporate_actions"] = out["corporate_actions"][:15]
                return out
        except Exception:
            pass

    # ── US (or India fallback) — yfinance ─────────────────────────────────────
    import yfinance as yf

    try:
        t = yf.Ticker(ticker)

        try:
            divs = t.dividends
            if divs is not None and len(divs):
                for idx, amount in list(divs.items())[-8:]:
                    out["dividends"].append({
                        "date":   str(idx)[:10],
                        "amount": round(float(amount), 2),
                    })
                out["dividends"].reverse()
        except Exception:
            pass

        try:
            info = t.info or {}
        except Exception:
            info = {}

        ex_div = info.get("exDividendDate")
        if ex_div:
            try:
                out["upcoming"].append({
                    "label": "Ex-Dividend Date",
                    "date":  datetime.utcfromtimestamp(ex_div).strftime("%Y-%m-%d"),
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


# ── Shareholding pattern ─────────────────────────────────────────────────────

def _parse_shareholding(raw: list) -> list[dict]:
    """Normalize Upstox shareholding to [{date, promoter, fii, dii, public}]."""
    quarters = []
    for item in (raw or [])[:6]:
        if not isinstance(item, dict):
            continue

        def _pct(*keys) -> float:
            for k in keys:
                v = item.get(k)
                if v is not None:
                    try:
                        return round(float(str(v).replace("%", "").strip()), 2)
                    except (ValueError, TypeError):
                        pass
            return 0.0

        promoter = _pct("promoter", "promoters", "promoter_group", "promoter_holding")
        fii      = _pct("fii", "fiis", "fii_holding", "foreign_portfolio_investor")
        dii      = _pct("dii", "diis", "dii_holding", "mutual_fund")
        public   = _pct("public", "retail", "public_holding", "others")
        date     = str(item.get("date") or item.get("quarter") or item.get("as_of_date") or "")

        if promoter == 0 and fii == 0 and dii == 0 and public == 0:
            continue
        quarters.append({
            "date": date, "promoter": promoter,
            "fii": fii, "dii": dii, "public": public,
        })
    return quarters


@router.get("/{ticker}/shareholding")
def shareholding_pattern(ticker: str, _user=Depends(get_current_user)):
    if not _is_indian(ticker):
        return {"ticker": ticker, "quarters": [], "india_only": True}
    try:
        upstox = market_data_client().providers.get("upstox")
        if not upstox or not upstox.available():
            return {"ticker": ticker, "quarters": []}
        raw = upstox.shareholding(ticker)
        return {"ticker": ticker, "quarters": _parse_shareholding(raw)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Shareholding unavailable: {e}")


# ── Financial summary ─────────────────────────────────────────────────────────

def _numf(v) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").replace("%", "").strip()) or None
    except (ValueError, TypeError):
        return None


@router.get("/{ticker}/financials")
def financials(ticker: str, _user=Depends(get_current_user)):
    if not _is_indian(ticker):
        return {"ticker": ticker, "income": [], "balance_sheet": {}, "ratios": {}, "india_only": True}
    try:
        upstox = market_data_client().providers.get("upstox")
        if not upstox or not upstox.available():
            return {"ticker": ticker, "income": [], "balance_sheet": {}, "ratios": {}}

        income_raw = []
        try:
            income_raw = upstox.income_statement(ticker)
        except Exception:
            pass

        income = []
        for q in (income_raw or [])[:8]:
            if not isinstance(q, dict):
                continue
            period  = str(q.get("date") or q.get("period") or q.get("quarter") or "")
            revenue = _numf(q.get("revenue") or q.get("total_revenue") or q.get("net_revenue") or q.get("sales"))
            pat     = _numf(q.get("pat") or q.get("net_profit") or q.get("profit_after_tax") or q.get("net_income"))
            ebitda  = _numf(q.get("ebitda") or q.get("operating_profit"))
            if period and (revenue is not None or pat is not None):
                income.append({"period": period, "revenue": revenue, "pat": pat, "ebitda": ebitda})

        bs_raw = []
        try:
            bs_raw = upstox.balance_sheet(ticker)
        except Exception:
            pass

        balance: dict = {}
        if bs_raw and isinstance(bs_raw[0], dict):
            latest = bs_raw[0]
            balance = {
                "total_assets": _numf(latest.get("total_assets") or latest.get("total_asset")),
                "total_debt":   _numf(latest.get("total_debt") or latest.get("borrowings")),
                "cash":         _numf(latest.get("cash") or latest.get("cash_and_equivalents")),
                "networth":     _numf(latest.get("networth") or latest.get("net_worth") or latest.get("shareholders_equity")),
            }

        ratios: dict = {}
        try:
            fund_data = market_data_client().fundamentals(ticker).data or {}
            ratios = {
                "pe":       _clean(fund_data.get("trailingPE")),
                "pb":       _clean(fund_data.get("priceToBook")),
                "roe":      fund_data.get("returnOnEquity"),
                "ev_ebitda":fund_data.get("_ev_ebitda"),
                "roce":     fund_data.get("_roce"),
                "roa":      fund_data.get("_roa"),
                "quick":    fund_data.get("_quick_ratio"),
            }
        except Exception:
            pass

        return {"ticker": ticker, "income": income, "balance_sheet": balance, "ratios": ratios}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Financials unavailable: {e}")


# ── Peers / Competitors ───────────────────────────────────────────────────────

@router.get("/{ticker}/peers")
def peers(ticker: str, _user=Depends(get_current_user)):
    if not _is_indian(ticker):
        return {"ticker": ticker, "peers": [], "india_only": True}
    try:
        upstox = market_data_client().providers.get("upstox")
        if not upstox or not upstox.available():
            return {"ticker": ticker, "peers": []}

        raw = upstox.competitors(ticker)
        peer_list = []
        for p in (raw or [])[:6]:
            if not isinstance(p, dict):
                continue
            sym = str(p.get("ticker") or p.get("symbol") or p.get("trading_symbol") or "")
            if sym and not sym.endswith((".NS", ".BO")):
                sym = f"{sym}.NS"
            name  = p.get("name") or p.get("company_name") or sym
            price = _clean(p.get("price") or p.get("last_price"))
            pe    = _clean(p.get("pe") or p.get("pe_ratio"))
            peer_list.append({"ticker": sym, "name": name, "price": price, "pe": pe})

        missing = [p["ticker"] for p in peer_list if p["price"] is None and p["ticker"]]
        if missing:
            try:
                batch = upstox.batch_quotes(missing)
                pm = {q["ticker"]: q["price"] for q in batch}
                for p in peer_list:
                    if p["price"] is None:
                        p["price"] = pm.get(p["ticker"])
            except Exception:
                pass

        return {"ticker": ticker, "peers": peer_list}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Peers unavailable: {e}")


# ── Intraday candles ──────────────────────────────────────────────────────────

@router.get("/{ticker}/intraday")
def intraday_chart(ticker: str, interval: str = Query("30minute"), _user=Depends(get_current_user)):
    if not _is_indian(ticker):
        return {"ticker": ticker, "candles": [], "india_only": True}
    try:
        upstox = market_data_client().providers.get("upstox")
        if not upstox or not upstox.available():
            return {"ticker": ticker, "candles": []}
        candles = upstox.intraday(ticker, interval)
        return {"ticker": ticker, "currency": "INR", "candles": candles}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Intraday data unavailable: {e}")


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
