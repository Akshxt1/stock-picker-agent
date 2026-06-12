# src/tools/stock_data.py

from langchain.tools import tool
import yfinance as yf

@tool("Get Stock Data")
def get_stock_data(ticker: str) -> str:
    """
    Fetches historical price data and key fundamentals for a given stock ticker.
    Use this tool when you need basic pricing, volume, and company information.
    """
    try:
        # SECURITY FIX: Added error handling to prevent API failure from crashing the Agent
        stock = yf.Ticker(ticker)
        
        info = stock.info
        if not info:
            return f"No fundamental data found for {ticker}."
            
        name = info.get("shortName", ticker)
        sector = info.get("sector", "Unknown")
        industry = info.get("industry", "Unknown")
        market_cap = info.get("marketCap", "Unknown")
        pe = info.get("trailingPE", "N/A")
        pb = info.get("priceToBook", "N/A")
        roe = info.get("returnOnEquity", "N/A")
        debt_to_eq = info.get("debtToEquity", "N/A")
        rev_growth = info.get("revenueGrowth", "N/A")
        eps = info.get("trailingEps", "N/A")
        high_52 = info.get("fiftyTwoWeekHigh", "N/A")
        low_52 = info.get("fiftyTwoWeekLow", "N/A")
        
        hist = stock.history(period="1mo")
        if hist.empty:
            prices = "No recent price history available."
        else:
            last_close = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else last_close
            day_change = ((last_close - prev_close) / prev_close) * 100
            month_start = hist["Close"].iloc[0]
            mom_30d = ((last_close - month_start) / month_start) * 100
            avg_vol = hist["Volume"].mean()
            last_vol = hist["Volume"].iloc[-1]
            vol_spike = last_vol / avg_vol if avg_vol > 0 else 1.0
            
            prices = (
                f"Current Price: {last_close:.2f} (Day Change: {day_change:.2f}%)\n"
                f"30-Day Momentum: {mom_30d:.2f}%\n"
                f"Volume Spike Ratio: {vol_spike:.2f}x average"
            )

        return (
            f"Data for {name} ({ticker}):\n"
            f"Sector: {sector} | Industry: {industry}\n"
            f"Market Cap: {market_cap}\n"
            f"Fundamentals: P/E={pe}, P/B={pb}, ROE={roe}, Debt/Eq={debt_to_eq}, RevGrowth={rev_growth}, EPS={eps}\n"
            f"52w High: {high_52} | 52w Low: {low_52}\n"
            f"{prices}"
        )
        
    except Exception as e:
        # Prevent API failure from crashing the Agent
        return f"Error fetching stock data for {ticker}: API unavailable or timed out. Details: {str(e)}"

@tool("Get Batch Stock Data")
def get_batch_stock_data(tickers: str) -> str:
    """
    Fetches a quick summary of current prices for a comma-separated list of tickers.
    """
    try:
        ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
        if not ticker_list:
            return "No valid tickers provided."
            
        # Added timeout to prevent hanging the server
        data = yf.download(tickers=" ".join(ticker_list), period="1d", group_by="ticker", timeout=10)
        
        results = []
        if len(ticker_list) == 1:
            t = ticker_list[0]
            if not data.empty and "Close" in data:
                val = data["Close"].iloc[-1]
                results.append(f"{t}: {val:.2f}")
        else:
            for t in ticker_list:
                if t in data and not data[t].empty and "Close" in data[t]:
                    val = data[t]["Close"].iloc[-1]
                    results.append(f"{t}: {val:.2f}")
                    
        return " | ".join(results) if results else "Could not retrieve batch prices."
    except Exception as e:
        return f"Error fetching batch data: {str(e)}"