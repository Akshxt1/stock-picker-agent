"""
src/api/routes/admin.py

Protected endpoints — only account_type='admin' can access.

GET  /api/admin/users                       — all user profiles
PATCH /api/admin/users/{user_id}/account-type — update a user's account type
GET  /api/admin/usage                       — token usage stats
GET  /api/admin/runs                        — recent crew run log
GET  /api/admin/logs                        — last N lines from app log file
"""

import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api.routes.auth import get_current_user, ADMIN_EMAIL

router = APIRouter()

LOG_FILE = Path(__file__).parents[3] / "logs" / "app.log"

def require_admin(user=Depends(get_current_user)):
    is_admin = user.get("account_type") == "admin" or user.get("email") == ADMIN_EMAIL
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(_user=Depends(require_admin)):
    try:
        from src.database.models import get_all_user_profiles
        return get_all_user_profiles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AccountTypeBody(BaseModel):
    account_type: str


@router.patch("/users/{user_id}/account-type")
def set_account_type(user_id: str, body: AccountTypeBody, _user=Depends(require_admin)):
    try:
        from src.database.models import update_account_type
        ok = update_account_type(user_id, body.account_type)
        if not ok:
            raise HTTPException(status_code=400, detail="Invalid account type or user not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Usage stats ───────────────────────────────────────────────────────────────

@router.get("/usage")
def usage_stats(_user=Depends(require_admin)):
    try:
        from src.database.models import Session, ApiUsage
        with Session() as sess:
            rows = sess.query(ApiUsage).order_by(ApiUsage.timestamp.desc()).limit(200).all()
        total_cost  = sum(r.estimated_cost or 0 for r in rows)
        total_in    = sum(r.input_tokens or 0 for r in rows)
        total_out   = sum(r.output_tokens or 0 for r in rows)
        by_user: dict = {}
        for r in rows:
            uid = r.username or r.user_id or "unknown"
            if uid not in by_user:
                by_user[uid] = {"calls": 0, "cost": 0.0, "tokens": 0}
            by_user[uid]["calls"]  += 1
            by_user[uid]["cost"]   += r.estimated_cost or 0
            by_user[uid]["tokens"] += (r.input_tokens or 0) + (r.output_tokens or 0)
        return {
            "total_calls":        len(rows),
            "total_input_tokens": total_in,
            "total_output_tokens":total_out,
            "total_cost_usd":     round(total_cost, 4),
            "by_user":            by_user,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Recent runs ───────────────────────────────────────────────────────────────

@router.get("/runs")
def recent_runs(_user=Depends(require_admin)):
    try:
        from src.database.models import Session, ApiUsage
        with Session() as sess:
            rows = sess.query(ApiUsage).order_by(ApiUsage.timestamp.desc()).limit(50).all()
        return [
            {
                "id":            r.id,
                "timestamp":     r.timestamp.isoformat() if r.timestamp else None,
                "user":          r.username or r.user_id,
                "model":         r.model,
                "agent":         r.agent,
                "context":       r.run_context,
                "input_tokens":  r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd":      round(r.estimated_cost or 0, 5),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── App logs ──────────────────────────────────────────────────────────────────

@router.get("/logs")
def app_logs(lines: int = 100, _user=Depends(require_admin)):
    try:
        if not LOG_FILE.exists():
            return {"lines": [], "path": str(LOG_FILE)}
        content = LOG_FILE.read_text(encoding="utf-8", errors="replace")
        all_lines = content.splitlines()
        return {
            "lines": all_lines[-lines:],
            "total": len(all_lines),
            "path":  str(LOG_FILE),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Scheduler status ──────────────────────────────────────────────────────────

@router.get("/scheduler")
def scheduler_status(_user=Depends(require_admin)):
    try:
        from src.database.models import Session, SystemSettings
        with Session() as sess:
            row = sess.query(SystemSettings).filter(SystemSettings.key == "scheduler").first()
        return row.value if row else {"enabled": False, "jobs": []}
    except Exception as e:
        return {"enabled": False, "jobs": [], "error": str(e)}


@router.post("/scheduler")
def update_scheduler(config: dict, _user=Depends(require_admin)):
    try:
        from src.database.models import Session, SystemSettings
        from datetime import datetime, timezone
        with Session() as sess:
            row = sess.query(SystemSettings).filter(SystemSettings.key == "scheduler").first()
            if row:
                row.value = config
            else:
                sess.add(SystemSettings(key="scheduler", value=config))
            sess.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
