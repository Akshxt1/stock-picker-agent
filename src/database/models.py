# src/database/models.py

import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# Read database URL from environment variable, default to local SQLite
DB_URL = os.getenv("DATABASE_URL", "sqlite:///src/database/stock_picker.db")

# If using Supabase Postgres, ensure the URL uses 'postgresql://' instead of 'postgres://'
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DB_URL, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Pick(Base):
    __tablename__ = "picks"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    market = Column(String)
    sector = Column(String)
    size = Column(String)
    analysis_date = Column(String)
    
    ticker = Column(String)
    company = Column(String)
    current_price = Column(Float)
    currency = Column(String)
    
    why_buy = Column(JSON)
    why_not_buy = Column(JSON)
    
    technical_signal = Column(String)
    sentiment = Column(String)
    confidence = Column(String)
    
    stop_loss_pct = Column(Float)
    target_pct = Column(Float)
    
    price_at_pick = Column(Float)
    run_by_user_id = Column(String, nullable=True)

class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    
    ticker = Column(String)
    market = Column(String)
    currency = Column(String)
    
    quantity = Column(Float)
    entry_price = Column(Float)
    entry_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    is_open = Column(Boolean, default=True)
    exit_price = Column(Float, nullable=True)
    exit_date = Column(DateTime, nullable=True)
    
    pick_id = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)

class ApiUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    
    model = Column(String)
    agent = Column(String)
    run_context = Column(String)
    
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)

# PRODUCTION FIX: Database Table for Scheduler Settings
class SystemSettings(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(JSON)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(engine)

def calculate_anthropic_cost(model: str, input_tokens: int, output_tokens: int) -> float:
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