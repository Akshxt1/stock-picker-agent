# src/agents/portfolio_analyzer.py
#
# Analyzes each open portfolio position using Claude Haiku.
# Gives a fast, data-backed Hold / Sell / Buy More recommendation.
# Runs per-position in ~5 seconds. Much cheaper than a full crew run.

import os, json, re
import anthropic
from dotenv import load_dotenv

load_dotenv()


def analyze_position(pos: dict) -> dict:
    """
    Analyze one portfolio position and return a recommendation.

    Args:
        pos: dict from get_portfolio() — has ticker, entry_price,
             current_price, pnl_pct, days_held, currency, etc.

    Returns:
        dict with action, confidence, summary, reasons, stop_loss, target_price
    """
    ticker   = pos.get("ticker", "")
    currency = pos.get("currency", "USD")
    cur_sym  = "₹" if currency == "INR" else "$"

    # ── Get fresh technical + sentiment data ────────────────────────────────
    tech, sent = {}, {}
    try:
        from src.tools.technical_indicators import get_technical_indicators
        tech = get_technical_indicators.func(ticker)
    except Exception:
        pass
    try:
        from src.tools.news_sentiment import get_stock_sentiment
        sent = get_stock_sentiment.func(ticker)
    except Exception:
        pass

    headlines = "\n".join(
        f"  • {h}" for h in sent.get("recent_headlines", [])[:4]
    ) or "  No recent headlines available"

    prompt = f"""You are a portfolio analyst. Analyze this stock position and give a precise recommendation.

POSITION
  Ticker    : {ticker}  ({pos.get('company','')})
  Sector    : {pos.get('sector','Unknown')}
  Market    : {pos.get('market','Unknown')}
  Entry     : {cur_sym}{pos.get('entry_price',0):,.2f}
  Current   : {cur_sym}{pos.get('current_price',0):,.2f}
  P&L       : {pos.get('pnl_pct',0):+.2f}%  ({cur_sym}{pos.get('pnl_amount',0):+,.2f})
  Qty       : {pos.get('quantity',0):.0f} shares
  Days Held : {pos.get('days_held',0)}

TECHNICALS
  RSI              : {tech.get('rsi','N/A')}  →  {tech.get('rsi_signal','N/A')}
  MACD             : {tech.get('macd_signal_label','N/A')}
  EMA Trend        : {tech.get('ema_trend','N/A')}
  Bollinger        : {tech.get('bb_signal','N/A')}
  Technical Score  : {tech.get('technical_score','N/A')} / 4
  Overall Signal   : {tech.get('overall_signal','N/A')}
  ATR (volatility) : {tech.get('atr','N/A')}

SENTIMENT  :  {sent.get('overall_sentiment','N/A')}
NEWS (recent)
{headlines}

TASK
Based on the data above give one of these recommendations:
  HOLD      — keep the position, thesis intact
  SELL      — exit now, risk outweighs reward
  BUY_MORE  — add to the position, strong setup

Rules:
  - Use actual numbers from the data (RSI value, P&L %, ATR, etc.)
  - Be honest — if the thesis is broken, say SELL even if it hurts
  - stop_loss and target_price must be in the same currency as the position ({cur_sym})
  - Keep summary under 20 words
  - Give exactly 3 reason bullets, each under 25 words

Respond ONLY with valid JSON, no markdown fences, no extra text:
{{
  "action": "HOLD",
  "confidence": "High",
  "summary": "Short one-line verdict here",
  "reasons": ["reason 1", "reason 2", "reason 3"],
  "stop_loss": null,
  "target_price": null
}}"""

    try:
        client   = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model      = "claude-haiku-4-5-20251001",
            max_tokens = 600,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw  = response.content[0].text
        raw  = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)
        data["ticker"] = ticker
        return data

    except Exception as e:
        return {
            "ticker":       ticker,
            "action":       "HOLD",
            "confidence":   "Low",
            "summary":      f"Analysis unavailable: {str(e)[:60]}",
            "reasons":      [],
            "stop_loss":    None,
            "target_price": None,
        }


def analyze_all_positions(market: str = None) -> list[dict]:
    """
    Analyze every open portfolio position.

    Args:
        market: "INDIA", "US", or None for all

    Returns:
        list of analysis dicts, one per position
    """
    from src.database.paper_trading import get_portfolio
    positions = get_portfolio(market=market)
    results   = []
    for pos in positions:
        print(f"  Analysing {pos['ticker']}...")
        result = analyze_position(pos)
        results.append(result)
    return results