"""
src/api/routes/auth.py
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

try:
    from supabase import create_client, Client as SupabaseClient
    _SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    _SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    supabase: SupabaseClient = create_client(_SUPABASE_URL, _SUPABASE_KEY) if _SUPABASE_URL else None
except ImportError:
    supabase = None

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

ADMIN_EMAIL = "akshatgupta428@gmail.com"


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    username: str = ""

class ForgotPasswordRequest(BaseModel):
    email: str

class UpdateAccountTypeRequest(BaseModel):
    account_type: str


# ── Dependency ────────────────────────────────────────────────────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    if not supabase:
        return {"user_id": "dev", "email": "akshatgupta428@gmail.com",
                "name": "Dev", "account_type": "admin", "weekly_runs": 0,
                "limits": {"crew_runs": 9999, "portfolio_runs": 9999}}
    try:
        resp = supabase.auth.get_user(token)
        user = resp.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        try:
            from src.database.models import upsert_user_profile
            profile = upsert_user_profile(
                user_id=user.id,
                email=user.email,
                username=(user.user_metadata or {}).get("username", ""),
            )
        except Exception:
            profile = {"account_type": "trial", "weekly_runs": 0,
                       "limits": {"crew_runs": 2, "portfolio_runs": 3}}
        return {
            "user_id":      user.id,
            "email":        user.email,
            "name":         (user.user_metadata or {}).get("username") or user.email.split("@")[0],
            "account_type": profile["account_type"],
            "weekly_runs":  profile["weekly_runs"],
            "weekly_portfolio_runs": profile.get("weekly_portfolio_runs", 0),
            "limits":       profile["limits"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(body: LoginRequest):
    if not supabase:
        return {
            "access_token": "dev-token",
            "user": {"user_id": "dev", "email": body.email,
                     "name": "Dev", "account_type": "admin",
                     "weekly_runs": 0, "limits": {"crew_runs": 9999, "portfolio_runs": 9999}},
        }
    try:
        resp = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
        user = resp.user
        try:
            from src.database.models import upsert_user_profile
            profile = upsert_user_profile(
                user_id=user.id, email=user.email,
                username=(user.user_metadata or {}).get("username", ""),
            )
            account_type = profile["account_type"]
            weekly_runs  = profile["weekly_runs"]
            limits       = profile["limits"]
        except Exception:
            account_type = "trial"; weekly_runs = 0
            limits = {"crew_runs": 2, "portfolio_runs": 3}

        return {
            "access_token": resp.session.access_token,
            "user": {
                "user_id":      user.id,
                "email":        user.email,
                "name":         (user.user_metadata or {}).get("username") or user.email.split("@")[0],
                "account_type": account_type,
                "weekly_runs":  weekly_runs,
                "limits":       limits,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/signup")
def signup(body: SignupRequest):
    if not supabase:
        return {"message": "Dev mode — signup skipped"}
    try:
        resp = supabase.auth.sign_up({
            "email":    body.email,
            "password": body.password,
            "options":  {"data": {"username": body.username}},
        })
        return {
            "message": "Check your email to confirm your account.",
            "user_id": resp.user.id if resp.user else None,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    if not supabase:
        return {"message": "Dev mode — skipped"}
    try:
        supabase.auth.reset_password_email(body.email)
        return {"message": "Password reset email sent."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
