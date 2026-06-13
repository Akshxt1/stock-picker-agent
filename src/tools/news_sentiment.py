# src/tools/news_sentiment.py
# News: Finnhub for US stocks, yfinance fallback for Indian (.NS/.BO) stocks
# Sentiment: keyword scoring on headlines from whichever source works

from crewai.tools import tool
import requests
import os
import time
import yfinance as yf
from datetime import datetime, timedelta

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")


def _is_indian_ticker(ticker: str) -> bool:
    return ticker.upper().endswith((".NS", ".BO"))


def _fetch_headlines_yfinance(ticker: str) -> list[str]:
    """Fetch news headlines via yfinance (works for NSE/BSE tickers, no API key needed)."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news or []
        headlines = []
        for item in news[:6]:
            # yfinance news structure: item["content"]["title"] in newer versions
            title = (
                item.get("title")
                or item.get("content", {}).get("title")
                or ""
            )
            if title:
                headlines.append(title)
        return headlines
    except Exception:
        return []


def _fetch_headlines_finnhub(ticker: str) -> list[str]:
    """Fetch news headlines via Finnhub (works for US tickers)."""
    if not FINNHUB_API_KEY:
        return []
    try:
        today     = datetime.today()
        date_to   = today.strftime("%Y-%m-%d")
        date_from = (today - timedelta(days=14)).strftime("%Y-%m-%d")
        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={ticker}&from={date_from}&to={date_to}&token={FINNHUB_API_KEY}"
        )
        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                return [item.get("headline", "") for item in data[:6] if item.get("headline")]
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt == 2:
                    return []
                time.sleep(2)
    except Exception:
        return []
    return []


def _score_sentiment(headlines: list[str]) -> str:
    positive_words = {
        "beat", "surge", "growth", "upgrade", "strong", "record",
        "profit", "win", "rise", "boost", "expansion", "acquisition",
        "outperform", "rally", "gain", "up",
    }
    negative_words = {
        "miss", "drop", "loss", "downgrade", "weak", "cut",
        "fall", "risk", "crash", "lawsuit", "debt", "fraud",
        "investigation", "decline", "down", "layoff", "recall",
    }
    pos = sum(1 for h in headlines for w in positive_words if w in h.lower())
    neg = sum(1 for h in headlines for w in negative_words if w in h.lower())
    if pos > neg + 1:
        return "Bullish"
    elif neg > pos + 1:
        return "Bearish"
    return "Neutral"


def _get_headlines(ticker: str) -> list[str]:
    """Route to the right news source based on ticker type."""
    if _is_indian_ticker(ticker):
        headlines = _fetch_headlines_yfinance(ticker)
        # Fallback to Finnhub anyway in case yfinance has nothing
        if not headlines:
            headlines = _fetch_headlines_finnhub(ticker)
    else:
        headlines = _fetch_headlines_finnhub(ticker)
        if not headlines:
            headlines = _fetch_headlines_yfinance(ticker)
    return headlines


@tool("Get Stock News")
def get_stock_news(ticker: str) -> str:
    """
    Fetches the latest news headlines for a given stock ticker.
    Uses yfinance for Indian stocks (.NS/.BO), Finnhub for US stocks.
    """
    headlines = _get_headlines(ticker)
    if not headlines:
        return f"No recent news found for {ticker}."
    return "\n".join(f"- {h}" for h in headlines)


@tool("Get Stock Sentiment")
def get_stock_sentiment(ticker: str) -> dict:
    """
    Returns structured sentiment data: overall_sentiment, recent_headlines.
    Uses yfinance for Indian stocks (.NS/.BO), Finnhub for US stocks.
    """
    headlines = _get_headlines(ticker)
    overall   = _score_sentiment(headlines) if headlines else "Neutral"

    return {
        "ticker":            ticker,
        "overall_sentiment": overall,
        "recent_headlines":  headlines,
        "source":            "yfinance" if _is_indian_ticker(ticker) else "finnhub",
    }