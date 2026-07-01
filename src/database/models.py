# src/database/models.py

import os
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger(__name__)

# Automatically hunt down the .env file and load it safely on Windows/Mac/Linux
load_dotenv(find_dotenv())

# Email that is always granted admin (configurable; keep one source of truth).
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "akshatgupta428@gmail.com")

# Read database URL from environment, default to local SQLite.
_SQLITE_FALLBACK = "sqlite:///src/database/stock_picker.db"
DB_URL = (os.getenv("DATABASE_URL") or "").strip()
if not DB_URL:
    # DATABASE_URL can be present but blank when a Railway variable reference
    # like ${{Postgres.DATABASE_URL}} fails to resolve (wrong service name).
    # Fall back to SQLite so the app boots instead of crash-looping — but shout
    # about it, because on Railway that SQLite file is ephemeral and wipes.
    if "DATABASE_URL" in os.environ:
        logger.warning(
            "DATABASE_URL is set but empty — your Railway/host variable reference "
            "did not resolve. Falling back to ephemeral SQLite (data will NOT persist)."
        )
    DB_URL = _SQLITE_FALLBACK

# If using Supabase Postgres, ensure the URL uses 'postgresql://' instead of 'postgres://'
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

# pool_pre_ping recycles dead connections (managed Postgres on Railway/Supabase
# closes idle ones, which otherwise surfaces as random "server closed the
# connection" errors after the app has been quiet). Harmless for SQLite.
_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
if DB_URL.startswith("sqlite"):
    # FastAPI serves requests across threads; allow SQLite connections to be
    # shared between them.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DB_URL, **_engine_kwargs)
Session = sessionmaker(bind=engine)
Base = declarative_base()


# ─── Models ───────────────────────────────────────────────────────────────────

class Pick(Base):
    __tablename__ = "picks"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    market = Column(String)         # 'INDIA' or 'US'
    sector = Column(String)
    size = Column(String)           # 'Large', 'Mid', 'Small'
    analysis_date = Column(String)  # 'YYYY-MM-DD'
    
    ticker = Column(String)
    company = Column(String)
    current_price = Column(Float)
    currency = Column(String)       # 'INR' or 'USD'
    
    # Stored as JSON strings (lists of strings)
    why_buy = Column(JSON)
    why_not_buy = Column(JSON)
    
    technical_signal = Column(String)
    sentiment = Column(String)
    confidence = Column(String)

    # Fundamentals carried from the research stage (stored as the agent's
    # display strings, e.g. "21.41%", "3.35", "15.00%")
    roe = Column(String, nullable=True)
    debt_to_equity = Column(String, nullable=True)
    revenue_growth = Column(String, nullable=True)
    pe_ratio = Column(String, nullable=True)

    stop_loss_pct = Column(Float)
    target_pct = Column(Float)

    # Store the exact price when the pick was made for historical tracking
    price_at_pick = Column(Float)
    
    # Track who/what generated this pick
    run_by_user_id = Column(String, nullable=True)
    run_by_username = Column(String, nullable=True)

class Portfolio(Base):
    """Paper trading portfolio positions"""
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user_id = Column(String, nullable=True)     # Link to user account
    username = Column(String, nullable=True)    # Human readable name
    
    ticker = Column(String)
    market = Column(String)
    currency = Column(String)
    
    # Entry details
    quantity = Column(Float)
    entry_price = Column(Float)
    entry_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Position status
    is_open = Column(Boolean, default=True)
    exit_price = Column(Float, nullable=True)
    exit_date = Column(DateTime, nullable=True)

    pick_id = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)

    # Saved output of the lightweight per-holding "Run Analysis"
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    recommendation = Column(String, nullable=True)   # HOLD / BUY / BUY_MORE / SELL
    analysis_summary = Column(String, nullable=True)
    why_buy = Column(JSON, nullable=True)            # list[str] reasoning
    why_not_buy = Column(JSON, nullable=True)        # list[str] risks
    analyzed_at = Column(DateTime, nullable=True)

class Transaction(Base):
    """Log of all buy/sell actions"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    
    ticker = Column(String)
    action = Column(String) # 'BUY' or 'SELL'
    quantity = Column(Float)
    price = Column(Float)
    notes = Column(String, nullable=True)

class ApiUsage(Base):
    """Track LLM token usage and estimated costs per user"""
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    
    model = Column(String)              # e.g., 'claude-3-5-haiku-latest'
    agent = Column(String)              # 'researcher', 'full_crew', etc.
    run_context = Column(String)        # e.g., 'INDIA/Tech/Large'
    
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)

class SystemSettings(Base):
    """Store global system configurations (like the Auto-Scheduler)"""
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(JSON)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class MarketDataCache(Base):
    """Cached provider responses to reduce repeated market-data API calls"""
    __tablename__ = "market_data_cache"

    cache_key = Column(String, primary_key=True)
    source = Column(String)
    payload = Column(JSON)
    expires_at = Column(DateTime)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class UserProfile(Base):
    """Local mirror of user profile data synced from Supabase auth"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)   # Supabase auth UUID
    username = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notification_email = Column(String, nullable=True)      # separate email for alerts
    account_type = Column(String, default="trial")          # 'admin', 'premium', 'trial', 'guest'
    weekly_runs  = Column(Integer, default=0)               # crew (market scan) runs this week
    weekly_portfolio_runs = Column(Integer, default=0)     # deep/portfolio analysis runs this week
    week_start   = Column(String, nullable=True)            # ISO date of current week start
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, nullable=True)
    tutorial_seen = Column(Boolean, default=False)

# ─── Initialization ───────────────────────────────────────────────────────────

def init_db():
    """Create all tables if they don't exist, then run additive column migrations."""
    Base.metadata.create_all(engine)
    _migrate_add_columns()


def _migrate_add_columns():
    """Idempotently add new nullable columns to existing tables.

    create_all() never ALTERs an existing table, so for databases created
    before these columns were introduced we add them by hand. Safe to run
    on every startup — each column is only added if missing.
    """
    from sqlalchemy import inspect, text

    additions = {
        "picks": {
            "roe": "VARCHAR",
            "debt_to_equity": "VARCHAR",
            "revenue_growth": "VARCHAR",
            "pe_ratio": "VARCHAR",
            "run_by_username": "VARCHAR",
        },
        "portfolio": {
            "target_price": "FLOAT",
            "stop_loss": "FLOAT",
            "recommendation": "VARCHAR",
            "analysis_summary": "VARCHAR",
            "why_buy": "JSON",
            "why_not_buy": "JSON",
            "analyzed_at": "DATETIME",
        },
        "user_profiles": {
            "weekly_portfolio_runs": "INTEGER DEFAULT 0",
            "notification_email": "VARCHAR",
            "tutorial_seen": "BOOLEAN DEFAULT FALSE",
        },
    }

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        with engine.begin() as conn:
            for table, cols in additions.items():
                if table not in existing_tables:
                    continue
                have = {c["name"] for c in inspector.get_columns(table)}
                for col, sqltype in cols.items():
                    if col not in have:
                        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {sqltype}'))
    except Exception as e:
        # Migration is best-effort; never block startup on it.
        print(f"  [migrate] skipped: {e}")


# ─── Cost Calculators ─────────────────────────────────────────────────────────

def calculate_anthropic_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost in USD based on Anthropic pricing"""
    pricing = {
        "claude-3-5-sonnet-latest": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-latest": {"input": 0.25, "output": 1.25},
        "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
        "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25}
    }
    
    rates = pricing.get(model, {"input": 0.0, "output": 0.0})
    
    input_cost = (input_tokens / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    
    return input_cost + output_cost

def log_api_usage(user_id: str, username: str, model: str, input_tokens: int, output_tokens: int, agent: str, run_context: str):
    """Helper to quickly log usage and calculate costs"""
    cost = calculate_anthropic_cost(model, input_tokens, output_tokens)
    
    with Session() as sess:
        usage = ApiUsage(
            user_id=user_id,
            username=username,
            model=model,
            agent=agent,
            run_context=run_context,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost
        )
        sess.add(usage)
        sess.commit()

# ─── Route helpers (used by FastAPI routes) ──────────────────────────────────

def get_user_picks(user_id: str, market: str = None) -> list:
    with Session() as sess:
        query = sess.query(Pick).filter(Pick.run_by_user_id == user_id)
        if market:
            query = query.filter(Pick.market == market)
        rows = query.order_by(Pick.created_at.desc()).all()
        return [_pick_to_dict(r) for r in rows]


def _pick_to_dict(r) -> dict:
    """Normalized pick shape consumed by the frontend (clickable, fully detailed)."""
    return {
        "id":             r.id,
        "ticker":         r.ticker,
        "company_name":   r.company,
        "market":         r.market,
        "sector":         r.sector,
        "size":           r.size,
        "current_price":  r.current_price,
        "currency":       r.currency,
        "recommendation": r.technical_signal,
        "technical_signal": r.technical_signal,
        "sentiment":      r.sentiment,
        "confidence":     r.confidence,
        "roe":            r.roe,
        "debt_to_equity": r.debt_to_equity,
        "revenue_growth": r.revenue_growth,
        "pe_ratio":       r.pe_ratio,
        "why_buy":        r.why_buy or [],
        "why_not_buy":    r.why_not_buy or [],
        "stop_loss_pct":  r.stop_loss_pct,
        "target_pct":     r.target_pct,
        "analysis_date":  r.analysis_date,
        "run_by_username": getattr(r, "run_by_username", None),
        "reasoning":      str(r.why_buy) if r.why_buy else "",
    }

def delete_pick(pick_id: int, user_id: str):
    with Session() as sess:
        row = sess.query(Pick).filter(Pick.id == pick_id, Pick.run_by_user_id == user_id).first()
        if row:
            sess.delete(row)
            sess.commit()

def get_portfolio(user_id: str, market: str = None) -> list:
    with Session() as sess:
        query = sess.query(Portfolio).filter(
            Portfolio.user_id == user_id, Portfolio.is_open == True
        )
        if market:
            query = query.filter(Portfolio.market == market)
        rows = query.order_by(Portfolio.created_at.desc()).all()
        return [
            {
                "id":               r.id,
                "ticker":           r.ticker,
                "market":           r.market,
                "currency":         r.currency,
                "quantity":         r.quantity,
                "buy_price":        r.entry_price,
                "current_price":    None,   # filled in by the route (live)
                "pnl_pct":          None,
                "pe_ratio":         None,
                # saved "Run Analysis" output
                "target_price":     r.target_price,
                "stop_loss":        r.stop_loss,
                "recommendation":   r.recommendation,
                "analysis_summary": r.analysis_summary,
                "why_buy":          r.why_buy or [],
                "why_not_buy":      r.why_not_buy or [],
                "analyzed_at":      r.analyzed_at.isoformat() if r.analyzed_at else None,
            }
            for r in rows
        ]


def save_holding_analysis(holding_id: int, user_id: str, recommendation: str,
                          target_price: float = None, stop_loss: float = None,
                          summary: str = None, why_buy: list = None,
                          why_not_buy: list = None) -> bool:
    """Persist the lightweight per-holding analysis result onto the position."""
    with Session() as sess:
        row = sess.query(Portfolio).filter(
            Portfolio.id == holding_id, Portfolio.user_id == user_id
        ).first()
        if not row:
            return False
        row.recommendation   = recommendation
        row.target_price     = target_price
        row.stop_loss        = stop_loss
        row.analysis_summary = summary
        row.why_buy          = why_buy or []
        row.why_not_buy      = why_not_buy or []
        row.analyzed_at      = datetime.now(timezone.utc)
        sess.commit()
        return True

def add_portfolio_position(user_id: str, ticker: str, quantity: float, buy_price: float,
                           username: str = None):
    t = ticker.upper()
    if t.endswith(".NS") or t.endswith(".BO"):
        market, currency = "INDIA", "INR"
    else:
        market, currency = "US", "USD"
    with Session() as sess:
        pos = Portfolio(
            user_id=user_id,
            username=username,
            ticker=t,
            quantity=quantity,
            entry_price=buy_price,
            market=market,
            currency=currency,
        )
        sess.add(pos)
        sess.commit()

def remove_portfolio_position(holding_id: int, user_id: str):
    with Session() as sess:
        row = sess.query(Portfolio).filter(
            Portfolio.id == holding_id, Portfolio.user_id == user_id
        ).first()
        if row:
            row.is_open = False
            sess.commit()


ACCOUNT_LIMITS = {
    "admin":   {"crew_runs": 9999, "portfolio_runs": 9999},
    "premium": {"crew_runs": 5,    "portfolio_runs": 5},
    "trial":   {"crew_runs": 2,    "portfolio_runs": 3},
    "guest":   {"crew_runs": 0,    "portfolio_runs": 0},
}


def upsert_user_profile(user_id: str, email: str = None, username: str = None) -> dict:
    """Create or update a user profile. Returns the profile as dict."""
    from datetime import date
    week_start = date.today().strftime("%Y-W%W")  # e.g. "2026-W25"
    with Session() as sess:
        profile = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            # New user — default to 'trial' unless it's the admin email
            acct = "admin" if email == ADMIN_EMAIL else "trial"
            profile = UserProfile(
                user_id=user_id, email=email, username=username,
                account_type=acct, weekly_runs=0, week_start=week_start,
                last_seen=datetime.now(timezone.utc),
            )
            sess.add(profile)
        else:
            # Reset weekly counters if new week
            if profile.week_start != week_start:
                profile.weekly_runs = 0
                profile.weekly_portfolio_runs = 0
                profile.week_start  = week_start
            if email:    profile.email    = email
            # Only set username from Supabase metadata if not already set locally
            if username and not profile.username: profile.username = username
            profile.last_seen = datetime.now(timezone.utc)
            # Always enforce admin for the admin email, even if DB had old value
            if email == ADMIN_EMAIL:
                profile.account_type = "admin"
            # Migrate old account types to new names
            elif profile.account_type in ("free", None, ""):
                profile.account_type = "trial"
            elif profile.account_type == "pro":
                profile.account_type = "premium"
        sess.commit()
        sess.refresh(profile)
        return {
            "user_id":           profile.user_id,
            "email":             profile.email,
            "username":          profile.username,
            "notification_email": profile.notification_email,
            "account_type":      profile.account_type,
            "weekly_runs":       profile.weekly_runs,
            "weekly_portfolio_runs": profile.weekly_portfolio_runs or 0,
            "tutorial_seen":     bool(profile.tutorial_seen),
            "limits":            ACCOUNT_LIMITS.get(profile.account_type, ACCOUNT_LIMITS["trial"]),
        }


def update_username(user_id: str, username: str) -> dict:
    """Update a user's display name in the local DB."""
    with Session() as sess:
        profile = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise ValueError(f"User {user_id} not found")
        profile.username = username
        sess.commit()
        sess.refresh(profile)
        return {"user_id": profile.user_id, "username": profile.username, "email": profile.email}


def update_notification_email(user_id: str, notification_email: str) -> dict:
    """Update a user's separate notification email."""
    with Session() as sess:
        profile = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise ValueError(f"User {user_id} not found")
        profile.notification_email = notification_email or None
        sess.commit()
        sess.refresh(profile)
        return {"user_id": profile.user_id, "notification_email": profile.notification_email}


def update_tutorial_seen(user_id: str, seen: bool) -> None:
    """Mark that the user has completed the onboarding tutorial."""
    with Session() as sess:
        profile = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if profile:
            profile.tutorial_seen = seen
            sess.commit()


def clear_user_picks(user_id: str) -> int:
    """Delete all picks for a user. Returns the number of rows deleted."""
    with Session() as sess:
        rows = sess.query(Pick).filter(Pick.run_by_user_id == user_id).all()
        count = len(rows)
        for row in rows:
            sess.delete(row)
        sess.commit()
        return count


def increment_run_count(user_id: str) -> bool:
    """Increment weekly crew (market-scan) run count. True if allowed, False if at limit."""
    from datetime import date
    week_start = date.today().strftime("%Y-W%W")
    with Session() as sess:
        profile = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return True  # unknown user, allow
        if profile.week_start != week_start:
            profile.weekly_runs = 0
            profile.weekly_portfolio_runs = 0
            profile.week_start  = week_start
        limits = ACCOUNT_LIMITS.get(profile.account_type, ACCOUNT_LIMITS["trial"])
        if profile.weekly_runs >= limits["crew_runs"]:
            return False
        profile.weekly_runs += 1
        sess.commit()
        return True


def increment_portfolio_run_count(user_id: str) -> bool:
    """Increment weekly deep/portfolio analysis count. True if allowed, False if at limit.

    Used by single-stock Deep Analysis and portfolio-level analysis — both draw
    from the account's `portfolio_runs` weekly quota.
    """
    from datetime import date
    week_start = date.today().strftime("%Y-W%W")
    with Session() as sess:
        profile = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return True
        if profile.week_start != week_start:
            profile.weekly_runs = 0
            profile.weekly_portfolio_runs = 0
            profile.week_start  = week_start
        limits = ACCOUNT_LIMITS.get(profile.account_type, ACCOUNT_LIMITS["trial"])
        if (profile.weekly_portfolio_runs or 0) >= limits["portfolio_runs"]:
            return False
        profile.weekly_portfolio_runs = (profile.weekly_portfolio_runs or 0) + 1
        sess.commit()
        return True


def decrement_run_count(user_id: str) -> None:
    """Refund one weekly crew run (e.g. the run errored before producing anything)."""
    with Session() as sess:
        profile = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if profile and (profile.weekly_runs or 0) > 0:
            profile.weekly_runs -= 1
            sess.commit()


def decrement_portfolio_run_count(user_id: str) -> None:
    """Refund one weekly deep/portfolio analysis run."""
    with Session() as sess:
        profile = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if profile and (profile.weekly_portfolio_runs or 0) > 0:
            profile.weekly_portfolio_runs -= 1
            sess.commit()


def get_all_user_profiles() -> list:
    with Session() as sess:
        rows = sess.query(UserProfile).order_by(UserProfile.last_seen.desc()).all()
        return [
            {
                "user_id":      r.user_id,
                "email":        r.email,
                "username":     r.username,
                "account_type": r.account_type,
                "weekly_runs":  r.weekly_runs,
                "last_seen":    r.last_seen.isoformat() if r.last_seen else None,
                "created_at":   r.created_at.isoformat() if r.created_at else None,
                "limits":       ACCOUNT_LIMITS.get(r.account_type, ACCOUNT_LIMITS["trial"]),
            }
            for r in rows
        ]


def update_account_type(user_id: str, account_type: str) -> bool:
    if account_type not in ACCOUNT_LIMITS:
        return False
    with Session() as sess:
        profile = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return False
        profile.account_type = account_type
        sess.commit()
    return True


def get_usage_stats(user_id: str = None) -> dict:
    """Get aggregated usage stats for a user (or global if user_id is None)"""
    with Session() as sess:
        query = sess.query(ApiUsage)
        if user_id:
            query = query.filter(ApiUsage.user_id == user_id)
            
        logs = query.all()
        
        return {
            "total_calls": len(logs),
            "total_input": sum(log.input_tokens for log in logs),
            "total_output": sum(log.output_tokens for log in logs),
            "total_cost": sum(log.estimated_cost for log in logs)
        }
