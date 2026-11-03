"""Rebuild src/forecast/pool_banks.json: pooled, volatility-standardised forward-return
distributions per asset group and horizon, for every "as of" cutoff.

    uv run python scripts/build_forecast_pool.py

For each year cutoff Y (and "latest") a bank holds only outcomes that had already ended before
Jan 1 of Y, so a backtest at a date in year Y that uses the Y bank sees no future information.
Source: ~250 large-cap stocks and ETFs (India, US) plus major coins, from Yahoo (adjusted prices).
The universe is today's large caps, so the pooled distribution is survivorship-flattered; the
model removes its drift (see model.py). Re-run roughly quarterly.
"""

import json
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

import yfinance as yf  # noqa: E402

from src.assets.crypto import YF_FALLBACK  # noqa: E402
from src.data.stock_universe import get_stocks  # noqa: E402
from src.forecast import model  # noqa: E402
from src.forecast.scenarios import HORIZON_DAYS, horizon_bars  # noqa: E402

OUT = ROOT / "src" / "forecast" / "pool_banks.json"
FIRST_CUTOFF = 2019
POINTS = 1001

GROUPS = {
    "INDIA": ("EQUITY", get_stocks("INDIA")),
    "US": ("EQUITY", get_stocks("US") + ["SPY", "QQQ", "VTI", "IWM", "EFA", "EEM", "TLT", "GLD",
                                         "XLF", "XLK", "XLE", "XLV"]),
    "CRYPTO": ("CRYPTO", [v for k, v in YF_FALLBACK.items() if k not in ("tether", "usd-coin")]),
}


def download(tickers: list[str], period: str) -> dict[str, pd.Series]:
    out = {}
    tickers = sorted(set(tickers))
    for i in range(0, len(tickers), 40):
        batch = tickers[i:i + 40]
        df = yf.download(batch, period=period, auto_adjust=True, progress=False,
                         group_by="ticker", threads=True)
        for t in batch:
            try:
                s = df[t]["Close"].dropna()
                s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
                s = s[~s.index.duplicated()]
                if len(s) > 400:
                    out[t] = s[s > 0]
            except Exception:
                pass
    return out


def main():
    cutoffs = list(range(FIRST_CUTOFF, date.today().year + 1)) + ["latest"]
    banks: dict = {}
    for group, (kind, tickers) in GROUPS.items():
        series = download(tickers, "max" if group == "CRYPTO" else "10y")
        print(f"{group}: {len(series)}/{len(set(tickers))} assets", flush=True)
        for horizon in HORIZON_DAYS:
            bars = horizon_bars(horizon, kind)
            zs, ends = [], []
            for close in series.values():
                lc = np.log(close.values)
                if len(lc) <= bars:
                    continue
                fwd = np.full(len(lc), np.nan)
                fwd[:-bars] = lc[bars:] - lc[:-bars]
                z = fwd / (model.trailing_vol(close).values * np.sqrt(bars))
                end = np.full(len(lc), np.datetime64("NaT"), dtype="datetime64[ns]")
                end[:-bars] = close.index.values[bars:]
                ok = np.isfinite(z)
                zs.append(z[ok])
                ends.append(end[ok])
            z, end = np.concatenate(zs), np.concatenate(ends)
            for c in cutoffs:
                mask = np.ones(len(z), bool) if c == "latest" else end < np.datetime64(f"{c}-01-01")
                zz = z[mask]
                if len(zz) < 2000:
                    continue
                q = np.quantile(zz - zz.mean(), np.linspace(0, 1, POINTS))
                banks.setdefault(str(c), {}).setdefault(horizon, {})[group] = [round(float(v), 3) for v in q]
    meta = {"built": date.today().isoformat(), "points": POINTS, "source": "yahoo adjusted, ~250 large caps/ETFs + major coins"}
    OUT.write_text(json.dumps({"meta": meta, "banks": banks}, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB), cutoffs: {sorted(banks)}")


if __name__ == "__main__":
    main()
