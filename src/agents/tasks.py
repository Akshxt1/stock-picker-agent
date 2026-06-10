# src/agents/tasks.py  — v2 (Stronger, Stricter Quality Gate)
# Agents now ONLY recommend stocks with confirmed bullish signals.
# Low confidence and bearish picks are REJECTED at the Master Analyst stage.

from crewai import Task
from src.agents.agents import (
    create_researcher, create_data_analyst,
    create_sentiment_analyst, create_master_analyst,
)
from datetime import datetime


def create_tasks(market: str, sector: str, size: str, tickers: list):
    researcher        = create_researcher()
    data_analyst      = create_data_analyst()
    sentiment_analyst = create_sentiment_analyst()
    master_analyst    = create_master_analyst()

    ticker_list = ", ".join(tickers)
    today       = datetime.today().strftime("%Y-%m-%d")

    # ── Task 1: Research ──────────────────────────────────────────────────────
    task_research = Task(
        description=(
            f"Today's date: {today}\n"
            f"Analyse {size} Cap stocks in the {sector} sector of the {market} market.\n\n"
            f"Fetch data for ALL these tickers: {ticker_list}\n\n"
            f"For EACH ticker collect:\n"
            f"  1. Company name, exchange, sector, industry\n"
            f"  2. Current price, day change %, 30-day momentum\n"
            f"  3. Market cap and classification\n"
            f"  4. Volume spike ratio (flag anything above 1.5x as notable)\n"
            f"  5. Fundamentals: P/E, P/B, ROE, revenue growth YoY, debt-to-equity, EPS\n"
            f"  6. 52-week high and low — calculate how far current price is from each\n"
            f"  7. Recent news headlines (last 7 days)\n\n"
            f"Flag immediately if:\n"
            f"  - Debt-to-equity > 3 (HIGH RISK)\n"
            f"  - Revenue growth < 0% (DECLINING)\n"
            f"  - 30-day momentum < -15% (SEVERE DOWNTREND)\n"
            f"  - ROE < 5% (POOR QUALITY)\n\n"
            f"Present structured data for every ticker before continuing."
        ),
        expected_output=(
            f"Structured data for each of the {len(tickers)} tickers with all metrics listed. "
            f"Clearly flag any HIGH RISK, DECLINING, or SEVERE DOWNTREND stocks."
        ),
        agent=researcher,
    )

    # ── Task 2: Technical Analysis ────────────────────────────────────────────
    task_technical = Task(
        description=(
            f"Run full technical analysis for: {ticker_list}\n\n"
            f"For EACH ticker calculate:\n"
            f"  1. RSI (14) — classify: <30 oversold, 30-45 weak, 45-55 neutral, 55-70 strong, >70 overbought\n"
            f"  2. MACD — bullish crossover, bearish crossover, or divergence\n"
            f"  3. Bollinger Bands — band position and squeeze/expansion\n"
            f"  4. EMA 20 vs EMA 50 — trend direction and strength\n"
            f"  5. ATR — volatility rating (Low/Medium/High/Extreme)\n"
            f"  6. Volume trend — increasing/decreasing vs 20-day average\n"
            f"  7. Technical score (-4 to +4) and overall signal\n\n"
            f"QUALITY GATE — Mark a stock as TECHNICALLY REJECTED if:\n"
            f"  - RSI > 75 (dangerously overbought)\n"
            f"  - RSI < 25 (in freefall, not a recovery play)\n"
            f"  - EMA 20 AND EMA 50 both pointing sharply downward\n"
            f"  - MACD histogram deeply negative with no sign of reversal\n"
            f"  - Technical score below -2\n\n"
            f"Rank ALL tickers from strongest to weakest technical setup.\n"
            f"Produce a SHORTLIST of the top 5 technically sound stocks.\n"
            f"Be ruthless — it is better to return 2 good picks than 5 mediocre ones."
        ),
        expected_output=(
            f"Ranked list of all tickers with full technical data, signal labels, "
            f"and a final SHORTLIST of top 5 with TECHNICALLY REJECTED stocks clearly marked."
        ),
        agent=data_analyst,
        context=[task_research],
    )

    # ── Task 3: Sentiment & Risk Analysis ────────────────────────────────────
    task_sentiment = Task(
        description=(
            f"Analyse sentiment and risk for: {ticker_list}\n\n"
            f"For EACH ticker:\n"
            f"  1. News sentiment: Bullish / Neutral / Bearish with key themes\n"
            f"  2. Market buzz score and direction (increasing or fading)\n"
            f"  3. Identify the single most important catalyst (positive or negative)\n"
            f"  4. RED FLAGS — insider selling, earnings miss, guidance cut, "
            f"     regulatory issues, debt warnings, management change\n"
            f"  5. TAILWINDS — earnings beat, new contracts, sector tailwind, "
            f"     government policy support, analyst upgrades\n\n"
            f"{'For Indian stocks also consider: RBI rate decisions, FII/DII flows, PLI scheme, Budget impact.' if market == 'INDIA' else ''}\n"
            f"{'For US stocks also consider: Fed policy, earnings guidance, sector rotation, macro data.' if market == 'US' else ''}\n\n"
            f"SENTIMENT GATE — Immediately flag as SENTIMENT REJECTED if:\n"
            f"  - Multiple serious red flags present simultaneously\n"
            f"  - Company faces active regulatory investigation or legal action\n"
            f"  - Earnings guidance was just cut significantly\n"
            f"  - Insider selling is unusually heavy\n\n"
            f"Assign each stock: PASS / CAUTION / REJECT"
        ),
        expected_output=(
            f"Sentiment report for every ticker with red flags, tailwinds, key catalyst, "
            f"and a PASS/CAUTION/REJECT rating. Clearly identify SENTIMENT REJECTED stocks."
        ),
        agent=sentiment_analyst,
        context=[task_research],
    )

    # ── Task 4: Master Analyst — Strict Quality Gate ──────────────────────────
    task_master = Task(
        description=(
            f"You are the final quality gatekeeper. Today: {today}\n\n"
            f"Review ALL research, technical, and sentiment reports.\n\n"
            f"MANDATORY REJECTION RULES — automatically exclude any stock that:\n"
            f"  ✗ Was marked TECHNICALLY REJECTED or SENTIMENT REJECTED\n"
            f"  ✗ Has RSI > 75 (overbought) or < 25 (freefall)\n"
            f"  ✗ Has Debt-to-Equity > 3\n"
            f"  ✗ Has negative revenue growth\n"
            f"  ✗ Has EMA 20 below EMA 50 AND MACD bearish AND RSI below 45 (triple bearish)\n"
            f"  ✗ Has active legal/regulatory issues\n"
            f"  ✗ Had earnings guidance cut in the last 30 days\n\n"
            f"SELECTION CRITERIA (only stocks that PASS all gates):\n"
            f"  ✓ Technical score ≥ 1 (at minimum mild bullish)\n"
            f"  ✓ Sentiment: Bullish or Neutral (NOT Bearish)\n"
            f"  ✓ Confidence: ONLY Medium or High (NEVER Low confidence picks)\n"
            f"  ✓ RSI between 35-68 (trending, not extreme)\n"
            f"  ✓ At least one clear identifiable catalyst or tailwind\n"
            f"  ✓ ROE > 8% (quality threshold)\n\n"
            f"WEIGHTING: Technical (40%) + Fundamentals (30%) + Sentiment (20%) + Risk (10%)\n\n"
            f"If fewer than 3 stocks pass the quality gate, return only those that genuinely pass.\n"
            f"DO NOT lower the bar to fill up picks — 1 High confidence pick beats 5 Low confidence picks.\n\n"
            f"For each selected stock write:\n"
            f"  why_buy: 3 specific bullet points with actual numbers (RSI, P/E, growth rate, etc.)\n"
            f"  why_not_buy: 2 honest risk bullet points\n"
            f"  stop_loss_pct: how many % below entry to set stop loss (e.g. 8 means 8% below)\n"
            f"  target_pct: upside target % from current price (realistic, data-backed)\n\n"
            f"Output ONLY valid JSON:\n"
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
            f'      "why_buy": ["point with numbers", "point with numbers", "point with numbers"],\n'
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
            f"Empty picks array is acceptable if no stock passes the quality gate."
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