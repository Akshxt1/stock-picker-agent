# src/agents/tasks.py

from crewai import Task
from src.agents.agents import (
    create_researcher, create_data_analyst,
    create_sentiment_analyst, create_master_analyst,
)
from datetime import datetime


def create_tasks(market: str, sector: str, size: str):
    """
    Create the 4-agent task pipeline.
    No tickers argument — the Researcher discovers stocks itself.
    """
    researcher        = create_researcher()
    data_analyst      = create_data_analyst()
    sentiment_analyst = create_sentiment_analyst()
    master_analyst    = create_master_analyst()

    today = datetime.today().strftime("%Y-%m-%d")

    # ── Task 1: Discovery + Research ─────────────────────────────────────────
    # The Researcher calls discover_stocks() and get_market_movers() itself,
    # builds its own watchlist, then fetches data for each stock it finds.
    task_research = Task(
        description=(
            f"Today's date: {today}\n"
            f"Market: {market} | Sector: {sector} | Size: {size} Cap\n\n"
            f"STEP 1 — DISCOVER STOCKS:\n"
            f"  Call the discover_stocks tool with market='{market}', "
            f"sector='{sector}', size='{size}'.\n"
            f"  Also call get_market_movers with market='{market}', sector='{sector}' "
            f"to find momentum candidates.\n"
            f"  Combine both results into a watchlist of 8-15 tickers. "
            f"Remove duplicates. Prefer stocks that appear in BOTH lists.\n\n"
            f"STEP 2 — RESEARCH EACH STOCK:\n"
            f"  For EACH ticker in your watchlist, collect:\n"
            f"  1. Company name, exchange, sector, industry\n"
            f"  2. Current price, day change %, 30-day momentum\n"
            f"  3. Market cap and classification\n"
            f"  4. Volume spike ratio (flag anything above 1.5x as notable)\n"
            f"  5. Fundamentals: P/E, P/B, ROE, revenue growth YoY, "
            f"debt-to-equity, EPS\n"
            f"  6. 52-week high and low — calculate how far current price is from each\n"
            f"  7. Recent news headlines (last 7 days)\n\n"
            f"STEP 3 — FIRST PASS FILTER:\n"
            f"  Flag and DROP any stock with:\n"
            f"  - Debt-to-equity > 3 (HIGH RISK)\n"
            f"  - Revenue growth < 0% (DECLINING)\n"
            f"  - 30-day momentum < -15% (SEVERE DOWNTREND)\n"
            f"  - ROE < 5% (POOR QUALITY)\n"
            f"  - Market cap data unavailable (unreliable data)\n\n"
            f"Present the full watchlist with all metrics, clearly marking "
            f"which stocks passed and which were dropped."
        ),
        expected_output=(
            "A watchlist of 8-15 stocks the agent discovered itself, with full "
            "fundamental data for each. Clearly shows which stocks passed the first "
            "pass filter and which were dropped with reasons."
        ),
        agent=researcher,
    )

    # ── Task 2: Technical Analysis ────────────────────────────────────────────
    task_technical = Task(
        description=(
            f"Using the watchlist from the Researcher's report, run full technical "
            f"analysis on all stocks that PASSED the first pass filter.\n\n"
            f"For EACH ticker calculate:\n"
            f"  1. RSI (14) — classify: <30 oversold, 30-45 weak, 45-55 neutral, "
            f"55-70 strong, >70 overbought\n"
            f"  2. MACD — bullish crossover, bearish crossover, or divergence\n"
            f"  3. Bollinger Bands — band position and squeeze/expansion\n"
            f"  4. EMA 20 vs EMA 50 — trend direction and strength\n"
            f"  5. ATR — volatility rating (Low/Medium/High/Extreme)\n"
            f"  6. Volume trend — increasing/decreasing vs 20-day average\n"
            f"  7. Technical score (-4 to +4) and overall signal\n\n"
            f"QUALITY GATE — Mark as TECHNICALLY REJECTED if:\n"
            f"  - RSI > 75 (dangerously overbought)\n"
            f"  - RSI < 25 (in freefall)\n"
            f"  - EMA 20 AND EMA 50 both pointing sharply downward\n"
            f"  - MACD histogram deeply negative with no sign of reversal\n"
            f"  - Technical score below -2\n\n"
            f"Rank all tickers from strongest to weakest technical setup.\n"
            f"Produce a SHORTLIST of the top 5 technically sound stocks.\n"
            f"Be ruthless — 2 good picks beats 5 mediocre ones."
        ),
        expected_output=(
            "Ranked list of all tickers with full technical data, signal labels, "
            "and a final SHORTLIST of top 5. TECHNICALLY REJECTED stocks clearly marked."
        ),
        agent=data_analyst,
        context=[task_research],
    )

    # ── Task 3: Sentiment & Risk Analysis ────────────────────────────────────
    task_sentiment = Task(
        description=(
            f"Using the watchlist from the Researcher's report, analyse sentiment "
            f"and risk for all stocks that PASSED the first pass filter.\n\n"
            f"For EACH ticker:\n"
            f"  1. News sentiment: Bullish / Neutral / Bearish with key themes\n"
            f"  2. Market buzz score and direction (increasing or fading)\n"
            f"  3. Identify the single most important catalyst (positive or negative)\n"
            f"  4. RED FLAGS — insider selling, earnings miss, guidance cut, "
            f"regulatory issues, debt warnings, management change\n"
            f"  5. TAILWINDS — earnings beat, new contracts, sector tailwind, "
            f"government policy support, analyst upgrades\n\n"
            + (
                "For Indian stocks also consider: RBI rate decisions, FII/DII flows, "
                "PLI scheme, Budget impact.\n\n"
                if market == "INDIA" else
                "For US stocks also consider: Fed policy, earnings guidance, "
                "sector rotation, macro data.\n\n"
            ) +
            f"SENTIMENT GATE — Immediately flag as SENTIMENT REJECTED if:\n"
            f"  - Multiple serious red flags present simultaneously\n"
            f"  - Company faces active regulatory investigation or legal action\n"
            f"  - Earnings guidance was just cut significantly\n"
            f"  - Insider selling is unusually heavy\n\n"
            f"Assign each stock: PASS / CAUTION / REJECT"
        ),
        expected_output=(
            "Sentiment report for every ticker with red flags, tailwinds, key catalyst, "
            "and a PASS/CAUTION/REJECT rating. SENTIMENT REJECTED stocks clearly identified."
        ),
        agent=sentiment_analyst,
        context=[task_research],
    )

    # ── Task 4: Master Analyst — Final Quality Gate ───────────────────────────
    task_master = Task(
        description=(
            f"You are the final quality gatekeeper. Today: {today}\n\n"
            f"Review ALL research, technical, and sentiment reports.\n\n"
            f"MANDATORY REJECTION RULES — automatically exclude any stock that:\n"
            f"  ✗ Was marked TECHNICALLY REJECTED or SENTIMENT REJECTED\n"
            f"  ✗ Has RSI > 75 (overbought) or < 25 (freefall)\n"
            f"  ✗ Has Debt-to-Equity > 3\n"
            f"  ✗ Has negative revenue growth\n"
            f"  ✗ Has EMA 20 below EMA 50 AND MACD bearish AND RSI below 45 "
            f"(triple bearish)\n"
            f"  ✗ Has active legal/regulatory issues\n"
            f"  ✗ Had earnings guidance cut in the last 30 days\n\n"
            f"SELECTION CRITERIA (only stocks that PASS all gates):\n"
            f"  ✓ Technical score ≥ 1 (at minimum mild bullish)\n"
            f"  ✓ Sentiment: Bullish or Neutral (NOT Bearish)\n"
            f"  ✓ Confidence: ONLY Medium or High (NEVER Low confidence picks)\n"
            f"  ✓ RSI between 35-68 (trending, not extreme)\n"
            f"  ✓ At least one clear identifiable catalyst or tailwind\n"
            f"  ✓ ROE > 8% (quality threshold)\n\n"
            f"WEIGHTING: Technical (40%) + Fundamentals (30%) + Sentiment (20%) "
            f"+ Risk (10%)\n\n"
            f"If fewer than 3 stocks pass the quality gate, return only those that "
            f"genuinely pass.\n"
            f"DO NOT lower the bar to fill picks — 1 High confidence pick beats "
            f"5 Low confidence picks.\n\n"
            f"For each selected stock write:\n"
            f"  why_buy: 3 specific bullet points with actual numbers\n"
            f"  why_not_buy: 2 honest risk bullet points\n"
            f"  stop_loss_pct: % below entry to set stop loss\n"
            f"  target_pct: realistic upside target % from current price\n\n"
            f"CRITICAL INSTRUCTION: Output ONLY valid JSON. NO MARKDOWN BACKTICKS. "
            f"NO CONVERSATIONAL TEXT. Raw JSON only:\n"
            f'{{\n'
            f'  "market": "{market}",\n'
            f'  "sector": "{sector}",\n'
            f'  "size": "{size}",\n'
            f'  "analysis_date": "{today}",\n'
            f'  "picks": [\n'
            f'    {{\n'
            f'      "ticker": "TICKER",\n'
            f'      "company": "Full Company Name",\n'
            f'      "current_price": 0.00,\n'
            f'      "currency": "INR or USD",\n'
            f'      "why_buy": ["point with numbers", "point with numbers", '
            f'"point with numbers"],\n'
            f'      "why_not_buy": ["risk with context", "risk with context"],\n'
            f'      "technical_signal": "Bullish or Neutral",\n'
            f'      "sentiment": "Bullish or Neutral",\n'
            f'      "confidence": "High or Medium",\n'
            f'      "stop_loss_pct": 8.0,\n'
            f'      "target_pct": 15.0\n'
            f'    }}\n'
            f'  ]\n'
            f'}}'
        ),
        expected_output=(
            f"Valid JSON with market, sector, size, analysis_date={today}, and picks array. "
            f"Only Medium/High confidence stocks with Bullish/Neutral signals. "
            f"Empty picks array is acceptable if no stock passes the quality gate. "
            f"OUTPUT MUST BE PURE JSON WITH NO EXTRA TEXT."
        ),
        agent=master_analyst,
        context=[task_research, task_technical, task_sentiment],
    )

    agents = {
        "researcher":        researcher,
        "data_analyst":      data_analyst,
        "sentiment_analyst": sentiment_analyst,
        "master_analyst":    master_analyst,
    }
    return task_research, task_technical, task_sentiment, task_master, agents