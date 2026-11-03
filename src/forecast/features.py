"""Point-in-time features: every value at row t uses only data up to and including t.

That property is what makes the backtest honest, and it is covered by a test that
truncates the series and checks the earlier rows do not change.
"""

import numpy as np
import pandas as pd


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, np.nan))


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature frame indexed like `df` (needs a Close column; Volume is optional)."""
    close = pd.to_numeric(df["Close"], errors="coerce")
    logret = np.log(close).diff()
    out = pd.DataFrame(index=df.index)
    for n in (5, 21, 63, 126):
        out[f"ret_{n}"] = close / close.shift(n) - 1
    out["vol_21"] = logret.rolling(21, min_periods=15).std()
    out["vol_63"] = logret.rolling(63, min_periods=30).std()
    out["drawdown_252"] = close / close.rolling(252, min_periods=60).max() - 1
    out["ma_gap_200"] = close / close.rolling(200, min_periods=100).mean() - 1
    out["rsi_14"] = _rsi(close)
    if "Volume" in df and pd.to_numeric(df["Volume"], errors="coerce").fillna(0).gt(0).any():
        v = pd.to_numeric(df["Volume"], errors="coerce")
        out["volume_ratio"] = v.rolling(21, min_periods=10).mean() / v.rolling(63, min_periods=30).mean()
    else:
        out["volume_ratio"] = np.nan
    return out.replace([np.inf, -np.inf], np.nan)


def latest_snapshot(df: pd.DataFrame) -> dict:
    """JSON-safe feature values at the last row (stored with each logged prediction)."""
    row = build_features(df).iloc[-1]
    return {k: (round(float(v), 5) if np.isfinite(v) else None) for k, v in row.items()}
