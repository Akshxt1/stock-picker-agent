"""
src/api/routes/portfolio_agent.py — upload a portfolio (screenshot / PDF / CSV / Excel) and get a strategy

POST /api/portfolio-agent/parse        multipart file -> draft holdings matched to real symbols (nothing is stored)
POST /api/portfolio-agent/analyze      confirmed holdings -> live values, P&L, risk, simulation (no AI, no quota)
POST /api/portfolio-agent/strategy     confirmed holdings + goal -> {job_id}; costs 1 weekly portfolio-run quota
GET  /api/portfolio-agent/jobs/{id}    poll the strategy job: status, progress, result (refunded automatically on failure)

Guests are blocked. The strategy runs on the durable job queue because the AI step takes 20-60 seconds.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.api.routes.auth import get_current_user
from src.assets.types import parse_symbol
from src.jobs import service as jobs
from src.portfolio_agent import analysis, extract, job as strategy_job, match, strategy
from src.portfolio_agent.llm import AgentUnavailable, NotConfigured

logger = logging.getLogger("stockpicker.portfolio_agent")

router = APIRouter()


class HoldingIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    quantity: float = Field(gt=0, le=1e12)
    avg_price: float | None = Field(default=None, gt=0, le=1e13)
    asset_class: str | None = Field(default=None, pattern="^(EQUITY|FUND|CRYPTO)$")
    name: str | None = Field(default=None, max_length=120)


class AnalyzeRequest(BaseModel):
    holdings: list[HoldingIn] = Field(min_length=1, max_length=analysis.MAX_HOLDINGS)


class StrategyRequest(AnalyzeRequest):
    goal: str = Field(default="", max_length=strategy.MAX_GOAL)
    risk: str = Field(default="moderate", pattern="^(conservative|moderate|aggressive)$")


def _no_guests(user):
    if user.get("account_type") == "guest":
        raise HTTPException(status_code=403, detail="Guest accounts can't use the portfolio agent. Please sign up.")


def _agent_error(e: AgentUnavailable):
    if isinstance(e, NotConfigured):
        raise HTTPException(status_code=503, detail=str(e))
    raise HTTPException(status_code=422, detail=str(e))


@router.post("/parse")
def parse_upload(file: UploadFile = File(...), user=Depends(get_current_user)):
    _no_guests(user)
    data = file.file.read(extract.MAX_BYTES + 1)         # never read more than the cap
    try:
        draft = extract.extract_holdings(data)
    except extract.UnsupportedFile as e:
        raise HTTPException(status_code=415, detail=str(e))
    except AgentUnavailable as e:
        _agent_error(e)
    except Exception:
        logger.exception("portfolio upload parse failed")
        raise HTTPException(status_code=502, detail="The AI service is temporarily unavailable. Please try again.")
    rows = match.match_rows(draft["holdings"], draft["portfolio_currency"])
    return {"source": draft["source"], "portfolio_currency": draft["portfolio_currency"],
            "notes": draft["notes"], "rows": rows}


@router.post("/analyze")
def analyze_portfolio(req: AnalyzeRequest, user=Depends(get_current_user)):
    _no_guests(user)
    try:
        return analysis.analyze([h.model_dump() for h in req.holdings])
    except ValueError as e:                      # AnalysisError and bad symbols
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/strategy")
def start_strategy(req: StrategyRequest, user=Depends(get_current_user)):
    _no_guests(user)
    account_type = user.get("account_type", "trial")
    if not strategy.configured():
        raise HTTPException(status_code=503, detail="AI features are not configured on this server.")
    for h in req.holdings:                       # cheap input check before any quota is spent
        try:
            parse_symbol(h.symbol, h.asset_class)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    from src.database.models import ACCOUNT_LIMITS, increment_portfolio_run_count
    try:
        allowed = increment_portfolio_run_count(user["user_id"])
    except Exception:
        logger.exception("portfolio-agent quota check failed for %s", user.get("user_id"))
        raise HTTPException(status_code=503, detail="Could not verify your usage quota. Please retry shortly.")
    if not allowed:
        limit = ACCOUNT_LIMITS.get(account_type, {}).get("portfolio_runs", 0)
        raise HTTPException(status_code=429, detail=f"Weekly analysis limit reached ({limit} deep/portfolio runs for "
                                                    f"{account_type} plan). Resets next Monday.")
    try:
        job_id = jobs.enqueue(strategy_job.KIND, user["user_id"], user.get("name"),
                              {"holdings": [h.model_dump() for h in req.holdings], "goal": req.goal, "risk": req.risk})
    except Exception:
        logger.exception("could not enqueue portfolio strategy job")
        jobs.refund_quota(user["user_id"], strategy_job.KIND)
        raise HTTPException(status_code=503, detail="Could not start the run. Please retry shortly.")
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def strategy_status(job_id: str, user=Depends(get_current_user)):
    job = jobs.get_job(job_id)
    if not job or job["kind"] != strategy_job.KIND or \
            (job["user_id"] != user["user_id"] and user.get("account_type") != "admin"):
        raise HTTPException(status_code=404, detail="Job not found")
    events = jobs.events_after(job_id, 0)
    progress = next((p.get("text") for _, p in reversed(events) if p.get("type") == "progress"), None)
    return {"status": job["status"], "progress": progress, "result": job["result"],
            "error": job["error"] if job["status"] == "error" else None}
