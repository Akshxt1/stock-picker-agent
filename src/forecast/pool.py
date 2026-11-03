"""Pooled return distributions (built by scripts/build_forecast_pool.py).

A bank is the sorted, volatility-standardised forward-return sample of a whole asset group
(INDIA, US, CRYPTO) for one horizon. It gives every asset, including ones with short
histories, a far bigger sample of tail behaviour than its own past can.

Banks are stored per "as of" year so a backtest never sees outcomes from after the date it is
forecasting from; live forecasts use the "latest" bank.
"""

import json
import logging
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np

from src.assets.types import AssetClass, AssetRef

PATH = Path(__file__).with_name("pool_banks.json")
STALE_DAYS = 200

logger = logging.getLogger("stockpicker.forecast")


@lru_cache(maxsize=1)
def _load() -> dict:
    try:
        raw = json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("forecast pool %s missing or unreadable; forecasts fall back to own-history only", PATH.name)
        return {}
    built = (raw.get("meta") or {}).get("built")
    try:
        age = (date.today() - date.fromisoformat(built)).days
        if age > STALE_DAYS:
            logger.warning("forecast pool is %d days old; rebuild with scripts/build_forecast_pool.py", age)
    except (TypeError, ValueError):
        pass
    return raw.get("banks", {})


def group_for(ref: AssetRef) -> str:
    if ref.asset_class == AssetClass.CRYPTO:
        return "CRYPTO"
    return "INDIA" if ref.market == "INDIA" else "US"


def bank(horizon: str, group: str, as_of: date | None = None) -> np.ndarray | None:
    """Pooled z sample usable for a forecast made on `as_of` (None = today). None if unavailable."""
    banks = _load()
    if as_of is None:
        key = "latest"
    else:
        years = sorted(int(k) for k in banks if k.isdigit() and int(k) <= as_of.year)
        if not years:
            return None            # before the first cutoff: no leak-free bank exists
        key = str(years[-1])
    z = banks.get(key, {}).get(horizon, {}).get(group)
    return np.asarray(z, dtype=float) if z else None
