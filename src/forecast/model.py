"""Scenario model: a volatility-scaled bootstrap of the asset's own history.

The one thing about future returns that history predicts reliably is their *spread*.
So we standardise every past forward return by the volatility known at the time
(z = log-return / (vol * sqrt(horizon))), then re-scale those z-scores by today's
volatility and bucket the result into scenarios. Past drift is removed entirely.

The asset's own history is a small sample of tail behaviour, so it is blended with a pooled
sample from the whole asset group (pool.py) and with the plain base rate: 20% own, 50% pooled,
30% base rate. Assets with no pooled bank available fall back to 50% own / 50% base rate.

How the settings were chosen (walk-forward 2019-2025, ~250 stocks/ETFs/coins, 3m and 1y, trained
only on data that had ended before each test year): dropping drift, a smoother vol estimate and
blending each helped at both horizons and in every asset group; pooling helped most (1y skill
vs the base rate ~5.8% -> ~8.7%) and also helped assets with short histories. Pooled *feature*
models (momentum/drawdown/RSI/market regime, logistic and boosted trees) did NOT beat this --
direction is not predictable from price features, only spread is.
Caveat: the research universe is today's large caps, so survivorship flatters every model.
Survivorship check: on 81 collapsed assets (Yes Bank, RCOM, FTT, LUNC, SNAP, ...) the model already predicted
crash rates close to what happened (3m: 21% vs 23% observed; 1y: 28% vs 29%), because failing assets are volatile
beforehand; mixing 5-40% collapsed assets into the pool barely changed any score, so the pool was left as is.
Calibration there: 3m odds sit on the diagonal; at 1y crash/decline ran high (~13% predicted vs ~8%
observed) and strong growth low. That is left uncorrected on purpose -- the sample excludes the
companies that failed, and a power recalibration fitted on 2019-22 did not help on 2023+.

Any fancier model (sentiment, theses) has to beat this in the backtest; see backtest.py.
"""

import numpy as np
import pandas as pd

from src.forecast.scenarios import SCENARIOS, classify

MODEL_VERSION = "volboot-4"
SOLO_VERSION = "volboot-3"       # same model without a pooled bank
MIN_SAMPLES = 150                # own-history samples needed without a pooled bank
MIN_SAMPLES_POOLED = 60          # ... and with one: the pool supplies the tails
W_OWN, W_POOL, W_BASE = 0.2, 0.5, 0.3
W_OWN_SOLO = 0.5                 # no pool: half own bootstrap, half base rate
LOW_VOL_ANNUAL = 0.05            # below this (debt/liquid funds) the model showed no edge: use the base rate
QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
_ALPHA = 1.0  # total pseudo-count; keeps log loss finite when a bucket is empty


def trailing_vol(close: pd.Series) -> pd.Series:
    """Daily vol known at each bar: half fast-decaying (reacts to recent shocks), half 1-year (stable)."""
    r = np.log(close).diff()
    fast = np.sqrt((r ** 2).ewm(alpha=0.06, min_periods=30).mean())
    return 0.5 * fast + 0.5 * r.rolling(252, min_periods=60).std()


def _smooth(counts: np.ndarray) -> np.ndarray:
    p = counts + _ALPHA / len(counts)
    return p / p.sum()


def _probs(simple_returns: np.ndarray, cut_points: list[float]) -> np.ndarray:
    idx = classify(simple_returns, cut_points)
    return _smooth(np.bincount(idx, minlength=len(SCENARIOS)).astype(float))


def _clean(close: pd.Series) -> pd.Series:
    close = pd.to_numeric(close, errors="coerce").dropna()
    return close[close > 0]


def _wquantiles(values: np.ndarray, weights: np.ndarray, qs) -> list[float]:
    order = np.argsort(values)
    v, cw = values[order], np.cumsum(weights[order])
    cw = cw / cw[-1]
    return [float(v[min(np.searchsorted(cw, q), len(v) - 1)]) for q in qs]


def base_rate(close: pd.Series, bars: int, cut_points: list[float],
              min_samples: int = MIN_SAMPLES) -> dict | None:
    """Unconditional benchmark: how often each scenario happened in this asset's past."""
    close = _clean(close)
    fwd = (close.shift(-bars) / close - 1).dropna().to_numpy()
    if len(fwd) < min_samples:
        return None
    return dict(zip(SCENARIOS, _probs(fwd, cut_points).tolist()))


def predict(close: pd.Series, bars: int, cut_points: list[float],
            pool_z: np.ndarray | None = None) -> dict | None:
    """Scenario probabilities from data up to the last bar; None if history is too short.

    `pool_z` is a pooled standardised-return sample (see pool.py). With it the forecast leans on
    the pool's tails (20% own / 50% pooled / 30% base rate); without it, half own / half base rate.
    The result includes `base_rate`, the unconditional benchmark scored against. Very low-volatility
assets (annualised vol under 5%, e.g. debt funds) just get the base rate, as the model showed no edge there.
    """
    close = _clean(close)
    need = MIN_SAMPLES_POOLED if pool_z is not None else MIN_SAMPLES
    sigma = trailing_vol(close)
    fwd_log = np.log(close.shift(-bars) / close)
    z = (fwd_log / (sigma * np.sqrt(bars))).replace([np.inf, -np.inf], np.nan).dropna()
    base = base_rate(close, bars, cut_points, need)
    if len(z) < need or base is None or not np.isfinite(sigma.iloc[-1]) or sigma.iloc[-1] <= 0:
        return None

    z = z.to_numpy()
    z = z - z.mean()                      # no drift: past returns, esp. of survivors, flatter the future
    sigma_now = float(sigma.iloc[-1])
    scale = sigma_now * np.sqrt(bars)
    own = np.exp(z * scale) - 1
    base_p = np.array([base[s] for s in SCENARIOS])

    if pool_z is not None:
        pooled = np.exp(np.asarray(pool_z) * scale) - 1
        probs = W_OWN * _probs(own, cut_points) + W_POOL * _probs(pooled, cut_points) + W_BASE * base_p
        sim = np.concatenate([own, pooled])
        weights = np.concatenate([np.full(len(own), W_OWN / len(own)), np.full(len(pooled), W_POOL / len(pooled))])
        version = MODEL_VERSION
    else:
        probs = W_OWN_SOLO * _probs(own, cut_points) + (1 - W_OWN_SOLO) * base_p
        sim, weights, version = own, np.ones(len(own)), SOLO_VERSION

    low_vol = sigma_now * np.sqrt(252) < LOW_VOL_ANNUAL
    if low_vol:     # walk-forward on Indian debt/liquid funds: skill -6% (3m) / +7% (1y), i.e. none shown
        probs = base_p

    qv = _wquantiles(sim, weights, QUANTILES)
    return {
        "probs": dict(zip(SCENARIOS, probs.tolist())),
        "base_rate": base,
        "quantiles": {f"p{int(q * 100)}": v for q, v in zip(QUANTILES, qv)},
        "expected_return": float(np.average(sim, weights=weights)),
        "daily_vol": sigma_now,
        "n_samples": int(len(z)),
        "model_version": version,
        "low_volatility": bool(low_vol),
    }
