"""Numbers about a confirmed portfolio: live values and P&L, concentration, risk contribution,
diversification, and a historical simulation of the *whole* portfolio over 1-3 months.

The simulation answers "how likely is it that this portfolio gains X% in N months?" honestly, from how
these exact holdings moved together in the past, with past drift removed and the spread scaled to
current volatility (the same philosophy as the single-asset forecasts). It is what keeps the strategy
text from promising results the numbers don't support.
"""

import concurrent.futures
import logging
import math

import numpy as np
import pandas as pd

from src.assets import service as assets
from src.assets.metrics import compute_metrics
from src.assets.types import AssetRef, parse_symbol

logger = logging.getLogger("stockpicker.portfolio_agent")

MAX_HOLDINGS = 40
MIN_COMMON_DAYS = 120
HISTORY_DAYS = 500
HORIZONS = {"1 month": 21, "2 months": 42, "3 months": 63}
THRESHOLDS = (0.0, 0.05, 0.10, 0.20)
QS = (0.05, 0.25, 0.5, 0.75, 0.95)
BLOCK = 5
SIM_PATHS = 4000


class AnalysisError(ValueError):
    """The portfolio can't be analysed (message is safe to show the user)."""


def jsonable(x):
    """Recursively make a result safe for a JSON column: numpy scalars -> python, NaN/inf -> None."""
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, (np.floating, float)):
        x = float(x)
        return x if math.isfinite(x) else None
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def _fx_usd_inr() -> float:
    from src.providers import market_data_client
    return float(market_data_client().quote("USDINR=X", ttl_seconds=300).data["price"])


def _fetch(h: dict) -> dict:
    """Everything needed for one holding; failures are recorded on the row, not raised."""
    row = {"symbol": h["symbol"], "name": h.get("name"), "quantity": float(h["quantity"]),
           "avg_price": h.get("avg_price")}
    try:
        ref = parse_symbol(h["symbol"], h.get("asset_class"))
        row.update(asset_class=ref.asset_class.value, market=ref.market, currency=ref.currency, display=ref.display)
        row["price"] = float(assets.quote(ref)["price"])
        df = assets.history(ref, "2y")
        close = pd.to_numeric(df["Close"], errors="coerce").dropna()
        close = close[close > 0].tail(HISTORY_DAYS + 5)
        row["_close"] = close
        m = compute_metrics(close.tail(252), ref.asset_class.value)
        row["metrics"] = {k: m.get(k) for k in ("annual_volatility", "max_drawdown", "current_drawdown",
                                                "total_return", "sharpe")}
        try:
            from src.forecast import service as fc
            f = fc.forecast(ref, "3m", log=False)
            p = f["probs"]
            row["outlook_3m"] = {"probs": p, "downside": p["CRASH"] + p["DECLINE"],
                                 "upside": p["STRONG_GROWTH"] + p["MULTIBAGGER"], "low_volatility": f.get("low_volatility", False),
                                 "p5": f["quantiles"]["p5"], "p50": f["quantiles"]["p50"], "p95": f["quantiles"]["p95"]}
        except Exception:
            row["outlook_3m"] = None
    except Exception as e:
        logger.warning("could not load %s: %s", h.get("symbol"), e)
        row["error"] = "Live data unavailable for this holding."
    return row


def _portfolio_series(returns: pd.DataFrame, w: np.ndarray) -> np.ndarray:
    simple = np.exp(returns.to_numpy()) - 1
    return np.log1p(np.clip(simple @ w, -0.99, None))


def _bootstrap_sums(p: np.ndarray, h: int) -> np.ndarray:
    """h-day log returns from resampled 5-day blocks of the portfolio's daily history.

    With only 1-2 years of data, overlapping h-day windows are nearly the same few windows repeated and
    their quantiles are noisy. Block resampling keeps short-range clustering and the joint behaviour of
    the holdings (each day is the whole portfolio) while giving stable estimates. Seeded: same input,
    same answer.
    """
    rng = np.random.default_rng(7)
    nb = -(-h // BLOCK)
    starts = rng.integers(0, len(p) - BLOCK + 1, size=(SIM_PATHS, nb))
    idx = (starts[:, :, None] + np.arange(BLOCK)).reshape(SIM_PATHS, -1)[:, :h]
    return p[idx].sum(axis=1)


def simulate(returns: pd.DataFrame, w: np.ndarray, breakeven: float | None) -> dict | None:
    """Outcome distribution for fixed weights over 1/2/3 months (block bootstrap of the portfolio's history)."""
    if len(returns) < MIN_COMMON_DAYS:
        return None
    p = _portfolio_series(returns, w)
    p = p - p.mean()                                     # no drift: past gains aren't a forecast
    full = p.std()
    if not full or not math.isfinite(full):
        return None
    recent = p[-63:].std()
    scale = float(np.clip((0.5 * recent + 0.5 * full) / full, 0.5, 2.0))
    p = p * scale
    thresholds = sorted({round(t, 4) for t in THRESHOLDS} | ({round(breakeven, 4)} if breakeven and 0 < breakeven < 2 else set()))
    out = {}
    for label, h in HORIZONS.items():
        if len(p) < h + 40:
            continue
        rets = np.exp(_bootstrap_sums(p, h)) - 1
        out[label] = {
            "days": h, "paths": int(len(rets)),
            "quantiles": {f"p{int(q * 100)}": float(np.quantile(rets, q)) for q in QS},
            "prob_at_least": {f"{t:+.1%}": float((rets >= t).mean()) for t in thresholds},
            "prob_loss": float((rets < 0).mean()),
        }
    return {"scaled_vol_ratio": round(scale, 2), "common_days": int(len(returns)), "horizons": out,
            "breakeven_return": breakeven}


def merge_duplicates(holdings: list[dict]) -> list[dict]:
    """The same symbol listed twice (e.g. two lots) becomes one row: summed quantity, weighted-average price."""
    merged: dict[str, dict] = {}
    for h in holdings:
        sym = h["symbol"].strip()
        key = sym if sym.upper().startswith(("CRYPTO:", "MF:")) else sym.upper()
        if key not in merged:
            merged[key] = {**h, "symbol": sym}
            continue
        m = merged[key]
        q1, q2 = float(m["quantity"]), float(h["quantity"])
        if m.get("avg_price") and h.get("avg_price"):
            m["avg_price"] = (m["avg_price"] * q1 + h["avg_price"] * q2) / (q1 + q2)
        else:
            m["avg_price"] = None                 # can't average a known price with an unknown one
        m["quantity"] = q1 + q2
    return list(merged.values())


def analyze(holdings: list[dict]) -> dict:
    """`holdings`: [{symbol, quantity, avg_price?, asset_class?, name?}] already confirmed by the user."""
    holdings = merge_duplicates(holdings)
    if not holdings:
        raise AnalysisError("No holdings to analyse.")
    if len(holdings) > MAX_HOLDINGS:
        raise AnalysisError(f"Too many holdings (limit {MAX_HOLDINGS}).")
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(_fetch, holdings))
    ok = [r for r in rows if "error" not in r]
    if not ok:
        raise AnalysisError("Live prices couldn't be loaded for any of these holdings. Please try again shortly.")

    # one reporting currency: whichever holds more of the value
    inr_native = sum(r["price"] * r["quantity"] for r in ok if r["currency"] == "INR")
    usd_native = sum(r["price"] * r["quantity"] for r in ok if r["currency"] == "USD")
    fx = None
    if inr_native and usd_native:
        try:
            fx = _fx_usd_inr()
        except Exception:
            raise AnalysisError("The USD/INR exchange rate is unavailable, so a mixed portfolio can't be totalled. Try again shortly.")
        base = "INR" if inr_native >= usd_native * fx else "USD"
    else:
        base = "INR" if inr_native else "USD"

    def to_base(amount: float, ccy: str) -> float:
        if ccy == base or fx is None:
            return amount
        return amount * fx if base == "INR" else amount / fx

    value = cost = cost_value = 0.0
    for r in ok:
        r["value"] = to_base(r["price"] * r["quantity"], r["currency"])
        value += r["value"]
        if r.get("avg_price"):
            r["cost"] = to_base(r["avg_price"] * r["quantity"], r["currency"])
            r["pnl_pct"] = r["price"] / r["avg_price"] - 1
            cost += r["cost"]
            cost_value += r["value"]
    for r in ok:
        r["weight"] = r["value"] / value

    w = np.array([r["weight"] for r in ok])
    hhi = float((w ** 2).sum())
    by_class: dict[str, float] = {}
    by_market: dict[str, float] = {}
    for r in ok:
        by_class[r["asset_class"]] = by_class.get(r["asset_class"], 0) + r["weight"]
        by_market[r["market"]] = by_market.get(r["market"], 0) + r["weight"]

    portfolio = {
        "value": value, "cost_known": cost if cost else None,
        "pnl_pct": (cost_value / cost - 1) if cost else None,
        "pnl_amount": (cost_value - cost) if cost else None,
        "cost_coverage": (cost_value / value) if value else 0.0,
        "breakeven_return": (cost / cost_value - 1) if cost and cost_value else None,
        "n_holdings": len(ok), "top3_weight": float(np.sort(w)[::-1][:3].sum()),
        "effective_n": round(1 / hhi, 1), "hhi": round(hhi, 3),
        "by_asset_class": {k: round(v, 4) for k, v in by_class.items()},
        "by_market": {k: round(v, 4) for k, v in by_market.items()},
    }

    # joint behaviour: aligned daily log returns -> correlation, risk contribution, simulation
    series = {r["symbol"]: np.log(r["_close"]).diff() for r in ok if len(r["_close"]) > 60}
    notes = []
    if len(series) >= 1 and len(series) == len(ok):
        rets = pd.concat(series, axis=1).dropna().tail(HISTORY_DAYS)
        rets = rets[[r["symbol"] for r in ok]] if len(series) == len(ok) else rets
    else:
        rets = pd.DataFrame()
    sim = None
    if len(rets) >= MIN_COMMON_DAYS:
        cov = np.cov(rets.to_numpy().T) * 252 if rets.shape[1] > 1 else np.array([[rets.iloc[:, 0].var() * 252]])
        port_var = float(w @ cov @ w)
        port_vol = math.sqrt(port_var)
        rc = (w * (cov @ w)) / port_var if port_var > 0 else w
        for r, c in zip(ok, rc):
            r["risk_share"] = float(c)
        indiv = np.sqrt(np.diag(cov))
        portfolio.update(annual_volatility=port_vol,
                         diversification_ratio=float((w @ indiv) / port_vol) if port_vol else None)
        if rets.shape[1] > 1:
            corr = np.corrcoef(rets.to_numpy().T)
            iu = np.triu_indices_from(corr, k=1)
            portfolio["avg_correlation"] = float(corr[iu].mean())
            pairs = sorted(((float(corr[i, j]), ok[i]["display"], ok[j]["display"]) for i, j in zip(*iu)), reverse=True)
            portfolio["most_correlated"] = [{"a": a, "b": b, "corr": round(c, 2)} for c, a, b in pairs[:3]]
        sim = simulate(rets, w, portfolio["breakeven_return"])
    else:
        notes.append(f"Only {len(rets)} days of shared price history, too few to simulate the portfolio as a whole.")

    failed = [r["symbol"] for r in rows if "error" in r]
    if failed:
        notes.append(f"No live data for {', '.join(failed)}; they are excluded from totals.")
    if fx:
        notes.append(f"Mixed currencies converted at USD/INR {fx:.2f}.")
    if portfolio["cost_coverage"] < 0.999 and cost:
        notes.append("Buy prices are missing for some holdings, so P&L covers only part of the portfolio.")

    out_rows = []
    for r in ok:
        keep = {k: v for k, v in r.items() if not k.startswith("_")}
        out_rows.append(keep)
    out_rows.sort(key=lambda r: -r["value"])
    return jsonable({"base_currency": base, "fx_usd_inr": fx, "portfolio": portfolio, "holdings": out_rows,
                     "simulation": sim, "failed": failed, "notes": notes})
