# Handles user registration, login, and password management.
# Passwords are hashed with bcrypt — never stored as plain text.

import bcrypt
from datetime import datetime
from src.database.models import Session, User


def register_user(username: str, email: str, name: str, password: str) -> dict:
    """
    Create a new user account.
    Returns {"success": True, "username": ...} or {"success": False, "error": ...}
    """
    session = Session()
    try:
        uname = username.lower().strip()
        email = email.lower().strip()

        if session.query(User).filter(User.username == uname).first():
            return {"success": False, "error": "Username already taken"}
        if session.query(User).filter(User.email == email).first():
            return {"success": False, "error": "Email already registered"}
        if len(password) < 6:
            return {"success": False, "error": "Password must be at least 6 characters"}

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user   = User(username=uname, email=email, name=name.strip(), password=hashed)
        session.add(user)
        session.commit()
        return {"success": True, "username": uname, "name": name.strip()}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def login_user(username: str, password: str) -> dict:
    """
    Authenticate a user.
    Returns {"success": True, "username": ..., "name": ...} or {"success": False, "error": ...}
    """
    session = Session()
    try:
        user = session.query(User).filter(
            User.username == username.lower().strip()
        ).first()

        if not user:
            return {"success": False, "error": "Username not found"}
        if not user.is_active:
            return {"success": False, "error": "Account is inactive"}
        if not bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
            return {"success": False, "error": "Incorrect password"}

        return {
            "success":  True,
            "username": user.username,
            "name":     user.name,
            "email":    user.email,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def get_user_info(username: str) -> dict | None:
    """Return basic info about a user, or None if not found."""
    session = Session()
    user    = session.query(User).filter(User.username == username).first()
    session.close()
    if not user:
        return None
    return {
        "username":   user.username,
        "name":       user.name,
        "email":      user.email,
        "created_at": user.created_at.strftime("%d %b %Y"),
    }


def change_password(username: str, old_password: str, new_password: str) -> dict:
    """Change a user's password after verifying the old one."""
    check = login_user(username, old_password)
    if not check["success"]:
        return {"success": False, "error": "Current password is incorrect"}
    if len(new_password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters"}

    session = Session()
    try:
        user          = session.query(User).filter(User.username == username).first()
        user.password = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        session.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()
