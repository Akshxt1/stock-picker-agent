# src/auth/supabase_auth.py
# Supabase auth client — sign up, sign in, sign out, get user

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client = None

def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in your .env file.\n"
                "Get them from: https://supabase.com → your project → Settings → API"
            )
        _client = create_client(url, key)
    return _client


def sign_up(email: str, password: str, name: str) -> dict:
    """
    Register a new user via Supabase Auth.
    Returns {"success": True, "user": ...} or {"success": False, "error": ...}
    """
    try:
        client   = get_client()
        response = client.auth.sign_up({
            "email":    email.lower().strip(),
            "password": password,
            "options":  {"data": {"name": name.strip()}}
        })
        if response.user:
            _ensure_profile(response.user.id, email, name)
            return {
                "success":  True,
                "user_id":  response.user.id,
                "email":    response.user.email,
                "name":     name,
            }
        return {"success": False, "error": "Registration failed. Try again."}
    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower() or "already exists" in msg.lower():
            return {"success": False, "error": "Email already registered"}
        return {"success": False, "error": msg}


def sign_in(email: str, password: str) -> dict:
    """
    Sign in with email + password.
    Returns {"success": True, "user_id", "email", "name", "account_type", "session"} or error.
    """
    try:
        client   = get_client()
        response = client.auth.sign_in_with_password({
            "email":    email.lower().strip(),
            "password": password,
        })
        if response.user:
            profile = _get_or_create_profile(
                response.user.id,
                response.user.email,
                response.user.user_metadata.get("name", email.split("@")[0]),
            )
            return {
                "success":      True,
                "user_id":      response.user.id,
                "email":        response.user.email,
                "name":         profile.get("name",""),
                "account_type": profile.get("account_type","free"),
                "session":      response.session,
            }
        return {"success": False, "error": "Sign-in failed"}
    except Exception as e:
        msg = str(e)
        if "invalid" in msg.lower() or "credentials" in msg.lower():
            return {"success": False, "error": "Invalid email or password"}
        return {"success": False, "error": msg}


def sign_in_as_guest() -> dict:
    """Return a guest session (no Supabase call needed)."""
    return {
        "success":      True,
        "user_id":      "guest",
        "email":        "guest@stockpicker",
        "name":         "Guest",
        "account_type": "guest",
        "session":      None,
    }


def sign_out() -> None:
    """Sign out the current user."""
    try:
        get_client().auth.sign_out()
    except Exception:
        pass


def reset_password_email(email: str) -> dict:
    """Send a password-reset email via Supabase."""
    try:
        get_client().auth.reset_password_email(email.lower().strip())
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Profile helpers (stored in our SQLite) ────────────────────────────────────

def _ensure_profile(user_id: str, email: str, name: str):
    """Create a profile row in SQLite if one doesn't exist yet."""
    from src.database.models import Session, UserProfile
    session = Session()
    try:
        if not session.query(UserProfile).filter_by(user_id=user_id).first():
            session.add(UserProfile(
                user_id      = user_id,
                email        = email,
                name         = name,
                account_type = "free",
            ))
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _get_or_create_profile(user_id: str, email: str, name: str) -> dict:
    """Get or create a SQLite profile for a Supabase user."""
    from src.database.models import Session, UserProfile
    session = Session()
    try:
        profile = session.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(
                user_id=user_id, email=email, name=name, account_type="free"
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
        return {
            "user_id":      profile.user_id,
            "email":        profile.email,
            "name":         profile.name,
            "account_type": profile.account_type,
        }
    except Exception:
        return {"user_id": user_id, "email": email, "name": name, "account_type": "free"}
    finally:
        session.close()