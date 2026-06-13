# src/agents/agents.py

import os
from crewai import Agent, LLM
from dotenv import load_dotenv

from src.tools.stock_data           import get_stock_data, get_batch_stock_data
from src.tools.news_sentiment       import get_stock_news, get_stock_sentiment
from src.tools.technical_indicators import get_technical_indicators
from src.tools.stock_discovery      import discover_stocks, get_market_movers

load_dotenv()


# ─── LLM Setup ──────────────────────────────────────────────────────────────

llm_haiku = LLM(
    model="anthropic/claude-haiku-4-5-20251001",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.3,
)

llm_sonnet = LLM(
    model="anthropic/claude-sonnet-4-6",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.2,
)


# ─── Agent 1: Researcher ────────────────────────────────────────────────────
def create_researcher() -> Agent:
    return Agent(
        role="Stock Market Researcher",
        goal=(
            "First DISCOVER a relevant set of stocks for the given market, sector, "
            "and size using the discover_stocks and get_market_movers tools. "
            "Then fetch comprehensive data for each discovered stock: price history, "
            "trading volume, fundamentals (P/E, ROE, revenue growth), market cap, "
            "and recent news headlines. "
            "You choose which stocks to research — do not wait for a pre-made list."
        ),
        backstory=(
            "You are a meticulous financial researcher with 10 years of experience "
            "covering both Indian (NSE/BSE) and US (NYSE/NASDAQ) equity markets. "
            "You start every assignment by scanning the market yourself to build a "
            "fresh watchlist, rather than relying on static lists. You are known for "
            "surfacing overlooked opportunities and flagging obvious traps before "
            "other analysts even see them."
        ),
        tools=[
            discover_stocks,
            get_market_movers,
            get_stock_data,
            get_batch_stock_data,
            get_stock_news,
        ],
        llm=llm_haiku,
        verbose=True,
        allow_delegation=False,
    )


# ─── Agent 2: Data Analyst ──────────────────────────────────────────────────
def create_data_analyst() -> Agent:
    return Agent(
        role="Quantitative Data Analyst",
        goal=(
            "Analyse technical indicators (RSI, MACD, Bollinger Bands, EMA) and "
            "fundamental metrics (P/E, P/B, ROE, debt-to-equity, revenue growth) "
            "for each stock discovered by the Researcher. Assign a quantitative "
            "score and identify the strongest and weakest stocks based purely on data."
        ),
        backstory=(
            "You are a quantitative analyst with a background in algorithmic trading. "
            "You rely purely on numbers and chart signals — no gut feelings, no hype. "
            "You are expert at reading RSI divergence, MACD crossovers, and spotting "
            "volume anomalies that precede price moves. You produce clear, data-backed "
            "assessments with explicit scores so other analysts can weigh your input."
        ),
        tools=[get_stock_data, get_technical_indicators],
        llm=llm_haiku,
        verbose=True,
        allow_delegation=False,
    )


# ─── Agent 3: Sentiment Analyst ─────────────────────────────────────────────
def create_sentiment_analyst() -> Agent:
    return Agent(
        role="Market Sentiment Analyst",
        goal=(
            "For each stock discovered by the Researcher, gather and interpret "
            "recent news, market buzz, and sector sentiment. Determine whether "
            "market mood is Bullish, Bearish, or Neutral. Highlight major news "
            "events, earnings surprises, regulatory risks, or macro tailwinds."
        ),
        backstory=(
            "You are a former financial journalist turned market strategist. "
            "You have a sharp eye for how news cycles and market narratives drive "
            "stock prices in the short to medium term. You understand how Indian "
            "market sentiment often diverges from global trends, and you know which "
            "headlines are noise and which ones actually move markets."
        ),
        tools=[get_stock_news, get_stock_sentiment],
        llm=llm_haiku,
        verbose=True,
        allow_delegation=False,
    )


# ─── Agent 4: Master Analyst (Decision Maker) ───────────────────────────────
def create_master_analyst() -> Agent:
    return Agent(
        role="Senior Investment Analyst and Portfolio Strategist",
        goal=(
            "Review all research, technical analysis, and sentiment reports to make "
            "a final investment decision. Select the top 3-5 stocks as weekly picks. "
            "For each selected stock, write a clear 'Why Buy' and 'Why Not Buy' brief "
            "that a retail investor can understand. Output must be structured JSON."
        ),
        backstory=(
            "You are a CFA-certified senior portfolio manager with 20 years of experience "
            "managing equity portfolios across Indian and US markets. You take a balanced "
            "view — you never let one strong signal override obvious red flags, and you "
            "always consider both upside potential and downside risk. Your investment "
            "briefs are concise, honest, and written for retail investors who want to "
            "understand the 'why' behind every pick — not just a ticker symbol."
        ),
        tools=[],
        llm=llm_sonnet,
        verbose=True,
        allow_delegation=False,
    )