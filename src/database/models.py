# src/database/models.py

import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv, find_dotenv

# Automatically hunt down the .env file and load it safely on Windows/Mac/Linux
load_dotenv(find_dotenv())

# Read database URL from environment variable, default to local SQLite
DB_URL = os.getenv("DATABASE_URL", "sqlite:///src/database/stock_picker.db")

# If using Supabase Postgres, ensure the URL uses 'postgresql://' instead of 'postgres://'
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DB_URL, echo=False)
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
    
    stop_loss_pct = Column(Float)
    target_pct = Column(Float)
    
    # Store the exact price when the pick was made for historical tracking
    price_at_pick = Column(Float)
    
    # Track who/what generated this pick
    run_by_user_id = Column(String, nullable=True)

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

class UserProfile(Base):
    """Local mirror of user profile data synced from Supabase auth"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)   # Supabase auth UUID
    username = Column(String, nullable=True)
    email = Column(String, nullable=True)
    account_type = Column(String, default="free")           # 'free', 'pro', 'admin'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, nullable=True)

# ─── Initialization ───────────────────────────────────────────────────────────

def init_db():
    """Create all tables if they don't exist"""
    Base.metadata.create_all(engine)


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