# src/auth/supabase_auth.py

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Absolute path to the project root (assuming this file is in src/auth/)
# This goes up two levels to reach the root folder
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env_path = os.path.join(root_dir, ".env")

# Force load the file at this exact location
load_dotenv(dotenv_path=env_path)

def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        # If this triggers, your .env file is either missing or empty
        raise ValueError(f"CRITICAL: Supabase keys missing. Python checked exactly this file: {env_path}")
    
    return create_client(url, key)

def _format_user(user_obj, role="free", name="User"):
    return {
        "user_id": user_obj.user.id,
        "email": user_obj.user.email,
        "name": user_obj.user.user_metadata.get("name", name) if user_obj.user.user_metadata else name,
        "account_type": user_obj.user.user_metadata.get("account_type", role) if user_obj.user.user_metadata else role
    }

def sign_in(email: str, password: str):
    clean_email = email.strip().lower()
    supabase = get_client()
    res = supabase.auth.sign_in_with_password({"email": clean_email, "password": password})
    return _format_user(res)

def sign_up(email: str, password: str, name: str):
    clean_email = email.strip().lower()
    supabase = get_client()
    res = supabase.auth.sign_up({
        "email": clean_email, 
        "password": password,
        "options": {"data": {"name": name, "account_type": "free"}}
    })
    return _format_user(res, role="free", name=name)

def sign_out():
    supabase = get_client()
    supabase.auth.sign_out()