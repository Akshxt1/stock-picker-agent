# src/tools/news_sentiment.py
#
# This tool fetches recent news headlines and sentiment scores
# for any stock using the Finnhub API (free tier: 60 calls/min).
#
# Agents use this to understand what the market is saying about a stock
# beyond just price and volume numbers.

import os
from datetime import datetime, timedelta

import finnhub
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()   # reads your .env file so FINNHUB_API_KEY is available

# ─── Create one shared Finnhub client ──────────────────────────────────────
# We create it once here so every tool call reuses the same connection

def get_finnhub_client():
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("FINNHUB_API_KEY not found. Check your .env file.")
    return finnhub.Client(api_key=api_key)


# ─── Helper: format ticker for Finnhub ─────────────────────────────────────
# yfinance uses RELIANCE.NS — but Finnhub uses NSE:RELIANCE
# This function converts between the two formats

def to_finnhub_symbol(ticker: str) -> str:
    """
    Convert yfinance ticker format to Finnhub format.

    Examples:
      RELIANCE.NS  →  NSE:RELIANCE
      TCS.BO       →  BSE:TCS
      AAPL         →  AAPL  (US stocks stay the same)
    """
    if ticker.endswith(".NS"):
        return "NSE:" + ticker.replace(".NS", "")
    elif ticker.endswith(".BO"):
        return "BSE:" + ticker.replace(".BO", "")
    return ticker   # US stocks — no change needed


# ─── Tool 1: Fetch recent news headlines ───────────────────────────────────

@tool("Stock News Fetcher")
def get_stock_news(ticker: str, days_back: int = 7) -> dict:
    """
    Fetches recent news headlines for a stock from the last N days.
    Returns headline, source, date, URL and a summary for each article.

    Ticker format:
      - Indian NSE: RELIANCE.NS, TCS.NS
      - Indian BSE: RELIANCE.BO
      - US stocks:  AAPL, MSFT, TSLA
    """
    try:
        client = get_finnhub_client()
        symbol = to_finnhub_symbol(ticker)

        # Date range — from X days ago to today
        today     = datetime.today()
        from_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        to_date   = today.strftime("%Y-%m-%d")

        raw_news = client.company_news(symbol, _from=from_date, to=to_date)

        if not raw_news:
            return {
                "ticker":   ticker,
                "symbol":   symbol,
                "articles": [],
                "note":     "No news found for this period. Stock may have limited coverage."
            }

        # Clean and limit to 10 most recent articles
        articles = []
        for item in raw_news[:10]:
            articles.append({
                "headline": item.get("headline", ""),
                "source":   item.get("source", ""),
                "date":     datetime.fromtimestamp(item.get("datetime", 0)).strftime("%Y-%m-%d"),
                "summary":  item.get("summary", "")[:300],  # first 300 chars only
                "url":      item.get("url", ""),
            })

        return {
            "ticker":        ticker,
            "symbol":        symbol,
            "period":        f"Last {days_back} days",
            "article_count": len(articles),
            "articles":      articles,
        }

    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ─── Tool 2: Fetch sentiment score ─────────────────────────────────────────

@tool("Stock Sentiment Scorer")
def get_stock_sentiment(ticker: str) -> dict:
    """
    Derives sentiment from price momentum, volume, and available news.
    Works for both Indian and US stocks without requiring a paid API.
    """
    try:
        import yfinance as yf

        stock   = yf.Ticker(ticker)
        info    = stock.info
        hist    = stock.history(period="1mo")

        if hist.empty:
            return {"ticker": ticker, "overall": "Neutral", "note": "No data"}

        # Price momentum signals
        price_now   = hist["Close"].iloc[-1]
        price_start = hist["Close"].iloc[0]
        momentum    = ((price_now - price_start) / price_start) * 100

        avg_vol   = hist["Volume"].mean()
        last_vol  = hist["Volume"].iloc[-1]
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1.0

        # News from yfinance (works for both markets)
        raw_news = stock.news or []
        headlines = [
            n.get("content", {}).get("title", "") or n.get("title", "")
            for n in raw_news[:5]
        ]
        headlines = [h for h in headlines if h]

        # Simple scoring
        score = 0
        if momentum > 3:   score += 2
        elif momentum > 0: score += 1
        elif momentum < -3: score -= 2
        else:              score -= 1

        if vol_ratio > 2 and momentum < 0: score -= 1
        if vol_ratio > 2 and momentum > 0: score += 1

        label = "Bullish" if score >= 2 else "Bearish" if score <= -1 else "Neutral"

        return {
            "ticker":            ticker,
            "overall_sentiment": label,
            "momentum_1mo_pct":  round(momentum, 2),
            "volume_spike":      round(vol_ratio, 2),
            "recent_headlines":  headlines,
            "sentiment_score":   score,
        }

    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ─── Quick test ─────────────────────────────────────────────────────────────
# Run with: uv run src/tools/news_sentiment.py

if __name__ == "__main__":
    print("=" * 50)
    print("Testing news fetch for TCS (Indian stock)...")
    result = get_stock_news.func("TCS.NS", 7)
    print(f"  Articles found : {result.get('article_count', 0)}")
    for a in result.get("articles", [])[:3]:
        print(f"  [{a['date']}] {a['headline'][:80]}")

    print("\nTesting sentiment for Apple (US stock)...")
    sentiment = get_stock_sentiment.func("AAPL")
    for key, val in sentiment.items():
        print(f"  {key:25} : {val}")