# src/tools/technical_indicators.py
#
# This tool calculates technical indicators for any stock.
# The Data Analyst agent uses these to spot buy/sell signals
# based on price momentum, trend strength, and overbought/oversold levels.
#
# Indicators we calculate:
#   RSI     — is the stock overbought or oversold?
#   MACD    — is momentum shifting up or down?
#   Bollinger Bands — is price near the top or bottom of its range?
#   EMA     — what is the short vs long-term trend direction?
#   ATR     — how volatile is this stock right now?

import yfinance as yf
import pandas as pd
import pandas_ta as ta
from crewai.tools import tool


# ─── Helper: human-readable signal interpretation ──────────────────────────

def interpret_rsi(rsi: float) -> str:
    """RSI ranges: <30 oversold (potential buy), >70 overbought (potential sell)"""
    if rsi is None:
        return "No data"
    if rsi < 30:
        return "Oversold — potential BUY signal"
    elif rsi > 70:
        return "Overbought — potential SELL signal"
    elif rsi < 45:
        return "Slightly weak — leaning bearish"
    elif rsi > 55:
        return "Slightly strong — leaning bullish"
    else:
        return "Neutral zone"


def interpret_macd(macd: float, signal: float) -> str:
    """MACD above signal line = bullish momentum, below = bearish"""
    if macd is None or signal is None:
        return "No data"
    if macd > signal:
        return "Bullish — MACD above signal line"
    else:
        return "Bearish — MACD below signal line"


def interpret_bollinger(price: float, upper: float, lower: float, mid: float) -> str:
    """Price near upper band = overbought, near lower band = oversold"""
    if upper is None or lower is None:
        return "No data"
    band_width = upper - lower
    if band_width == 0:
        return "No data"
    position = (price - lower) / band_width   # 0 = at lower band, 1 = at upper band
    if position > 0.85:
        return "Near upper band — overbought / strong momentum"
    elif position < 0.15:
        return "Near lower band — oversold / possible reversal"
    elif position > 0.5:
        return "Above midline — mild bullish"
    else:
        return "Below midline — mild bearish"


# ─── Main Tool ─────────────────────────────────────────────────────────────

@tool("Technical Indicators Calculator")
def get_technical_indicators(ticker: str) -> dict:
    """
    Calculates RSI, MACD, Bollinger Bands, EMA (20/50), and ATR for a stock.
    Returns both raw numbers and human-readable signal interpretations.

    Ticker format:
      - Indian NSE: RELIANCE.NS, TCS.NS
      - Indian BSE: RELIANCE.BO
      - US stocks:  AAPL, MSFT, TSLA
    """
    try:
        stock   = yf.Ticker(ticker)
        history = stock.history(period="6mo")   # 6 months for reliable indicator calc

        if history.empty or len(history) < 30:
            return {"error": f"Not enough price history for {ticker} to calculate indicators."}

        # pandas_ta works directly on a DataFrame
        df = history[["Open", "High", "Low", "Close", "Volume"]].copy()

        # ── Calculate indicators ───────────────────────────────────────────

        # RSI (14-period) — Relative Strength Index
        df.ta.rsi(length=14, append=True)

        # MACD (12, 26, 9) — Moving Average Convergence Divergence
        df.ta.macd(fast=12, slow=26, signal=9, append=True)

        # Bollinger Bands (20-period, 2 std devs)
        df.ta.bbands(length=20, std=2, append=True)

        # EMA — Exponential Moving Averages (short & long term trend)
        df.ta.ema(length=20, append=True)
        df.ta.ema(length=50, append=True)

        # ATR (14-period) — Average True Range (volatility measure)
        df.ta.atr(length=14, append=True)

        # ── Extract latest values (last row = most recent trading day) ─────
        latest = df.iloc[-1]
        price  = round(latest["Close"], 2)

        # RSI
        rsi = latest.get("RSI_14")
        rsi = round(rsi, 2) if pd.notna(rsi) else None

        # MACD
        macd_val    = latest.get("MACD_12_26_9")
        macd_signal = latest.get("MACDs_12_26_9")
        macd_hist   = latest.get("MACDh_12_26_9")
        macd_val    = round(macd_val,    4) if pd.notna(macd_val)    else None
        macd_signal = round(macd_signal, 4) if pd.notna(macd_signal) else None
        macd_hist   = round(macd_hist,   4) if pd.notna(macd_hist)   else None

        # Bollinger Bands
        bb_upper = latest.get("BBU_20_2.0")
        bb_mid   = latest.get("BBM_20_2.0")
        bb_lower = latest.get("BBL_20_2.0")
        bb_upper = round(bb_upper, 2) if pd.notna(bb_upper) else None
        bb_mid   = round(bb_mid,   2) if pd.notna(bb_mid)   else None
        bb_lower = round(bb_lower, 2) if pd.notna(bb_lower) else None

        # EMA
        ema20 = latest.get("EMA_20")
        ema50 = latest.get("EMA_50")
        ema20 = round(ema20, 2) if pd.notna(ema20) else None
        ema50 = round(ema50, 2) if pd.notna(ema50) else None

        # ATR
        atr = latest.get("ATRr_14")
        atr = round(atr, 2) if pd.notna(atr) else None

        # ── EMA trend direction ────────────────────────────────────────────
        if ema20 and ema50:
            ema_trend = "Bullish — price above both EMAs, short > long" if (price > ema20 > ema50) \
                   else "Bearish — short EMA below long EMA" if ema20 < ema50 \
                   else "Mixed — consolidating"
        else:
            ema_trend = "No data"

        # ── Overall signal score (simple scoring for Master Analyst) ───────
        # +1 for each bullish signal, -1 for bearish, 0 for neutral
        score = 0
        if rsi and rsi < 50:     score -= 1
        if rsi and rsi < 35:     score -= 1   # strong oversold bonus (contrarian buy)
        if rsi and rsi > 50:     score += 1
        if rsi and rsi > 65:     score += 1   # strong momentum
        if macd_val and macd_signal:
            score += 1 if macd_val > macd_signal else -1
        if ema20 and ema50:
            score += 1 if ema20 > ema50 else -1
        if bb_upper and bb_lower and bb_mid:
            pos = (price - bb_lower) / (bb_upper - bb_lower)
            score += 1 if pos > 0.5 else -1

        if score >= 2:
            overall = "Strong Bullish"
        elif score == 1:
            overall = "Mild Bullish"
        elif score == 0:
            overall = "Neutral"
        elif score == -1:
            overall = "Mild Bearish"
        else:
            overall = "Strong Bearish"

        return {
            "ticker":         ticker,
            "current_price":  price,

            # Raw values
            "rsi":            rsi,
            "macd":           macd_val,
            "macd_signal":    macd_signal,
            "macd_histogram": macd_hist,
            "bb_upper":       bb_upper,
            "bb_mid":         bb_mid,
            "bb_lower":       bb_lower,
            "ema_20":         ema20,
            "ema_50":         ema50,
            "atr":            atr,    # higher = more volatile

            # Signal interpretations (for the LLM to read)
            "rsi_signal":         interpret_rsi(rsi),
            "macd_signal_label":  interpret_macd(macd_val, macd_signal),
            "bb_signal":          interpret_bollinger(price, bb_upper, bb_lower, bb_mid),
            "ema_trend":          ema_trend,

            # Summary score for Master Analyst
            "technical_score":    score,       # raw number
            "overall_signal":     overall,     # human label
        }

    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ─── Quick test ─────────────────────────────────────────────────────────────
# Run with: uv run src/tools/technical_indicators.py

if __name__ == "__main__":
    for ticker in ["TCS.NS", "AAPL"]:
        print(f"\n{'='*50}")
        print(f"Technical indicators for {ticker}")
        print("=" * 50)
        result = get_technical_indicators.func(ticker)
        for key, val in result.items():
            print(f"  {key:25} : {val}")