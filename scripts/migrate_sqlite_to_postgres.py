"""
One-time migration: copy all rows from the local SQLite DB into a Postgres
database (Railway / Supabase). Run this once after provisioning Postgres, before
switching the deployed app over to it.

Usage (from the project root):

    # dest comes from DATABASE_URL (Railway/Supabase connection string)
    DATABASE_URL="postgresql://user:pass@host:5432/dbname" \
        uv run python scripts/migrate_sqlite_to_postgres.py

    # or pass source/dest explicitly
    uv run python scripts/migrate_sqlite_to_postgres.py \
        --source sqlite:///src/database/stock_picker.db \
        --dest   postgresql://user:pass@host:5432/dbname

Safe to re-run: tables that already contain rows in the destination are skipped,
so it never duplicates data.
"""

import argparse
import os
import sys

from sqlalchemy import create_engine

# Import the schema (Base + all model classes register their tables on Base).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database.models import Base  # noqa: E402


def _normalize(url: str) -> str:
    return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy SQLite data into Postgres.")
    parser.add_argument("--source", default="sqlite:///src/database/stock_picker.db",
                        help="Source SQLAlchemy URL (default: local SQLite file)")
    parser.add_argument("--dest", default=os.getenv("DATABASE_URL", ""),
                        help="Destination SQLAlchemy URL (default: $DATABASE_URL)")
    args = parser.parse_args()

    if not args.dest:
        print("ERROR: no destination — pass --dest or set DATABASE_URL.", file=sys.stderr)
        return 1

    src = create_engine(_normalize(args.source))
    dst = create_engine(_normalize(args.dest), pool_pre_ping=True)

    # Make sure the schema exists on the destination.
    Base.metadata.create_all(dst)

    total = 0
    with src.connect() as src_conn, dst.begin() as dst_conn:
        # sorted_tables respects foreign-key order (parents before children).
        for table in Base.metadata.sorted_tables:
            existing = dst_conn.execute(table.select().limit(1)).first()
            if existing is not None:
                print(f"  skip  {table.name:20} (destination already has rows)")
                continue

            rows = src_conn.execute(table.select()).fetchall()
            if not rows:
                print(f"  empty {table.name:20} (nothing to copy)")
                continue

            dst_conn.execute(table.insert(), [dict(r._mapping) for r in rows])
            print(f"  copied {table.name:20} {len(rows):>6} rows")
            total += len(rows)

    print(f"\nDone. Migrated {total} rows into {dst.url.render_as_string(hide_password=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
