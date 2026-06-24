"""
src/api/routes/auth.py
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger("stockpicker.auth")

try:
    from supabase import create_client, Client as SupabaseClient
    _SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    _SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    supabase: SupabaseClient = create_client(_SUPABASE_URL, _SUPABASE_KEY) if _SUPABASE_URL else None
except ImportError:
    supabase = None

# Only allow the unauthenticated "dev admin" bypass when explicitly in dev mode.
# In production (the default) a missing Supabase config must FAIL CLOSED, never
# silently grant admin access to every request.
_DEV_MODE = os.getenv("APP_ENV", "production").strip().lower() in ("dev", "development", "local")

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "akshatgupta428@gmail.com")


def _dev_admin_user() -> dict:
    return {
        "user_id": "dev", "email": ADMIN_EMAIL, "name": "Dev",
        "account_type": "admin", "weekly_runs": 0,
        "limits": {"crew_runs": 9999, "portfolio_runs": 9999},
    }


def _require_supabase():
    """Fail closed when auth isn't configured (unless explicitly in dev mode)."""
    if supabase is None and not _DEV_MODE:
        logger.error("Auth request received but Supabase is not configured (production mode).")
        raise HTTPException(
            status_code=503,
            detail="Authentication service is not configured. Please contact the administrator.",
        )


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
        if _DEV_MODE:
            return _dev_admin_user()
        _require_supabase()
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
        if _DEV_MODE:
            return {"access_token": "dev-token", "user": _dev_admin_user()}
        _require_supabase()
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
        # Don't leak provider internals or reveal whether an email exists.
        logger.warning("Login failed for %s: %s", body.email, e)
        raise HTTPException(status_code=401, detail="Invalid email or password.")


@router.post("/signup")
def signup(body: SignupRequest):
    if not supabase:
        if _DEV_MODE:
            return {"message": "Dev mode — signup skipped"}
        _require_supabase()
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
        logger.warning("Signup failed for %s: %s", body.email, e)
        raise HTTPException(status_code=400, detail="Could not create the account. Please try again.")


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    if not supabase:
        if _DEV_MODE:
            return {"message": "Dev mode — skipped"}
        _require_supabase()
    try:
        supabase.auth.reset_password_email(body.email)
    except Exception as e:
        # Log but always return success so we don't reveal which emails are registered.
        logger.warning("Password reset failed for %s: %s", body.email, e)
    return {"message": "If that email is registered, a password reset link has been sent."}
