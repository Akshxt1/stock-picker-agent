"""Unified entry point: quote / history / metrics / search for any asset class."""

import concurrent.futures

import pandas as pd

from src.assets import crypto, funds
from src.assets.metrics import compute_metrics
from src.assets.types import AssetClass, AssetRef, parse_symbol


def _equity_client():
    from src.providers import market_data_client
    return market_data_client()


def quote(ref: AssetRef) -> dict:
    """{price, day_change_pct, currency, source, ...} in the asset's native currency."""
    if ref.asset_class == AssetClass.CRYPTO:
        return {"symbol": ref.symbol, **crypto.quote(ref.provider_id)}
    if ref.symbol.startswith("MF:"):
        return {"symbol": ref.symbol, **funds.india_quote(ref.provider_id)}
    res = _equity_client().quote(ref.provider_id)
    data = dict(res.data)
    return {"symbol": ref.symbol, "currency": ref.currency, **data}


def history(ref: AssetRef, period: str = "1y") -> pd.DataFrame:
    if ref.asset_class == AssetClass.CRYPTO:
        return crypto.history(ref.provider_id, period)
    if ref.symbol.startswith("MF:"):
        return funds.india_history(ref.provider_id, period)
    return _equity_client().history(ref.provider_id, period).data


def metrics(ref: AssetRef, period: str = "1y") -> dict:
    df = history(ref, period)
    return {"symbol": ref.symbol, "asset_class": ref.asset_class.value, "period": period,
            **compute_metrics(df["Close"], ref.asset_class.value)}


def info(ref: AssetRef) -> dict:
    base = {"symbol": ref.symbol, "asset_class": ref.asset_class.value,
            "market": ref.market, "currency": ref.currency}
    if ref.symbol.startswith("MF:"):
        base.update(funds.india_meta(ref.provider_id))
    elif ref.asset_class == AssetClass.CRYPTO:
        base["name"] = crypto.coin_name(ref.provider_id)
    return base


def batch_quotes(refs: list[AssetRef]) -> dict[str, dict]:
    """Quotes for many assets; crypto is batched into one upstream call, the rest run in parallel.
    Assets whose quote fails are omitted (callers show '—')."""
    out: dict[str, dict] = {}
    coins = [r for r in refs if r.asset_class == AssetClass.CRYPTO]
    if coins:
        try:
            got = crypto.quotes([r.provider_id for r in coins])
        except Exception:
            got = {}
        for r in coins:
            if r.provider_id in got:
                out[r.symbol] = {"symbol": r.symbol, **got[r.provider_id]}

    others = [r for r in refs if r.asset_class != AssetClass.CRYPTO]

    def one(r: AssetRef):
        try:
            return r.symbol, quote(r)
        except Exception:
            return r.symbol, None

    if others:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            for sym, q in ex.map(one, others):
                if q:
                    out[sym] = q
    return out


def search(query: str, asset_class: str | None = None, market: str | None = None,
           limit: int = 10) -> list[dict]:
    """Search crypto and funds (stock search lives in /api/universe/search).

    A failing upstream degrades to fewer results rather than an error.
    """
    wanted = (asset_class or "").upper()
    results: list[dict] = []

    def run(fn, *args):
        try:
            return fn(*args)
        except Exception:
            return []

    if wanted in ("", "CRYPTO") and market in (None, "", "CRYPTO"):
        results += run(crypto.search, query, limit)
    if wanted in ("", "FUND"):
        if market in (None, "", "INDIA"):
            results += run(funds.search_india, query, limit)
        if market in (None, "", "US"):
            results += run(funds.search_us, query, limit)
    return results[: max(limit, 1) * (1 if wanted else 2)]


__all__ = ["quote", "history", "metrics", "info", "batch_quotes", "search", "parse_symbol"]
