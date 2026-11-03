"""Make forecasts, log them, resolve them against reality, and report the track record."""

import logging
import threading
from datetime import datetime, timedelta, timezone

import numpy as np

from src.assets import service as assets
from src.assets.types import AssetRef
from src.database.models import Prediction, Session, init_db
from src.forecast import backtest, features, model, pool, sentiment
from src.forecast.scenarios import (HORIZON_DAYS, SCENARIOS, classify, cuts, definitions,
                                    horizon_bars)
from src.providers.cache import get_cached, set_cached

logger = logging.getLogger("stockpicker.forecast")

HISTORY_PERIOD = "5y"
BACKTEST_TTL = 6 * 3600
RESOLVE_EVERY = 6 * 3600


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _close(ref: AssetRef, period: str = HISTORY_PERIOD):
    return assets.history(ref, period)["Close"]


def forecast(ref: AssetRef, horizon: str, log: bool = True) -> dict:
    """Scenario probabilities for `ref` over `horizon`. Raises ValueError if history is too short."""
    bars = horizon_bars(horizon, ref.asset_class)
    cut_points = cuts(horizon, ref.asset_class)
    df = assets.history(ref, HISTORY_PERIOD)
    pred = model.predict(df["Close"], bars, cut_points, pool.bank(horizon, pool.group_for(ref)))
    if pred is None:
        raise ValueError(f"Not enough price history for {ref.symbol} to forecast {horizon} scenarios "
                         f"({len(df)} observations).")
    price = float(df["Close"].dropna().iloc[-1])
    feats = features.latest_snapshot(df)
    out = {
        "symbol": ref.symbol, "asset_class": ref.asset_class.value, "horizon": horizon,
        "horizon_days": HORIZON_DAYS[horizon], "as_of": df.index[-1].strftime("%Y-%m-%d"),
        "price": price, "currency": ref.currency, **pred,
        "scenarios": definitions(ref.asset_class)[horizon], "features": feats,
    }
    if log:
        out["prediction_id"], created = _log(ref, horizon, bars, price, pred, pred["base_rate"], feats)
        if created and sentiment.enabled():
            sentiment.shadow_log_async(ref, out["prediction_id"])
    return out


def _log(ref, horizon, bars, price, pred, base, feats) -> tuple[int, bool]:
    """One logged prediction per (symbol, horizon, model, UTC day) so refreshes don't inflate the record."""
    init_db()
    now = _now()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    with Session() as s:
        existing = (s.query(Prediction.id)
                    .filter(Prediction.symbol == ref.symbol, Prediction.horizon == horizon,
                            Prediction.model_version == pred["model_version"],
                            Prediction.made_at >= day).first())
        if existing:
            return existing[0], False
        row = Prediction(
            symbol=ref.symbol, asset_class=ref.asset_class.value, horizon=horizon,
            horizon_bars=bars, model_version=pred["model_version"], made_at=now,
            due_at=now + timedelta(days=HORIZON_DAYS[horizon]), price_at=price,
            probs=pred["probs"], base_probs=base, quantiles=pred["quantiles"],
            features=feats, n_samples=pred["n_samples"])
        s.add(row)
        s.commit()
        return row.id, True


def run_backtest(ref: AssetRef, horizon: str) -> dict:
    key = f"forecast:backtest:{model.MODEL_VERSION}:{ref.symbol}:{horizon}"
    hit = get_cached(key)
    if hit:
        return hit
    res = backtest.walk_forward(_close(ref), horizon_bars(horizon, ref.asset_class),
                                cuts(horizon, ref.asset_class), horizon=horizon, group=pool.group_for(ref))
    res.update(symbol=ref.symbol, horizon=horizon)
    set_cached(key, "forecast", res, BACKTEST_TTL)
    return res


# ── Resolution ────────────────────────────────────────────────────────────────

def resolve_due(now: datetime | None = None) -> int:
    """Fill in outcomes for predictions whose horizon has passed. Returns how many were resolved."""
    init_db()
    now = now or _now()
    with Session() as s:
        due = s.query(Prediction).filter(Prediction.resolved_at.is_(None),
                                         Prediction.due_at <= now).all()
        by_symbol: dict[str, list[Prediction]] = {}
        for p in due:
            by_symbol.setdefault(p.symbol, []).append(p)

        resolved = 0
        for symbol, rows in by_symbol.items():
            try:
                ref = _ref_for(symbol, rows[0].asset_class)
                close = _close(ref, "2y").dropna()
            except Exception as e:
                logger.warning("could not resolve %s predictions: %s", symbol, e)
                continue
            for p in rows:
                later = close[close.index >= p.due_at.replace(hour=0, minute=0, second=0, microsecond=0)]
                if later.empty:
                    continue                      # market data hasn't reached the due date yet
                ret = float(later.iloc[0] / p.price_at - 1)
                p.outcome_price = float(later.iloc[0])
                p.outcome_return = ret
                p.outcome_scenario = SCENARIOS[int(classify(ret, cuts(p.horizon, p.asset_class)))]
                p.resolved_at = now
                resolved += 1
        s.commit()
    if resolved:
        logger.info("resolved %d predictions", resolved)
    return resolved


def _ref_for(symbol: str, asset_class: str) -> AssetRef:
    from src.assets.types import parse_symbol
    return parse_symbol(symbol, asset_class)


def start_resolver() -> threading.Event:
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            try:
                resolve_due()
            except Exception:
                logger.exception("prediction resolver failed")
            stop.wait(RESOLVE_EVERY)

    threading.Thread(target=loop, daemon=True, name="prediction-resolver").start()
    return stop


# ── Track record ──────────────────────────────────────────────────────────────

def track_record(model_version: str | None = None, horizon: str | None = None) -> dict:
    """Live out-of-sample performance of everything the model has predicted and that has resolved."""
    init_db()
    with Session() as s:
        q = s.query(Prediction)
        if model_version:
            q = q.filter(Prediction.model_version == model_version)
        if horizon:
            q = q.filter(Prediction.horizon == horizon)
        rows = q.all()
    resolved = [r for r in rows if r.resolved_at]
    out = {"total": len(rows), "resolved": len(resolved), "pending": len(rows) - len(resolved),
           "model_version": model_version or "all"}
    if not resolved:
        return out
    P = np.array([[r.probs[s] for s in SCENARIOS] for r in resolved])
    B = np.array([[r.base_probs[s] for s in SCENARIOS] for r in resolved])
    Y = np.array([np.eye(len(SCENARIOS))[SCENARIOS.index(r.outcome_scenario)] for r in resolved])
    out.update(backtest.score(P, B, Y))
    out["actual_distribution"] = {s: int(Y[:, i].sum()) for i, s in enumerate(SCENARIOS)}
    out["mean_predicted"] = {s: round(float(P[:, i].mean()), 4) for i, s in enumerate(SCENARIOS)}
    return out
