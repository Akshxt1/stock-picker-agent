# src/agents/portfolio_analyzer.py  — v2
# Saves AI recommendations back to the portfolio DB row

import os, json, re, anthropic
from dotenv import load_dotenv
load_dotenv()


def analyze_position(pos: dict) -> dict:
    ticker   = pos.get("ticker","")
    currency = pos.get("currency","USD")
    cur_sym  = "₹" if currency == "INR" else "$"

    tech, sent = {}, {}
    try:
        from src.tools.technical_indicators import get_technical_indicators
        tech = get_technical_indicators.func(ticker)
    except Exception: pass
    try:
        from src.tools.news_sentiment import get_stock_sentiment
        sent = get_stock_sentiment.func(ticker)
    except Exception: pass

    headlines = "\n".join(
        f"  • {h}" for h in sent.get("recent_headlines",[])[:4]
    ) or "  No recent headlines"

    entry  = pos.get("entry_price", 0)
    curr   = pos.get("current_price", 0)
    pnl    = pos.get("pnl_pct", 0)

    # Suggested stop loss and target based on ATR
    atr        = tech.get("atr") or 0
    atr_pct    = round((atr / curr) * 100, 2) if curr else 2.0
    stop_hint  = round(curr * (1 - atr_pct / 100 * 2), 2)
    target_hint= round(curr * (1 + atr_pct / 100 * 3), 2)

    prompt = f"""You are a portfolio risk manager. Analyse this position concisely.

POSITION
  Ticker      : {ticker}
  Company     : {pos.get('company','')}
  Entry       : {cur_sym}{entry:,.2f}
  Current     : {cur_sym}{curr:,.2f}
  P&L         : {pnl:+.2f}%
  Qty         : {pos.get('quantity',0):.0f} shares
  Days Held   : {pos.get('days_held',0)}

TECHNICALS
  RSI         : {tech.get('rsi','N/A')}  →  {tech.get('rsi_signal','N/A')}
  MACD        : {tech.get('macd_signal_label','N/A')}
  EMA Trend   : {tech.get('ema_trend','N/A')}
  Overall     : {tech.get('overall_signal','N/A')}  (score {tech.get('technical_score','N/A')}/4)

SENTIMENT    : {sent.get('overall_sentiment','N/A')}
NEWS
{headlines}

ATR hint: stop ~{cur_sym}{stop_hint:,.2f} | target ~{cur_sym}{target_hint:,.2f}

Give ONE clear recommendation with a concise 1-sentence summary and exactly 2 reasons.

Respond ONLY with this JSON (no markdown):
{{
  "action": "HOLD",
  "confidence": "High",
  "summary": "One clear sentence — max 15 words",
  "reasons": ["reason 1 with a number", "reason 2 with a number"],
  "stop_loss": {stop_hint},
  "target_price": {target_hint}
}}"""

    try:
        client   = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=400,
            messages=[{"role":"user","content":prompt}],
        )
        raw  = re.sub(r"```json|```","",response.content[0].text).strip()
        data = json.loads(raw)
        data["ticker"] = ticker

        # Save result back to portfolio DB
        if pos.get("id"):
            try:
                from src.database.paper_trading import save_ai_analysis
                save_ai_analysis(pos["id"], data)
            except Exception as e:
                print(f"  [save_ai] {e}")

        return data
    except Exception as e:
        return {
            "ticker":       ticker,
            "action":       "HOLD",
            "confidence":   "Low",
            "summary":      f"Analysis unavailable",
            "reasons":      [],
            "stop_loss":    stop_hint,
            "target_price": target_hint,
        }


def analyze_all_positions(market: str = None, user_id: str = None) -> list:
    from src.database.paper_trading import get_portfolio
    positions = get_portfolio(market=market, username=user_id)
    results   = []
    for pos in positions:
        print(f"  Analysing {pos['ticker']}...")
        results.append(analyze_position(pos))
    return results