# diagnose.py — run with: uv run diagnose.py
import sys, os
sys.path.insert(0, os.getcwd())

from src.database.models import init_db, Session, engine
from sqlalchemy import text

init_db()

print("\n── Columns in portfolio table ───────────────")
with engine.connect() as conn:
    result = conn.execute(text("PRAGMA table_info(portfolio)"))
    cols = result.fetchall()
    for col in cols:
        print(f"  {col[1]:20} {col[2]}")

print("\n── Columns in picks table ───────────────────")
with engine.connect() as conn:
    result = conn.execute(text("PRAGMA table_info(picks)"))
    cols = result.fetchall()
    for col in cols:
        print(f"  {col[1]:20} {col[2]}")

print("\n── All portfolio rows ───────────────────────")
with engine.connect() as conn:
    result = conn.execute(text("SELECT id, ticker, user_id, username, is_open FROM portfolio"))
    rows = result.fetchall()
    print(f"  Total: {len(rows)}")
    for r in rows:
        print(f"  id={r[0]} | {r[1]:10} | user_id={r[2]!r:30} | username={r[3]!r:20} | open={r[4]}")

print("\n── UserProfiles ─────────────────────────────")
with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT user_id, name, email, account_type FROM user_profiles"))
        rows = result.fetchall()
        for r in rows:
            print(f"  {r[1]:20} | {r[2]:30} | {r[3]:10} | uid={r[0][:16] if r[0] else None}...")
    except Exception as e:
        print(f"  user_profiles table error: {e}")