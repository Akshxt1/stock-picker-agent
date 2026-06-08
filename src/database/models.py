# src/database/models.py  (final version with auth + api usage)

from sqlalchemy import (
    create_engine, Column, Integer, Float,
    String, DateTime, Boolean, Text, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "stock_picker.db")
DB_URL  = f"sqlite:///{DB_PATH}"

engine  = create_engine(DB_URL, echo=False)
Base    = declarative_base()
Session = sessionmaker(bind=engine)


# ── UserProfile ───────────────────────────────────────────────────────────────
# Mirrors Supabase auth users, stores our extra metadata locally.

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(String(100), unique=True, nullable=False)  # Supabase UUID
    email        = Column(String(200), nullable=False)
    name         = Column(String(200), nullable=False)
    # account_type: admin | premium | free | guest
    account_type = Column(String(20), default="free", nullable=False)
    is_active    = Column(Boolean,    default=True)
    created_at   = Column(DateTime,   default=datetime.utcnow)

    def __repr__(self):
        return f"<UserProfile {self.email} [{self.account_type}]>"


# ── ApiUsage ──────────────────────────────────────────────────────────────────
# Logs every Claude API call so we can track cost per user.

class ApiUsage(Base):
    __tablename__ = "api_usage"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(String(100), nullable=True)   # Supabase UUID
    username     = Column(String(200), nullable=True)   # display name
    model        = Column(String(100), nullable=False)  # claude-haiku-4-5...
    agent        = Column(String(100), nullable=True)   # Researcher, Analyst etc.
    run_context  = Column(String(200), nullable=True)   # "INDIA · Technology · Large"
    input_tokens = Column(Integer,     default=0)
    output_tokens= Column(Integer,     default=0)
    cost_usd     = Column(Float,       default=0.0)
    timestamp    = Column(DateTime,    default=datetime.utcnow)

    def __repr__(self):
        return f"<ApiUsage {self.username} {self.model} ${self.cost_usd:.4f}>"


# ── Picks ─────────────────────────────────────────────────────────────────────

class Pick(Base):
    __tablename__ = "picks"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    ticker           = Column(String(20),  nullable=False)
    company          = Column(String(200), nullable=False)
    market           = Column(String(10),  nullable=False)
    sector           = Column(String(100), nullable=False)
    size             = Column(String(20),  nullable=False)
    currency         = Column(String(5),   nullable=False)
    price_at_pick    = Column(Float,       nullable=False)
    why_buy          = Column(JSON,        nullable=True)
    why_not_buy      = Column(JSON,        nullable=True)
    technical_signal = Column(String(20),  nullable=True)
    sentiment        = Column(String(20),  nullable=True)
    confidence       = Column(String(10),  nullable=True)
    analysis_date    = Column(String(20),  nullable=False)
    created_at       = Column(DateTime,    default=datetime.utcnow)
    in_portfolio     = Column(Boolean,     default=False)
    run_by_user_id   = Column(String(100), nullable=True)   # who triggered this run

    def __repr__(self):
        return f"<Pick {self.ticker} | {self.confidence} | {self.analysis_date}>"


# ── Portfolio ─────────────────────────────────────────────────────────────────

class Portfolio(Base):
    __tablename__ = "portfolio"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(String(100), nullable=True)   # Supabase UUID
    username        = Column(String(200), nullable=True)   # display name
    pick_id         = Column(Integer,     nullable=True)
    ticker          = Column(String(20),  nullable=False)
    company         = Column(String(200), nullable=False)
    market          = Column(String(10),  nullable=False)
    sector          = Column(String(100), nullable=False)
    currency        = Column(String(5),   nullable=False)
    entry_price     = Column(Float,       nullable=False)
    quantity        = Column(Float,       nullable=False)
    invested_amount = Column(Float,       nullable=False)
    is_open         = Column(Boolean,     default=True)
    exit_price      = Column(Float,       nullable=True)
    exit_date       = Column(DateTime,    nullable=True)
    entry_date      = Column(DateTime,    default=datetime.utcnow)

    def __repr__(self):
        return f"<Portfolio {self.ticker} {'OPEN' if self.is_open else 'CLOSED'}>"


# ── Transactions ──────────────────────────────────────────────────────────────

class Transaction(Base):
    __tablename__ = "transactions"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(String(100), nullable=True)
    username     = Column(String(200), nullable=True)
    portfolio_id = Column(Integer,     nullable=True)
    ticker       = Column(String(20),  nullable=False)
    action       = Column(String(10),  nullable=False)
    price        = Column(Float,       nullable=False)
    quantity     = Column(Float,       nullable=False)
    amount       = Column(Float,       nullable=False)
    currency     = Column(String(5),   nullable=False)
    timestamp    = Column(DateTime,    default=datetime.utcnow)
    notes        = Column(Text,        nullable=True)

    def __repr__(self):
        return f"<Transaction {self.action} {self.ticker} @ {self.price}>"


# ── DB init + migration ───────────────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(engine)
    _migrate()
    print(f"  DB ready: {DB_PATH}")


def _migrate():
    """Add new columns to existing tables without destroying data."""
    from sqlalchemy import text
    migrations = [
        ("portfolio",    "user_id",   "VARCHAR(100)"),
        ("portfolio",    "username",  "VARCHAR(200)"),
        ("transactions", "user_id",   "VARCHAR(100)"),
        ("transactions", "username",  "VARCHAR(200)"),
        ("picks",        "run_by_user_id", "VARCHAR(100)"),
    ]
    with engine.connect() as conn:
        for table, col, col_type in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                pass   # already exists


# ── Api cost logger (called from crew.py) ────────────────────────────────────

MODEL_PRICING = {
    # (input_per_1M, output_per_1M) in USD
    "claude-haiku-4-5-20251001":  (0.25, 1.25),
    "claude-sonnet-4-6":          (3.00, 15.00),
    "claude-haiku-4-5":           (0.25, 1.25),
    "claude-sonnet-4-5":          (3.00, 15.00),
}

def log_api_usage(
    user_id:       str,
    username:      str,
    model:         str,
    input_tokens:  int,
    output_tokens: int,
    agent:         str  = None,
    run_context:   str  = None,
) -> float:
    """
    Log one API call and return the USD cost.
    Call this after every agent LLM call.
    """
    prices    = MODEL_PRICING.get(model, (3.00, 15.00))
    cost      = (input_tokens / 1_000_000 * prices[0]) + \
                (output_tokens / 1_000_000 * prices[1])
    cost      = round(cost, 6)

    session   = Session()
    try:
        session.add(ApiUsage(
            user_id       = user_id,
            username      = username,
            model         = model,
            agent         = agent,
            run_context   = run_context,
            input_tokens  = input_tokens,
            output_tokens = output_tokens,
            cost_usd      = cost,
        ))
        session.commit()
    except Exception as e:
        print(f"  [ApiUsage] log error: {e}")
    finally:
        session.close()
    return cost


def get_usage_stats(user_id: str = None) -> dict:
    """
    Returns usage stats. If user_id=None, returns all users (admin view).
    """
    session = Session()
    try:
        q = session.query(ApiUsage)
        if user_id:
            q = q.filter(ApiUsage.user_id == user_id)
        rows = q.order_by(ApiUsage.timestamp.desc()).all()

        total_cost    = sum(r.cost_usd      for r in rows)
        total_input   = sum(r.input_tokens  for r in rows)
        total_output  = sum(r.output_tokens for r in rows)
        total_calls   = len(rows)

        # Per-user breakdown (for admin)
        by_user = {}
        for r in rows:
            u = r.username or r.user_id or "unknown"
            if u not in by_user:
                by_user[u] = {"calls":0,"cost":0.0,"tokens":0,"account_type":"—"}
            by_user[u]["calls"] += 1
            by_user[u]["cost"]  += r.cost_usd
            by_user[u]["tokens"]+= r.input_tokens + r.output_tokens

        # Enrich with account_type
        for u_name, stats in by_user.items():
            profile = session.query(UserProfile).filter(UserProfile.name == u_name).first()
            if profile:
                stats["account_type"] = profile.account_type

        return {
            "total_calls":   total_calls,
            "total_cost":    round(total_cost, 4),
            "total_input":   total_input,
            "total_output":  total_output,
            "by_user":       by_user,
            "recent":        [
                {
                    "timestamp":  r.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "username":   r.username or "—",
                    "model":      r.model.split("-")[1] if "-" in r.model else r.model,
                    "agent":      r.agent or "—",
                    "context":    r.run_context or "—",
                    "tokens_in":  r.input_tokens,
                    "tokens_out": r.output_tokens,
                    "cost":       f"${r.cost_usd:.4f}",
                }
                for r in rows[:50]
            ],
        }
    finally:
        session.close()


if __name__ == "__main__":
    print("Initialising DB...")
    init_db()
    print("Done.")