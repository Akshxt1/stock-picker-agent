"""
src/api/routes/portfolio.py

GET    /api/portfolio                 — user's portfolio (live price + P&L + P/E)
POST   /api/portfolio                 — add position
DELETE /api/portfolio/{holding_id}    — remove position
POST   /api/portfolio/{holding_id}/analyze — lightweight AI verdict (Target/SL/reco)
"""

import os
import json
import concurrent.futures

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.routes.auth import get_current_user

try:
    from src.database.models import (
        get_portfolio, add_portfolio_position, remove_portfolio_position,
        save_holding_analysis,
    )
    _DB = True
except ImportError:
    _DB = False

router = APIRouter()


class AddPositionRequest(BaseModel):
    ticker:   str
    quantity: float
    buy_price: float


# ── live enrichment ───────────────────────────────────────────────────────────

def _enrich(holding: dict) -> dict:
    """Attach live current price, P&L %, and P/E to a holding (cached quote)."""
    from src.providers import market_data_client
    client = market_data_client()
    ticker = holding["ticker"]
    try:
        price = float(client.quote(ticker).data["price"])
        holding["current_price"] = round(price, 2)
        buy = holding.get("buy_price")
        if buy:
            holding["pnl_pct"] = round((price - buy) / buy * 100, 2)
    except Exception:
        pass
    try:
        pe = client.fundamentals(ticker).data.get("trailingPE")
        if isinstance(pe, (int, float)):
            holding["pe_ratio"] = round(float(pe), 2)
    except Exception:
        pass
    return holding


@router.get("")
def get_portfolio_route(
    market: str | None = Query(None, description="Filter by market: INDIA or US"),
    user=Depends(get_current_user),
):
    if not _DB:
        return []
    try:
        holdings = get_portfolio(user["user_id"], market=market.upper() if market else None)
        if not holdings:
            return []
        # Fetch live quotes concurrently so one slow ticker can't stall the page.
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            holdings = list(ex.map(_enrich, holdings))
        return holdings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def add_position(body: AddPositionRequest, user=Depends(get_current_user)):
    if not _DB:
        return {"ok": True}
    try:
        add_portfolio_position(
            user_id   = user["user_id"],
            ticker    = body.ticker,
            quantity  = body.quantity,
            buy_price = body.buy_price,
            username  = user.get("username") or user.get("email"),
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{holding_id}")
def remove_position(holding_id: int, user=Depends(get_current_user)):
    if not _DB:
        return {"ok": True}
    try:
        remove_portfolio_position(holding_id, user["user_id"])
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Lightweight per-holding AI analysis ───────────────────────────────────────

def _analyze_and_save(holding: dict, user_id: str) -> dict:
    """Gather live context for a holding, get an LLM verdict, persist it. Returns verdict."""
    ticker = holding["ticker"]
    from src.providers import market_data_client
    client = market_data_client()
    ctx = {"ticker": ticker, "buy_price": holding.get("buy_price"), "quantity": holding.get("quantity")}
    try:
        ctx["current_price"] = round(float(client.quote(ticker).data["price"]), 2)
    except Exception:
        ctx["current_price"] = None
    try:
        info = client.fundamentals(ticker).data or {}
        ctx["pe"]  = info.get("trailingPE")
        ctx["roe"] = info.get("returnOnEquity")
        ctx["rev_growth"] = info.get("revenueGrowth")
        ctx["debt_to_equity"] = info.get("debtToEquity")
        ctx["company"] = info.get("shortName") or ticker
    except Exception:
        pass
    try:
        from src.tools.news_sentiment import _get_headlines, _score_sentiment
        heads = _get_headlines(ticker)[:6]
        ctx["headlines"] = heads
        ctx["sentiment"] = _score_sentiment(heads)
    except Exception:
        ctx["headlines"] = []

    verdict = _call_llm_verdict(ctx)
    save_holding_analysis(
        holding_id     = holding["id"],
        user_id        = user_id,
        recommendation = verdict.get("recommendation"),
        target_price   = verdict.get("target_price"),
        stop_loss      = verdict.get("stop_loss"),
        summary        = verdict.get("summary"),
        why_buy        = verdict.get("why_buy"),
        why_not_buy    = verdict.get("why_not_buy"),
    )
    return {"ticker": ticker, **verdict}


@router.post("/{holding_id}/analyze")
def analyze_holding(holding_id: int, user=Depends(get_current_user)):
    """One fast Anthropic verdict (HOLD/BUY/BUY_MORE/SELL) + target + stop-loss + reasoning.

    The quick per-holding verdict is cheap and does NOT consume the deep-analysis quota.
    """
    if not _DB:
        raise HTTPException(status_code=503, detail="DB unavailable")

    holdings = get_portfolio(user["user_id"])
    holding = next((h for h in holdings if h["id"] == holding_id), None)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    verdict = _analyze_and_save(holding, user["user_id"])
    return {"ok": True, **verdict}


@router.post("/analyze-all")
def analyze_all_holdings(market: str | None = Query(None), user=Depends(get_current_user)):
    """Analyse every holding (optionally one market) in one go.

    Counts as 1 against the account's weekly deep/portfolio analysis quota.
    """
    if not _DB:
        raise HTTPException(status_code=503, detail="DB unavailable")

    account_type = user.get("account_type", "trial")
    if account_type == "guest":
        raise HTTPException(status_code=403, detail="Guest accounts cannot run analysis. Please sign up.")

    try:
        from src.database.models import increment_portfolio_run_count, ACCOUNT_LIMITS
        if not increment_portfolio_run_count(user["user_id"]):
            limit = ACCOUNT_LIMITS.get(account_type, {}).get("portfolio_runs", 0)
            raise HTTPException(
                status_code=429,
                detail=f"Weekly analysis limit reached ({limit} deep/portfolio runs for {account_type} plan). Resets next Monday."
            )
    except HTTPException:
        raise
    except Exception:
        pass

    holdings = get_portfolio(user["user_id"], market=market.upper() if market else None)
    if not holdings:
        return {"ok": True, "analyzed": 0, "results": []}

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(_analyze_and_save, h, user["user_id"]) for h in holdings]
        for f in concurrent.futures.as_completed(futures):
            try:
                results.append(f.result())
            except Exception:
                pass
    return {"ok": True, "analyzed": len(results), "results": results}


def _call_llm_verdict(ctx: dict) -> dict:
    """Single Anthropic call returning a structured verdict. Falls back gracefully."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    cur = ctx.get("current_price")

    if not api_key:
        # Deterministic fallback so the feature still works without a key.
        return {
            "recommendation": "HOLD",
            "target_price": round(cur * 1.12, 2) if cur else None,
            "stop_loss":    round(cur * 0.92, 2) if cur else None,
            "summary": "AI key not configured — showing a neutral default. Set ANTHROPIC_API_KEY for a real analysis.",
            "why_buy": [],
            "why_not_buy": [],
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You are a CFA-certified portfolio strategist. Given the data below for a stock the user "
            "already holds, weigh fundamentals, valuation, and news sentiment, then decide an action "
            "and realistic price levels. Respond with ONLY raw JSON, no markdown:\n"
            '{"recommendation": "HOLD|BUY_MORE|SELL", "target_price": number, "stop_loss": number, '
            '"summary": "2 short sentences", '
            '"why_buy": ["specific point with a number", "specific point", "specific point"], '
            '"why_not_buy": ["specific risk", "specific risk"]}\n\n'
            f"Data: {json.dumps(ctx, default=str)}\n"
            f"Current price: {cur}. Target and stop_loss must be absolute prices in the same currency. "
            "why_buy and why_not_buy must cite the actual figures provided (P/E, ROE, growth, sentiment)."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")

        # Log token usage (best effort)
        try:
            from src.database.models import log_api_usage
            log_api_usage(
                user_id="", username="system",
                model="claude-haiku-4-5-20251001",
                input_tokens=msg.usage.input_tokens,
                output_tokens=msg.usage.output_tokens,
                agent="holding_analysis",
                run_context=ctx.get("ticker", ""),
            )
        except Exception:
            pass

        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start:end + 1])
        rec = str(data.get("recommendation", "HOLD")).upper()
        if rec not in ("HOLD", "BUY", "BUY_MORE", "SELL"):
            rec = "HOLD"
        return {
            "recommendation": rec,
            "target_price": data.get("target_price"),
            "stop_loss":    data.get("stop_loss"),
            "summary":      data.get("summary", ""),
            "why_buy":      data.get("why_buy") or [],
            "why_not_buy":  data.get("why_not_buy") or [],
        }
    except Exception as e:
        return {
            "recommendation": "HOLD",
            "target_price": round(cur * 1.12, 2) if cur else None,
            "stop_loss":    round(cur * 0.92, 2) if cur else None,
            "summary": f"Analysis fell back to defaults ({e}).",
            "why_buy": [],
            "why_not_buy": [],
        }
