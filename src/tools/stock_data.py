# src/tools/stock_data.py
# FIXED: Switched from `langchain.tools` to `crewai.tools` @tool decorator
#        to match the rest of the project and avoid silent CrewAI tool failures.

from crewai.tools import tool

from src.providers import market_data_client


@tool("Get Stock Data")
def get_stock_data(ticker: str) -> str:
    """
    Fetches historical price data and key fundamentals for a given stock ticker.
    Use this tool when you need basic pricing, volume, and company information.
    """
    try:
        client = market_data_client()
        info = client.fundamentals(ticker).data
        if not info:
            return f"No fundamental data found for {ticker}."

        name       = info.get("shortName", ticker)
        sector     = info.get("sector", "Unknown")
        industry   = info.get("industry", "Unknown")
        market_cap = info.get("marketCap", "Unknown")
        pe         = info.get("trailingPE", "N/A")
        pb         = info.get("priceToBook", "N/A")
        roe        = info.get("returnOnEquity", "N/A")
        debt_to_eq = info.get("debtToEquity", "N/A")
        rev_growth = info.get("revenueGrowth", "N/A")
        eps        = info.get("trailingEps", "N/A")
        high_52    = info.get("fiftyTwoWeekHigh", "N/A")
        low_52     = info.get("fiftyTwoWeekLow", "N/A")

        hist = client.history(ticker, period="1mo").data
        if hist.empty:
            prices = "No recent price history available."
        else:
            last_close  = hist["Close"].iloc[-1]
            prev_close  = hist["Close"].iloc[-2] if len(hist) > 1 else last_close
            day_change  = ((last_close - prev_close) / prev_close) * 100
            month_start = hist["Close"].iloc[0]
            mom_30d     = ((last_close - month_start) / month_start) * 100
            avg_vol     = hist["Volume"].mean()
            last_vol    = hist["Volume"].iloc[-1]
            vol_spike   = last_vol / avg_vol if avg_vol > 0 else 1.0

            prices = (
                f"Current Price: {last_close:.2f} (Day Change: {day_change:.2f}%)\n"
                f"30-Day Momentum: {mom_30d:.2f}%\n"
                f"Volume Spike Ratio: {vol_spike:.2f}x average"
            )

        return (
            f"Data for {name} ({ticker}):\n"
            f"Sector: {sector} | Industry: {industry}\n"
            f"Market Cap: {market_cap}\n"
            f"Fundamentals: P/E={pe}, P/B={pb}, ROE={roe}, Debt/Eq={debt_to_eq}, "
            f"RevGrowth={rev_growth}, EPS={eps}\n"
            f"52w High: {high_52} | 52w Low: {low_52}\n"
            f"{prices}"
        )

    except Exception as e:
        return f"Error fetching stock data for {ticker}: {str(e)}"


@tool("Get Batch Stock Data")
def get_batch_stock_data(tickers: str) -> str:
    """
    Fetches a quick summary of current prices for a comma-separated list of tickers.
    """
    try:
        ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
        if not ticker_list:
            return "No valid tickers provided."

        results = []
        client = market_data_client()
        for t in ticker_list:
            try:
                quote = client.quote(t).data
                results.append(f"{t}: {float(quote['price']):.2f}")
            except Exception:
                continue

        return " | ".join(results) if results else "Could not retrieve batch prices."

    except Exception as e:
        return f"Error fetching batch data: {str(e)}"
