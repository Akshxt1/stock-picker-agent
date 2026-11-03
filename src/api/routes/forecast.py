"""
src/api/routes/forecast.py — scenario forecasts (crash / decline / steady / strong growth / multi-bagger)

GET  /api/forecast?symbol=&horizon=3m|1y       — scenario probabilities, return quantiles; logged to the track record
GET  /api/forecast/backtest?symbol=&horizon=   — walk-forward score of the model on this asset's own history
GET  /api/forecast/track-record?horizon=&model_version=  — live, out-of-sample score of every resolved prediction
GET  /api/forecast/explain?symbol=&horizon=    — AI bull case / bear case grounded in the forecast data (cached)
GET  /api/forecast/scenarios?symbol=           — bucket definitions
POST /api/forecast/resolve                     — admin: resolve predictions that have come due

Probabilities describe how often each outcome has followed similar volatility conditions in the
asset's past. They are not investment advice and carry no guarantee.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.routes.admin import require_admin
from src.api.routes.auth import get_current_user
from src.assets.http import UpstreamError
from src.assets.types import parse_symbol
from src.forecast import explain, service
from src.forecast.scenarios import HORIZON_DAYS, definitions

logger = logging.getLogger("stockpicker.forecast")

router = APIRouter()

_HORIZON = Query("3m", pattern="^(3m|1y)$")


def _ref(symbol: str, asset_class: str | None):
    try:
        return parse_symbol(symbol, asset_class)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def get_forecast(symbol: str, horizon: str = _HORIZON, asset_class: str | None = None,
                 _user=Depends(get_current_user)):
    ref = _ref(symbol, asset_class)
    try:
        return service.forecast(ref, horizon)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except UpstreamError as e:
        logger.warning("forecast upstream failure: %s", e)
        raise HTTPException(status_code=502, detail="Market data is temporarily unavailable for this asset.")


@router.get("/backtest")
def get_backtest(symbol: str, horizon: str = _HORIZON, asset_class: str | None = None,
                 _user=Depends(get_current_user)):
    ref = _ref(symbol, asset_class)
    try:
        return service.run_backtest(ref, horizon)
    except UpstreamError as e:
        logger.warning("backtest upstream failure: %s", e)
        raise HTTPException(status_code=502, detail="Market data is temporarily unavailable for this asset.")


@router.get("/track-record")
def get_track_record(horizon: str | None = Query(None, pattern="^(3m|1y)$"),
                     model_version: str | None = Query(None, max_length=40),
                     _user=Depends(get_current_user)):
    return service.track_record(model_version=model_version, horizon=horizon)


@router.get("/explain")
def get_explanation(symbol: str, horizon: str = _HORIZON, asset_class: str | None = None,
                    _user=Depends(get_current_user)):
    ref = _ref(symbol, asset_class)
    try:
        return explain.explain(ref, horizon)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except UpstreamError as e:
        logger.warning("explain upstream failure: %s", e)
        raise HTTPException(status_code=502, detail="Market data is temporarily unavailable for this asset.")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("explain failed for %s", symbol)
        raise HTTPException(status_code=502, detail="The AI service is temporarily unavailable.")


@router.get("/scenarios")
def get_scenarios(symbol: str = "AAPL", asset_class: str | None = None, _user=Depends(get_current_user)):
    ref = _ref(symbol, asset_class)
    return {"horizons": HORIZON_DAYS, "definitions": definitions(ref.asset_class)}


@router.post("/resolve")
def resolve(_admin=Depends(require_admin)):
    return {"resolved": service.resolve_due()}
