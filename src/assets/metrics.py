"""Risk/return metrics from a price (or NAV) series. Pure functions, no I/O.

These are the shared building blocks for scenario labelling and features later
on, so they are deliberately asset-class agnostic: only the annualisation factor
differs (crypto trades every day, markets ~252).
"""

import math

import pandas as pd

TRADING_DAYS = {"EQUITY": 252, "FUND": 252, "CRYPTO": 365}
_WINDOWS = {"1m": 21, "3m": 63, "6m": 126, "1y": 252}


def _num(x, nd: int = 4):
    """JSON-safe float: None for NaN/inf."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


def compute_metrics(close: pd.Series, asset_class: str = "EQUITY", risk_free: float = 0.0) -> dict:
    """Summary stats for a Close series indexed by date (ascending)."""
    close = pd.to_numeric(close, errors="coerce").dropna()
    close = close[close > 0]
    if len(close) < 2:
        return {"observations": int(len(close))}

    ppy = TRADING_DAYS.get(asset_class, 252)
    rets = close.pct_change().dropna()
    days = max((close.index[-1] - close.index[0]).days, 1)
    total = close.iloc[-1] / close.iloc[0] - 1

    peak = close.cummax()
    dd = close / peak - 1

    vol = rets.std() * math.sqrt(ppy) if len(rets) > 1 else float("nan")
    mean_ann = rets.mean() * ppy
    sharpe = (mean_ann - risk_free) / vol if vol and math.isfinite(vol) and vol > 0 else float("nan")

    rolling = {}
    for name, n in _WINDOWS.items():
        n = int(n * ppy / 252)
        rolling[name] = _num(close.iloc[-1] / close.iloc[max(-1 - n, -len(close))] - 1) if len(close) >= n else None

    return {
        "observations": int(len(close)),
        "start": close.index[0].strftime("%Y-%m-%d"),
        "end": close.index[-1].strftime("%Y-%m-%d"),
        "last": _num(close.iloc[-1], 6),
        "total_return": _num(total),
        "cagr": _num((1 + total) ** (365 / days) - 1) if days >= 180 else None,  # too noisy when short
        "annual_volatility": _num(vol),
        "sharpe": _num(sharpe, 3),
        "max_drawdown": _num(dd.min()),
        "current_drawdown": _num(dd.iloc[-1]),
        "best_day": _num(rets.max()),
        "worst_day": _num(rets.min()),
        "rolling_returns": rolling,
    }
