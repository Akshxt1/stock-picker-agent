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
            f"DATA FORMAT NOTE (read before filtering):\n"
            f"  - ROE is expressed as a percentage, e.g. '21.41%' means 21.41% return on equity.\n"
            f"  - RevGrowth is expressed as a percentage, e.g. '15.00%' means 15% YoY growth.\n"
            f"  - Debt/Eq is a plain ratio, e.g. '3.35' means ₹3.35 of debt per ₹1.00 of equity.\n\n"
            f"STEP 3 — FIRST PASS FILTER:\n"
            f"  Flag and DROP any stock with:\n"
            f"  - Debt-to-equity ratio > 3.0 (HIGH RISK)\n"
            f"  - Revenue growth < 0% (DECLINING)\n"
            f"  - 30-day momentum < -15% (SEVERE DOWNTREND)\n"
            f"  - ROE < 8% (POOR QUALITY)\n"
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
            f"  [-] Was marked TECHNICALLY REJECTED or SENTIMENT REJECTED\n"
            f"  [-] Has RSI > 75 (overbought) or < 25 (freefall)\n"
            f"  [-] Has Debt-to-Equity > 3\n"
            f"  [-] Has negative revenue growth\n"
            f"  [-] Has EMA 20 below EMA 50 AND MACD bearish AND RSI below 45 "
            f"(triple bearish)\n"
            f"  [-] Has active legal/regulatory issues\n"
            f"  [-] Had earnings guidance cut in the last 30 days\n\n"
            f"SELECTION CRITERIA (only stocks that PASS all gates):\n"
            f"  [+] Technical score ≥ 1 (at minimum mild bullish)\n"
            f"  [+] Sentiment: Bullish or Neutral (NOT Bearish)\n"
            f"  [+] Confidence: ONLY Medium or High (NEVER Low confidence picks)\n"
            f"  [+] RSI between 35-68 (trending, not extreme)\n"
            f"  [+] At least one clear identifiable catalyst or tailwind\n"
            f"  [+] ROE > 8% (quality threshold)\n\n"
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
            f"  target_pct: realistic upside target % from current price\n"
            f"  roe, debt_to_equity, revenue_growth, pe_ratio: COPY the exact "
            f"figures the Researcher collected for this stock (keep the format, "
            f"e.g. ROE '21.41%', Debt/Eq '3.35', RevGrowth '15.00%', P/E '28.4'). "
            f"Use 'N/A' only if the Researcher genuinely had no value.\n\n"
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
            f'      "roe": "21.41%",\n'
            f'      "debt_to_equity": "3.35",\n'
            f'      "revenue_growth": "15.00%",\n'
            f'      "pe_ratio": "28.4",\n'
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


def create_single_stock_tasks(ticker: str):
    """Full 4-agent pipeline focused on ONE already-chosen ticker (no discovery).

    Powers the on-demand 'Deep Analysis' button on the stock detail page.
    """
    researcher        = create_researcher()
    data_analyst      = create_data_analyst()
    sentiment_analyst = create_sentiment_analyst()
    master_analyst    = create_master_analyst()

    today    = datetime.today().strftime("%Y-%m-%d")
    market   = "INDIA" if ticker.upper().endswith((".NS", ".BO")) else "US"
    currency = "INR" if market == "INDIA" else "USD"

    task_research = Task(
        description=(
            f"Today's date: {today}\n"
            f"Deep-research this single stock: {ticker} (market: {market}).\n\n"
            f"Use get_stock_data to pull fundamentals + price, and get_stock_news for headlines.\n"
            f"Report clearly:\n"
            f"  1. Company name, sector, industry\n"
            f"  2. Current price, day change %, 30-day momentum, volume spike\n"
            f"  3. Market cap and size classification\n"
            f"  4. Fundamentals: P/E, P/B, ROE, revenue growth YoY, debt-to-equity, EPS\n"
            f"  5. 52-week high/low and distance from each\n"
            f"  6. Recent news headlines (last 7 days)\n\n"
            f"DATA FORMAT: ROE/RevGrowth are percentages (e.g. '21.41%'); "
            f"Debt/Eq is a ratio (e.g. '3.35')."
        ),
        expected_output=f"A complete fundamental + price + news profile for {ticker}.",
        agent=researcher,
    )

    task_technical = Task(
        description=(
            f"Run a full technical read on {ticker} using get_technical_indicators.\n"
            f"Report RSI(14) with label, MACD signal, Bollinger position, EMA20 vs EMA50 trend, "
            f"ATR volatility, volume trend, a technical score (-4 to +4), and an overall "
            f"Bullish / Neutral / Bearish signal with a one-line justification."
        ),
        expected_output=f"Technical breakdown + signal for {ticker}.",
        agent=data_analyst,
        context=[task_research],
    )

    task_sentiment = Task(
        description=(
            f"Assess news + market sentiment for {ticker} using get_stock_news and "
            f"get_stock_sentiment.\n"
            f"Report: overall sentiment (Bullish/Neutral/Bearish), the single most important "
            f"catalyst, red flags, tailwinds, and a PASS/CAUTION/REJECT rating with reasoning."
        ),
        expected_output=f"Sentiment + risk assessment for {ticker}.",
        agent=sentiment_analyst,
        context=[task_research],
    )

    task_master = Task(
        description=(
            f"You are the CEO-level decision maker. Today: {today}\n"
            f"Synthesise the research, technical, and sentiment reports for {ticker} into a "
            f"single clear investment brief a retail investor can act on.\n\n"
            f"Weigh Technical (40%) + Fundamentals (30%) + Sentiment (20%) + Risk (10%).\n"
            f"Be honest — if it's not a buy, say HOLD or AVOID and explain why.\n\n"
            f"For the stock write:\n"
            f"  why_buy: 3 specific bullets WITH actual numbers from the reports\n"
            f"  why_not_buy: 2 honest risk bullets\n"
            f"  stop_loss_pct / target_pct: realistic % levels from current price\n"
            f"  roe, debt_to_equity, revenue_growth, pe_ratio: copy the Researcher's figures\n\n"
            f"CRITICAL: Output ONLY valid JSON. NO MARKDOWN. NO extra text:\n"
            f'{{\n'
            f'  "market": "{market}",\n'
            f'  "sector": "infer from research",\n'
            f'  "size": "infer from market cap",\n'
            f'  "analysis_date": "{today}",\n'
            f'  "picks": [\n'
            f'    {{\n'
            f'      "ticker": "{ticker}",\n'
            f'      "company": "Full Company Name",\n'
            f'      "current_price": 0.00,\n'
            f'      "currency": "{currency}",\n'
            f'      "roe": "21.41%",\n'
            f'      "debt_to_equity": "3.35",\n'
            f'      "revenue_growth": "15.00%",\n'
            f'      "pe_ratio": "28.4",\n'
            f'      "why_buy": ["point with numbers", "point with numbers", "point with numbers"],\n'
            f'      "why_not_buy": ["risk with context", "risk with context"],\n'
            f'      "technical_signal": "Bullish / Neutral / Bearish",\n'
            f'      "sentiment": "Bullish / Neutral / Bearish",\n'
            f'      "confidence": "High / Medium / Low",\n'
            f'      "stop_loss_pct": 8.0,\n'
            f'      "target_pct": 15.0\n'
            f'    }}\n'
            f'  ]\n'
            f'}}'
        ),
        expected_output=(
            f"Valid JSON for {ticker} with a single fully-populated pick. PURE JSON, no extra text."
        ),
        agent=master_analyst,
        context=[task_research, task_technical, task_sentiment],
    )

    agents = [researcher, data_analyst, sentiment_analyst, master_analyst]
    return task_research, task_technical, task_sentiment, task_master, agents