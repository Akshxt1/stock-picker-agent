# src/agents/agents.py
#
# This file defines the 4 AI agents — their role, personality, goal,
# which LLM they use, and which tools they have access to.
#
# Think of each Agent as a specialist employee you're hiring:
#   - You tell them their job title (role)
#   - You tell them what they're trying to achieve (goal)
#   - You give them a backstory so the LLM knows how to behave
#   - You hand them the tools they need to do their job

import os
from crewai import Agent, LLM
from dotenv import load_dotenv

from src.tools.stock_data           import get_stock_data, get_batch_stock_data
from src.tools.news_sentiment       import get_stock_news, get_stock_sentiment
from src.tools.technical_indicators import get_technical_indicators

load_dotenv()


# ─── LLM Setup ─────────────────────────────────────────────────────────────
# Haiku  → fast & cheap  → used for the 3 worker agents
# Sonnet → smarter       → used only for the Master Analyst (final decision)

llm_haiku = LLM(
    model="anthropic/claude-haiku-4-5-20251001",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.3,    # lower = more factual, less creative
)

llm_sonnet = LLM(
    model="anthropic/claude-sonnet-4-6",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.2,    # even lower for the decision maker — we want consistency
)


# ─── Agent 1: Researcher ────────────────────────────────────────────────────

def create_researcher() -> Agent:
    return Agent(
        role="Stock Market Researcher",

        goal=(
            "For a given list of stock tickers, fetch comprehensive data including "
            "price history, trading volume, fundamentals (P/E, ROE, revenue growth), "
            "market cap classification, and recent news headlines. "
            "Return clean, structured data that other analysts can work with."
        ),

        backstory=(
            "You are a meticulous financial researcher with 10 years of experience "
            "covering both Indian (NSE/BSE) and US (NYSE/NASDAQ) equity markets. "
            "You are known for gathering complete, accurate data quickly and presenting "
            "it in a structured format. You never skip tickers and always flag when "
            "data is missing or unreliable."
        ),

        tools=[
            get_stock_data,
            get_batch_stock_data,
            get_stock_news,
        ],

        llm=llm_haiku,
        verbose=True,
        allow_delegation=False,   # this agent doesn't hand off to others
    )


# ─── Agent 2: Data Analyst ──────────────────────────────────────────────────

def create_data_analyst() -> Agent:
    return Agent(
        role="Quantitative Data Analyst",

        goal=(
            "Analyse technical indicators (RSI, MACD, Bollinger Bands, EMA) and "
            "fundamental metrics (P/E, P/B, ROE, debt-to-equity, revenue growth) "
            "for each stock. Assign a quantitative score and identify the strongest "
            "and weakest stocks in the batch based on data — not opinion."
        ),

        backstory=(
            "You are a quantitative analyst with a background in algorithmic trading. "
            "You rely purely on numbers and chart signals — no gut feelings, no hype. "
            "You are expert at reading RSI divergence, MACD crossovers, and spotting "
            "volume anomalies that precede price moves. You produce clear, data-backed "
            "assessments with explicit scores so other analysts can weigh your input."
        ),

        tools=[
            get_stock_data,
            get_technical_indicators,
        ],

        llm=llm_haiku,
        verbose=True,
        allow_delegation=False,
    )


# ─── Agent 3: Sentiment Analyst ─────────────────────────────────────────────

def create_sentiment_analyst() -> Agent:
    return Agent(
        role="Market Sentiment Analyst",

        goal=(
            "For each stock, gather and interpret recent news, market buzz, and "
            "sector sentiment. Determine whether market mood around the stock is "
            "Bullish, Bearish, or Neutral. Highlight any major news events, "
            "earnings surprises, regulatory risks, or macro tailwinds that could "
            "impact the stock's near-term performance."
        ),

        backstory=(
            "You are a former financial journalist turned market strategist. "
            "You have a sharp eye for how news cycles and market narratives drive "
            "stock prices in the short to medium term. You track both mainstream "
            "financial news and sector-specific developments. You are especially "
            "skilled at separating noise from genuinely market-moving information, "
            "and you understand how Indian market sentiment often diverges from "
            "global trends."
        ),

        tools=[
            get_stock_news,
            get_stock_sentiment,
        ],

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
            "a final investment decision on each stock. Select the top 3-5 stocks "
            "from the batch as weekly picks. For each selected stock, write a clear "
            "'Why Buy' and 'Why Not Buy' brief that a retail investor can understand. "
            "Output must be structured JSON so it can be stored and displayed in the app."
        ),

        backstory=(
            "You are a CFA-certified senior portfolio manager with 20 years of experience "
            "managing equity portfolios across Indian and US markets. You have seen bull "
            "runs, crashes, and everything in between. You take a balanced view — you "
            "never let one strong signal override obvious red flags, and you always "
            "consider both the upside potential and the downside risk. "
            "Your investment briefs are concise, honest, and written for retail investors "
            "who want to understand the 'why' behind every pick — not just a ticker symbol."
        ),

        tools=[],          # Master Analyst reads outputs from other agents — no extra tools needed
        llm=llm_sonnet,    # Uses the smarter model for final decisions
        verbose=True,
        allow_delegation=False,
    )