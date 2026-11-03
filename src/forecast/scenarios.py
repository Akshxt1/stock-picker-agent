"""What a "scenario" means: forward-return buckets over a fixed horizon.

Definitions are deliberately explicit and versioned with the model, because a
probability only means something relative to the bucket it is attached to. Crypto
gets wider buckets since its typical moves are several times larger.
"""

import numpy as np

from src.assets.types import AssetClass

SCENARIOS = ["CRASH", "DECLINE", "STEADY", "STRONG_GROWTH", "MULTIBAGGER"]

SCENARIO_LABELS = {
    "CRASH": "Crash",
    "DECLINE": "Decline",
    "STEADY": "Steady",
    "STRONG_GROWTH": "Strong growth",
    "MULTIBAGGER": "Multi-bagger",
}

# Calendar days until the outcome is judged.
HORIZON_DAYS = {"3m": 91, "1y": 365}

# Upper bound of each bucket except the last (simple forward return): CRASH <= c0 < DECLINE <= c1 < ...
_CUTS = {
    ("3m", "STANDARD"): [-0.20, -0.05, 0.15, 0.40],
    ("1y", "STANDARD"): [-0.30, -0.10, 0.30, 1.00],
    ("3m", "CRYPTO"): [-0.30, -0.10, 0.20, 0.60],
    ("1y", "CRYPTO"): [-0.50, -0.20, 0.50, 2.00],
}


def _kind(asset_class: AssetClass | str) -> str:
    return "CRYPTO" if AssetClass(asset_class) == AssetClass.CRYPTO else "STANDARD"


def cuts(horizon: str, asset_class: AssetClass | str) -> list[float]:
    if horizon not in HORIZON_DAYS:
        raise ValueError(f"horizon must be one of {sorted(HORIZON_DAYS)}")
    return list(_CUTS[(horizon, _kind(asset_class))])


def horizon_bars(horizon: str, asset_class: AssetClass | str) -> int:
    """Price observations in the horizon: crypto trades daily, markets ~252 days a year."""
    days = HORIZON_DAYS[horizon]
    return days if _kind(asset_class) == "CRYPTO" else round(days * 252 / 365)


def periods_per_year(asset_class: AssetClass | str) -> int:
    return 365 if _kind(asset_class) == "CRYPTO" else 252


def classify(ret, cut_points: list[float]):
    """Scenario index (0=CRASH .. 4=MULTIBAGGER) for a return or array of returns."""
    return np.searchsorted(cut_points, ret, side="left")


def definitions(asset_class: AssetClass | str) -> dict:
    """Human-readable bucket bounds for the UI: {horizon: [{scenario, label, min, max}]}."""
    out = {}
    for h in HORIZON_DAYS:
        c = cuts(h, asset_class)
        bounds = [None] + c + [None]
        out[h] = [{"scenario": s, "label": SCENARIO_LABELS[s],
                   "min": bounds[i], "max": bounds[i + 1]} for i, s in enumerate(SCENARIOS)]
    return out
