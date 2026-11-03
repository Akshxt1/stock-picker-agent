"""
src/api/routes/assets.py — crypto, mutual funds and any other asset by canonical symbol

GET /api/assets/search?q=&asset_class=CRYPTO|FUND&market=INDIA|US|CRYPTO
GET /api/assets/info?symbol=
GET /api/assets/quote?symbol=
GET /api/assets/history?symbol=&period=1y
GET /api/assets/metrics?symbol=&period=1y      — return/risk summary (vol, drawdown, Sharpe, rolling returns)

Symbols: `CRYPTO:bitcoin`, `MF:118989`, or a plain ticker (`AAPL`, `RELIANCE.NS`, `VTSAX`);
see src/assets/types.py. Plain tickers default to EQUITY unless `asset_class=FUND`.
"""

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.routes.auth import get_current_user
from src.assets import service
from src.assets.http import UpstreamError
from src.assets.types import AssetRef, PERIOD_DAYS, parse_symbol

logger = logging.getLogger("stockpicker.assets")

router = APIRouter()


def _ref(symbol: str, asset_class: str | None) -> AssetRef:
    try:
        return parse_symbol(symbol, asset_class)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _period(period: str) -> str:
    if period not in PERIOD_DAYS:
        raise HTTPException(status_code=400, detail=f"period must be one of {sorted(PERIOD_DAYS)}")
    return period


def _upstream(e: Exception):
    logger.warning("asset upstream failure: %s", e)
    raise HTTPException(status_code=502, detail="Market data is temporarily unavailable for this asset.")


def _f(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


@router.get("/search")
def search(
    q: str = Query("", max_length=80),
    asset_class: str | None = Query(None, pattern="^(?i:CRYPTO|FUND)$"),
    market: str | None = Query(None, pattern="^(?i:INDIA|US|CRYPTO)$"),
    limit: int = Query(10, ge=1, le=25),
    _user=Depends(get_current_user),
):
    if not q.strip():
        return []
    return service.search(q, asset_class, market.upper() if market else None, limit)


@router.get("/info")
def info(symbol: str, asset_class: str | None = None, _user=Depends(get_current_user)):
    ref = _ref(symbol, asset_class)
    try:
        return service.info(ref)
    except UpstreamError as e:
        _upstream(e)


@router.get("/quote")
def quote(symbol: str, asset_class: str | None = None, _user=Depends(get_current_user)):
    ref = _ref(symbol, asset_class)
    try:
        return service.quote(ref)
    except Exception as e:
        _upstream(e)


@router.get("/history")
def history(symbol: str, period: str = "1y", asset_class: str | None = None,
            _user=Depends(get_current_user)):
    ref = _ref(symbol, asset_class)
    period = _period(period)
    try:
        df = service.history(ref, period)
    except Exception as e:
        _upstream(e)
    candles = []
    for idx, row in df.iterrows():
        close = _f(row.get("Close"))
        if close is None:
            continue
        candles.append({
            "date": str(idx)[:10],
            "open": _f(row.get("Open")), "high": _f(row.get("High")), "low": _f(row.get("Low")),
            "close": close, "volume": _f(row.get("Volume")),
        })
    return {"symbol": ref.symbol, "asset_class": ref.asset_class.value, "period": period,
            "currency": ref.currency, "candles": candles}


@router.get("/metrics")
def metrics(symbol: str, period: str = "1y", asset_class: str | None = None,
            _user=Depends(get_current_user)):
    ref = _ref(symbol, asset_class)
    period = _period(period)
    try:
        return service.metrics(ref, period)
    except Exception as e:
        _upstream(e)
