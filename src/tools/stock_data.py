# src/tools/stock_data.py
#
# This file is a TOOL — think of it as a function the AI agents can call
# whenever they need real stock data. The @tool decorator is what tells
# CrewAI "hey, agents can use this".

import yfinance as yf
from crewai.tools import tool


# ─── Helper: classify stock size from market cap ───────────────────────────

def classify_market_cap(market_cap: float, currency: str) -> str:
    """
    Returns Small / Mid / Large / Mega based on market cap value.
    Uses different thresholds for INR (Indian) vs USD (US) stocks.
    """
    if not market_cap:
        return "Unknown"

    if currency == "INR":
        # Indian market thresholds (in INR)
        if market_cap >= 2_000_000_000_000:   # ₹2 Lakh Cr+
            return "Large Cap"
        elif market_cap >= 500_000_000_000:    # ₹50,000 Cr+
            return "Mid Cap"
        else:
            return "Small Cap"
    else:
        # US market thresholds (in USD)
        if market_cap >= 200_000_000_000:      # $200B+
            return "Mega Cap"
        elif market_cap >= 10_000_000_000:     # $10B+
            return "Large Cap"
        elif market_cap >= 2_000_000_000:      # $2B+
            return "Mid Cap"
        else:
            return "Small Cap"


# ─── Tool 1: Fetch full stock data for a single ticker ─────────────────────

@tool("Stock Data Fetcher")
def get_stock_data(ticker: str) -> dict:
    """
    Fetches price, volume, fundamentals, and market cap data for a stock.

    Ticker format:
      - Indian NSE stocks  → add .NS  e.g. RELIANCE.NS, TCS.NS
      - Indian BSE stocks  → add .BO  e.g. RELIANCE.BO
      - US stocks          → plain    e.g. AAPL, MSFT, TSLA
    """
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info

        # Pull 3 months of daily price + volume history
        history = stock.history(period="3mo")

        if history.empty:
            return {"error": f"No price data found for {ticker}. Check the ticker symbol."}

        # ── Price metrics ──────────────────────────────────────────────────
        current_price  = history["Close"].iloc[-1]
        prev_price     = history["Close"].iloc[-2] if len(history) > 1 else current_price
        day_change_pct = ((current_price - prev_price) / prev_price) * 100

        # 30-day momentum (roughly 22 trading days)
        lookback       = min(22, len(history) - 1)
        price_30d_ago  = history["Close"].iloc[-lookback]
        momentum_30d   = ((current_price - price_30d_ago) / price_30d_ago) * 100

        # ── Volume metrics ─────────────────────────────────────────────────
        avg_volume     = history["Volume"].mean()
        latest_volume  = history["Volume"].iloc[-1]
        # Volume spike ratio > 2 means today's volume is 2x the average — a signal
        volume_spike   = (latest_volume / avg_volume) if avg_volume > 0 else 1.0

        # ── Market cap size classification ─────────────────────────────────
        currency       = info.get("currency", "USD")
        market_cap     = info.get("marketCap")
        cap_size       = classify_market_cap(market_cap, currency)

        return {
            # Identity
            "ticker":           ticker,
            "company_name":     info.get("longName", ticker),
            "sector":           info.get("sector", "Unknown"),
            "industry":         info.get("industry", "Unknown"),
            "exchange":         info.get("exchange", "Unknown"),
            "currency":         currency,

            # Size
            "market_cap":       market_cap,
            "market_cap_size":  cap_size,

            # Price
            "current_price":    round(current_price, 2),
            "day_change_pct":   round(day_change_pct, 2),
            "momentum_30d_pct": round(momentum_30d, 2),
            "week_52_high":     info.get("fiftyTwoWeekHigh"),
            "week_52_low":      info.get("fiftyTwoWeekLow"),

            # Volume
            "avg_volume_3mo":   int(avg_volume),
            "latest_volume":    int(latest_volume),
            "volume_spike":     round(volume_spike, 2),   # >2 = unusual activity

            # Fundamentals
            "pe_ratio":         info.get("trailingPE"),
            "pb_ratio":         info.get("priceToBook"),
            "roe":              info.get("returnOnEquity"),      # e.g. 0.18 = 18%
            "revenue_growth":   info.get("revenueGrowth"),      # e.g. 0.12 = 12%
            "profit_margin":    info.get("profitMargins"),
            "debt_to_equity":   info.get("debtToEquity"),
            "dividend_yield":   info.get("dividendYield"),
            "eps":              info.get("trailingEps"),
        }

    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ─── Tool 2: Fetch a batch of stocks at once ───────────────────────────────

@tool("Batch Stock Data Fetcher")
def get_batch_stock_data(tickers: list) -> list:
    """
    Fetches stock data for a list of tickers in one go.
    Returns a list of results — one dict per stock.

    Example input:  ["TCS.NS", "INFY.NS", "AAPL", "MSFT"]
    """
    results = []
    for ticker in tickers:
        data = get_stock_data(ticker)
        results.append(data)
    return results


# ─── Quick test — run this file directly to check it works ─────────────────
# In your terminal: uv run src/tools/stock_data.py

if __name__ == "__main__":
    print("Testing Indian stock (TCS)...")
    result = get_stock_data("TCS.NS")
    for key, value in result.items():
        print(f"  {key:20} : {value}")

    print("\nTesting US stock (Apple)...")
    result = get_stock_data("AAPL")
    for key, value in result.items():
        print(f"  {key:20} : {value}")