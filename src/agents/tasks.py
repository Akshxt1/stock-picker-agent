# src/agents/tasks.py
#
# Tasks are the actual instructions given to each agent per run.
# Each Task has:
#   - description  : detailed instructions of what to do
#   - expected_output : what the output should look like
#   - agent        : which agent handles this task
#   - context      : which previous tasks' outputs to read (creates the pipeline)

from crewai import Task
from src.agents.agents import (
    create_researcher,
    create_data_analyst,
    create_sentiment_analyst,
    create_master_analyst,
)


def create_tasks(market: str, sector: str, size: str, tickers: list):
    """
    Creates the 4 tasks for one analysis run.

    Args:
        market  : "INDIA" or "US"
        sector  : e.g. "Technology", "Banking"
        size    : "Large", "Mid", "Small", "Mega"
        tickers : list of ticker strings e.g. ["TCS.NS", "INFY.NS", "WIPRO.NS"]

    Returns:
        tuple of (task1, task2, task3, task4, agents_dict)
    """

    # Create fresh agent instances for this run
    researcher        = create_researcher()
    data_analyst      = create_data_analyst()
    sentiment_analyst = create_sentiment_analyst()
    master_analyst    = create_master_analyst()

    ticker_list = ", ".join(tickers)

    # ── Task 1: Research ───────────────────────────────────────────────────

    task_research = Task(
        description=(
            f"You are analysing {size} Cap stocks in the {sector} sector "
            f"of the {market} market.\n\n"
            f"Fetch comprehensive data for the following tickers:\n{ticker_list}\n\n"
            f"For EACH ticker, collect:\n"
            f"  1. Company name, sector, industry, exchange\n"
            f"  2. Current price, day change %, 30-day momentum\n"
            f"  3. Market cap and size classification\n"
            f"  4. Volume data and any volume spikes (ratio > 1.5 is noteworthy)\n"
            f"  5. Key fundamentals: P/E, P/B, ROE, revenue growth, debt-to-equity\n"
            f"  6. Recent news headlines (last 7 days)\n\n"
            f"If a ticker returns an error or no data, note it and continue with the rest.\n"
            f"Present data for ALL tickers before moving on."
        ),

        expected_output=(
            f"A structured summary for each of the {len(tickers)} tickers containing: "
            f"price data, volume analysis, fundamental metrics, market cap size, "
            f"and 3-5 recent news headlines. Flag any tickers with missing data."
        ),

        agent=researcher,
    )

    # ── Task 2: Technical Analysis ─────────────────────────────────────────

    task_technical = Task(
        description=(
            f"Using the research data collected, run a full technical analysis "
            f"for each of these tickers: {ticker_list}\n\n"
            f"For EACH ticker calculate and interpret:\n"
            f"  1. RSI (14) — is it oversold (<30), neutral, or overbought (>70)?\n"
            f"  2. MACD — is momentum bullish or bearish?\n"
            f"  3. Bollinger Bands — is price near the top, bottom, or mid of range?\n"
            f"  4. EMA 20 vs EMA 50 — short-term vs long-term trend direction\n"
            f"  5. ATR — how volatile is this stock?\n"
            f"  6. Overall technical score and signal (Strong Bullish to Strong Bearish)\n\n"
            f"Also review the fundamental metrics from the research:\n"
            f"  - Flag stocks with P/E above 40 as potentially overvalued\n"
            f"  - Flag stocks with debt-to-equity above 2 as high risk\n"
            f"  - Highlight stocks with ROE above 15% as fundamentally strong\n\n"
            f"Rank the tickers from most technically attractive to least."
        ),

        expected_output=(
            f"A ranked list of all tickers with their technical indicator values, "
            f"signal interpretations, overall technical score, and a 1-2 sentence "
            f"technical summary per stock. Include a top 5 shortlist."
        ),

        agent=data_analyst,
        context=[task_research],   # reads Task 1's output
    )

    # ── Task 3: Sentiment Analysis ─────────────────────────────────────────

    task_sentiment = Task(
        description=(
            f"Analyse market sentiment and news for each of these tickers: {ticker_list}\n\n"
            f"For EACH ticker:\n"
            f"  1. Fetch and read the recent news headlines (last 7-14 days)\n"
            f"  2. Get the Finnhub sentiment score (bullish/bearish %)\n"
            f"  3. Identify the dominant news theme (earnings, product launch, "
            f"     regulatory issue, macro factor, sector rotation, etc.)\n"
            f"  4. Assign an overall sentiment: Bullish / Neutral / Bearish\n"
            f"  5. Note any red flags: insider selling, legal issues, earnings miss, "
            f"     management change, etc.\n"
            f"  6. Note any tailwinds: strong earnings, new contracts, sector boom, "
            f"     government policy support, etc.\n\n"
            f"For Indian stocks, also consider:\n"
            f"  - RBI policy impact on banking/NBFC stocks\n"
            f"  - Government capex and PLI scheme beneficiaries\n"
            f"  - FII/DII flow trends in the sector\n\n"
            f"For US stocks, also consider:\n"
            f"  - Fed rate environment impact\n"
            f"  - Earnings season beat/miss patterns\n"
            f"  - Sector rotation signals"
        ),

        expected_output=(
            f"A sentiment report for each ticker with: overall sentiment label, "
            f"key news themes, top tailwinds, top risks, and a 2-3 sentence "
            f"narrative explaining the market mood around each stock."
        ),

        agent=sentiment_analyst,
        context=[task_research],   # reads Task 1's output for news data
    )

    # ── Task 4: Master Decision ────────────────────────────────────────────

    task_master = Task(
        description=(
            f"You are the final decision maker. Review all the analysis and select "
            f"the TOP 3-5 stocks from the {size} Cap {sector} sector in the {market} market.\n\n"
            f"Your selection criteria (weight each):\n"
            f"  - Technical signal     : 35% weight\n"
            f"  - Fundamentals quality : 30% weight\n"
            f"  - Sentiment / news     : 20% weight\n"
            f"  - Risk assessment      : 15% weight\n\n"
            f"For each selected stock write:\n"
            f"  WHY BUY     : 3-4 bullet points. Be specific — use actual numbers "
            f"(RSI value, P/E ratio, growth rate, etc.)\n"
            f"  WHY NOT BUY : 2-3 bullet points. Honest risks a retail investor must know.\n"
            f"  CONFIDENCE  : High / Medium / Low\n\n"
            f"Output your response as valid JSON in this exact format:\n"
            f"{{\n"
            f"  \"market\": \"{market}\",\n"
            f"  \"sector\": \"{sector}\",\n"
            f"  \"size\": \"{size}\",\n"
            f"  \"analysis_date\": \"YYYY-MM-DD\",\n"
            f"  \"picks\": [\n"
            f"    {{\n"
            f"      \"ticker\": \"TICKER\",\n"
            f"      \"company\": \"Company Name\",\n"
            f"      \"current_price\": 0.00,\n"
            f"      \"currency\": \"INR or USD\",\n"
            f"      \"why_buy\": [\"point 1\", \"point 2\", \"point 3\"],\n"
            f"      \"why_not_buy\": [\"risk 1\", \"risk 2\"],\n"
            f"      \"technical_signal\": \"Bullish/Bearish/Neutral\",\n"
            f"      \"sentiment\": \"Bullish/Bearish/Neutral\",\n"
            f"      \"confidence\": \"High/Medium/Low\"\n"
            f"    }}\n"
            f"  ]\n"
            f"}}"
        ),

        expected_output=(
            f"Valid JSON with market, sector, size, analysis_date, and a picks array "
            f"containing 3-5 stocks. Each pick must have ticker, company, current_price, "
            f"currency, why_buy list, why_not_buy list, technical_signal, sentiment, "
            f"and confidence fields."
        ),

        agent=master_analyst,
        context=[task_research, task_technical, task_sentiment],  # reads ALL 3 prior tasks
    )

    agents = {
        "researcher":        researcher,
        "data_analyst":      data_analyst,
        "sentiment_analyst": sentiment_analyst,
        "master_analyst":    master_analyst,
    }

    return task_research, task_technical, task_sentiment, task_master, agents