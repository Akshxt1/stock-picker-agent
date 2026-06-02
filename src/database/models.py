# src/database/models.py
#
# This file defines the database structure — think of it as
# designing the spreadsheet columns before filling in any data.
#
# We use SQLite (a file-based database — no server needed)
# and SQLAlchemy (a Python library that talks to the database).
#
# Tables we create:
#   picks       → every stock recommendation the agents make
#   portfolio   → stocks you've added to paper trading
#   transactions → every buy/sell action (the trade history)

from sqlalchemy import (
    create_engine, Column, Integer, Float,
    String, DateTime, Boolean, Text, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

# ─── Database file location ────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "stock_picker.db")
DB_URL  = f"sqlite:///{DB_PATH}"

# ─── Setup ─────────────────────────────────────────────────────────────────
engine  = create_engine(DB_URL, echo=False)
Base    = declarative_base()
Session = sessionmaker(bind=engine)


# ─── Table 1: Picks ─────────────────────────────────────────────────────────
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

    def __repr__(self):
        return f"<Pick {self.ticker} | {self.confidence} | {self.analysis_date}>"


# ─── Table 2: Portfolio ──────────────────────────────────────────────────────
class Portfolio(Base):
    __tablename__ = "portfolio"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    pick_id         = Column(Integer, nullable=True)
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
        status = "OPEN" if self.is_open else "CLOSED"
        return f"<Portfolio {self.ticker} | {status} | Entry: {self.entry_price}>"


# ─── Table 3: Transactions ───────────────────────────────────────────────────
class Transaction(Base):
    __tablename__ = "transactions"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, nullable=True)
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


# ─── Create all tables ───────────────────────────────────────────────────────
def init_db():
    Base.metadata.create_all(engine)
    print(f"  Database ready at: {DB_PATH}")


if __name__ == "__main__":
    print("Initialising database...")
    init_db()
    print("  Tables created: picks, portfolio, transactions")