"""
src/api/routes/picks.py

GET    /api/picks           — all picks for current user
GET    /api/picks/{pick_id} — single pick
DELETE /api/picks/{pick_id} — delete a pick
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from src.api.routes.auth import get_current_user

try:
    from src.database.models import get_user_picks, delete_pick
    _DB = True
except ImportError:
    _DB = False

router = APIRouter()


@router.get("")
def list_picks(
    market: str | None = Query(None, description="Filter by market: INDIA or US"),
    user=Depends(get_current_user),
):
    if not _DB:
        return []
    try:
        return get_user_picks(user["user_id"], market=market.upper() if market else None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pick_id}")
def get_pick(pick_id: int, user=Depends(get_current_user)):
    if not _DB:
        raise HTTPException(status_code=404, detail="Not found")
    picks = get_user_picks(user["user_id"])
    match = next((p for p in picks if p.get("id") == pick_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Pick not found")
    return match


@router.delete("/{pick_id}")
def remove_pick(pick_id: int, user=Depends(get_current_user)):
    if not _DB:
        return {"ok": True}
    try:
        delete_pick(pick_id, user["user_id"])
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
