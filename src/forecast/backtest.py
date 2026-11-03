"""Walk-forward evaluation: at each past date, fit on data available *then*, predict,
and score against what actually happened `bars` later.

Scores are compared with the unconditional base rate (skill > 0 means the model beat
"just use how often each scenario happened before"). Scenario outcomes overlap in time,
so effective sample size is smaller than `n`; treat small differences as noise.
"""

import numpy as np
import pandas as pd

from src.forecast import model, pool
from src.forecast.scenarios import SCENARIOS, classify

MIN_EVAL_POINTS = 12
_BINS = np.linspace(0, 1, 11)


def brier(p: np.ndarray, y: np.ndarray) -> float:
    """Mean over predictions of the squared error summed across scenarios (0 best, 2 worst)."""
    return float(np.mean(np.sum((p - y) ** 2, axis=1)))


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    return float(-np.mean(np.sum(y * np.log(np.clip(p, 1e-9, 1)), axis=1)))


def reliability(p: np.ndarray, y: np.ndarray) -> list[dict]:
    """Pooled over all scenarios: in each predicted-probability bin, how often did it happen?"""
    pf, yf = p.ravel(), y.ravel()
    rows = []
    for lo, hi in zip(_BINS[:-1], _BINS[1:]):
        m = (pf >= lo) & ((pf < hi) if hi < 1 else (pf <= hi))
        if m.any():
            rows.append({"bin": [round(float(lo), 1), round(float(hi), 1)],
                         "predicted": round(float(pf[m].mean()), 4),
                         "observed": round(float(yf[m].mean()), 4), "count": int(m.sum())})
    return rows


def score(p: np.ndarray, p_base: np.ndarray, y: np.ndarray) -> dict:
    """Metrics for aligned (n, 5) arrays of model probs, base-rate probs and one-hot outcomes."""
    bm, bb = brier(p, y), brier(p_base, y)
    return {
        "n": int(len(y)),
        "brier": round(bm, 4), "brier_base_rate": round(bb, 4),
        "skill": round(1 - bm / bb, 4) if bb > 0 else None,
        "log_loss": round(log_loss(p, y), 4), "log_loss_base_rate": round(log_loss(p_base, y), 4),
        "reliability": reliability(p, y),
    }


def _vec(d: dict) -> np.ndarray:
    return np.array([d[s] for s in SCENARIOS])


def walk_forward(close: pd.Series, bars: int, cut_points: list[float], step: int = 21,
                 horizon: str | None = None, group: str | None = None) -> dict:
    """With `horizon` and `group`, each forecast uses the pooled bank as of its own year, so
    the pool never contains outcomes from after the date being forecast from."""
    close = model._clean(close)
    n = len(close)
    P, B, Y, dates, pooled = [], [], [], [], 0
    for t in range(model.MIN_SAMPLES_POOLED + 10, n - bars, step):
        hist = close.iloc[: t + 1]
        z = pool.bank(horizon, group, close.index[t].date()) if horizon and group else None
        pred = model.predict(hist, bars, cut_points, z)
        if pred is None:
            continue
        base, pooled = pred["base_rate"], pooled + (z is not None)
        outcome = int(classify(close.iloc[t + bars] / close.iloc[t] - 1, cut_points))
        P.append(_vec(pred["probs"]))
        B.append(_vec(base))
        Y.append(np.eye(len(SCENARIOS))[outcome])
        dates.append(close.index[t].strftime("%Y-%m-%d"))

    if len(Y) < MIN_EVAL_POINTS:
        return {"status": "insufficient_history", "observations": int(n), "n": len(Y),
                "model_version": model.MODEL_VERSION,
                "detail": f"Need at least {MIN_EVAL_POINTS} out-of-sample forecasts; got {len(Y)} from {n} price points."}

    P, B, Y = np.array(P), np.array(B), np.array(Y)
    return {"status": "ok", "model_version": model.MODEL_VERSION, "bars": bars,
            "pooled_share": round(pooled / len(Y), 2),
            "first": dates[0], "last": dates[-1], **score(P, B, Y)}
