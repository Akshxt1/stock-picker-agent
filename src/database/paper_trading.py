# src/database/paper_trading.py
#
# This is the paper trading engine — all the operations for
# storing picks, managing the simulated portfolio, and
# calculating real-time P&L metrics.
#
# Functions in this file:
#   save_picks()          → store agent picks in the database
#   add_to_portfolio()    → "buy" a stock at current price
#   sell_position()       → "sell" and record the return
#   get_portfolio()       → get all holdings with live P&L
#   get_portfolio_metrics() → win rate, best pick, total return, Sharpe

import yfinance as yf
from datetime import datetime
from sqlalchemy.orm import Session as SessionType

from src.database.models import (
    engine, Session, init_db,
    Pick, Portfolio, Transaction
)


# ─── 1. Save picks from crew output ─────────────────────────────────────────

def save_picks(crew_output: dict) -> list[Pick]:
    """
    Takes the JSON output from the Master Analyst and saves
    all picks to the picks table.

    Args:
        crew_output: the dict returned by run_stock_picker()

    Returns:
        list of Pick objects that were saved
    """
    session    = Session()
    saved      = []
    market     = crew_output.get("market", "")
    sector     = crew_output.get("sector", "")
    size       = crew_output.get("size", "")
    date_str   = crew_output.get("analysis_date", datetime.today().strftime("%Y-%m-%d"))

    for p in crew_output.get("picks", []):
        pick = Pick(
            ticker           = p.get("ticker", ""),
            company          = p.get("company", ""),
            market           = market,
            sector           = sector,
            size             = size,
            currency         = p.get("currency", "USD"),
            price_at_pick    = p.get("current_price", 0.0),
            why_buy          = p.get("why_buy", []),
            why_not_buy      = p.get("why_not_buy", []),
            technical_signal = p.get("technical_signal", ""),
            sentiment        = p.get("sentiment", ""),
            confidence       = p.get("confidence", ""),
            analysis_date    = date_str,
        )
        session.add(pick)
        saved.append(pick)

    session.commit()

    for pick in saved:
        session.refresh(pick)

    print(f"  Saved {len(saved)} picks to database.")
    session.close()
    return saved


# ─── 2. Add a pick to the paper portfolio ───────────────────────────────────

def add_to_portfolio(
    ticker:   str,
    quantity: float,
    pick_id:  int   = None,
    notes:    str   = None
) -> Portfolio:
    """
    "Buys" a stock at its current live price and adds it
    to the paper trading portfolio.

    Args:
        ticker   : stock ticker e.g. "WIPRO.NS" or "AAPL"
        quantity : number of shares to simulate buying
        pick_id  : optional — link to a Pick row in the DB
        notes    : optional note about why you're adding it

    Returns:
        Portfolio object with entry details
    """
    session = Session()

    # Get current live price from yfinance
    stock   = yf.Ticker(ticker)
    hist    = stock.history(period="1d")
    if hist.empty:
        session.close()
        raise ValueError(f"Could not fetch price for {ticker}")

    entry_price     = round(hist["Close"].iloc[-1], 2)
    invested_amount = round(entry_price * quantity, 2)
    info            = stock.info
    currency        = info.get("currency", "USD")
    company         = info.get("longName", ticker)
    sector          = info.get("sector", "Unknown")
    market          = "INDIA" if ticker.endswith(".NS") or ticker.endswith(".BO") else "US"

    # Create portfolio entry
    position = Portfolio(
        pick_id         = pick_id,
        ticker          = ticker,
        company         = company,
        market          = market,
        sector          = sector,
        currency        = currency,
        entry_price     = entry_price,
        quantity        = quantity,
        invested_amount = invested_amount,
        is_open         = True,
    )
    session.add(position)
    session.flush()   # get the ID before committing

    # Log the transaction
    txn = Transaction(
        portfolio_id = position.id,
        ticker       = ticker,
        action       = "BUY",
        price        = entry_price,
        quantity     = quantity,
        amount       = invested_amount,
        currency     = currency,
        notes        = notes,
    )
    session.add(txn)

    # Mark pick as in_portfolio if linked
    if pick_id:
        pick = session.get(Pick, pick_id)
        if pick:
            pick.in_portfolio = True

    session.commit()
    session.refresh(position)

    print(f"  ✓ Added {ticker} — {quantity} shares @ {currency} {entry_price:,.2f}")
    print(f"    Total invested: {currency} {invested_amount:,.2f}")

    session.close()
    return position


# ─── 3. Sell a position ──────────────────────────────────────────────────────

def sell_position(portfolio_id: int, notes: str = None) -> dict:
    """
    Closes an open position at the current live price.

    Args:
        portfolio_id : the ID from the portfolio table
        notes        : optional reason for selling

    Returns:
        dict with exit price, P&L amount, and P&L %
    """
    session  = Session()
    position = session.get(Portfolio, portfolio_id)

    if not position:
        session.close()
        raise ValueError(f"Portfolio position {portfolio_id} not found")
    if not position.is_open:
        session.close()
        raise ValueError(f"{position.ticker} is already closed")

    # Get current price
    hist       = yf.Ticker(position.ticker).history(period="1d")
    exit_price = round(hist["Close"].iloc[-1], 2)

    # Calculate P&L
    pnl_amount = round((exit_price - position.entry_price) * position.quantity, 2)
    pnl_pct    = round(((exit_price - position.entry_price) / position.entry_price) * 100, 2)

    # Update position
    position.is_open    = False
    position.exit_price = exit_price
    position.exit_date  = datetime.utcnow()

    # Log sell transaction
    txn = Transaction(
        portfolio_id = portfolio_id,
        ticker       = position.ticker,
        action       = "SELL",
        price        = exit_price,
        quantity     = position.quantity,
        amount       = round(exit_price * position.quantity, 2),
        currency     = position.currency,
        notes        = notes,
    )
    session.add(txn)
    session.commit()

    result = {
        "ticker":      position.ticker,
        "entry_price": position.entry_price,
        "exit_price":  exit_price,
        "quantity":    position.quantity,
        "pnl_amount":  pnl_amount,
        "pnl_pct":     pnl_pct,
        "currency":    position.currency,
    }

    emoji = "🟢" if pnl_amount >= 0 else "🔴"
    print(f"  {emoji} Sold {position.ticker} @ {position.currency} {exit_price:,.2f}")
    print(f"     P&L: {position.currency} {pnl_amount:+,.2f}  ({pnl_pct:+.2f}%)")

    session.close()
    return result


# ─── 4. Get portfolio with live P&L ─────────────────────────────────────────

def get_portfolio(market: str = None) -> list[dict]:
    """
    Returns all open positions with their current live P&L.

    Args:
        market: "INDIA", "US", or None for all

    Returns:
        list of dicts, one per position
    """
    session   = Session()
    query     = session.query(Portfolio).filter(Portfolio.is_open == True)
    if market:
        query = query.filter(Portfolio.market == market.upper())
    positions = query.all()

    results = []
    for pos in positions:
        try:
            hist          = yf.Ticker(pos.ticker).history(period="1d")
            current_price = round(hist["Close"].iloc[-1], 2) if not hist.empty else pos.entry_price
        except:
            current_price = pos.entry_price

        current_value  = round(current_price * pos.quantity, 2)
        pnl_amount     = round(current_value - pos.invested_amount, 2)
        pnl_pct        = round((pnl_amount / pos.invested_amount) * 100, 2)
        days_held      = (datetime.utcnow() - pos.entry_date).days

        results.append({
            "id":              pos.id,
            "ticker":          pos.ticker,
            "company":         pos.company,
            "market":          pos.market,
            "sector":          pos.sector,
            "currency":        pos.currency,
            "entry_price":     pos.entry_price,
            "current_price":   current_price,
            "quantity":        pos.quantity,
            "invested":        pos.invested_amount,
            "current_value":   current_value,
            "pnl_amount":      pnl_amount,
            "pnl_pct":         pnl_pct,
            "days_held":       days_held,
            "entry_date":      pos.entry_date.strftime("%Y-%m-%d"),
        })

    session.close()
    return results


# ─── 5. Portfolio metrics dashboard ─────────────────────────────────────────

def get_portfolio_metrics() -> dict:
    """
    Calculates overall portfolio performance metrics.

    Returns:
        dict with total invested, current value, P&L,
        win rate, best pick, worst pick
    """
    session      = Session()
    open_pos     = session.query(Portfolio).filter(Portfolio.is_open == True).all()
    closed_pos   = session.query(Portfolio).filter(Portfolio.is_open == False).all()

    # ── Open positions metrics ─────────────────────────────────────────────
    total_invested     = 0
    total_current      = 0

    for pos in open_pos:
        try:
            hist          = yf.Ticker(pos.ticker).history(period="1d")
            current_price = hist["Close"].iloc[-1] if not hist.empty else pos.entry_price
        except:
            current_price = pos.entry_price

        total_invested += pos.invested_amount
        total_current  += current_price * pos.quantity

    unrealised_pnl     = round(total_current - total_invested, 2)
    unrealised_pnl_pct = round((unrealised_pnl / total_invested * 100), 2) if total_invested > 0 else 0

    # ── Closed positions metrics ───────────────────────────────────────────
    wins   = 0
    losses = 0
    best   = None
    worst  = None
    best_pct  = float("-inf")
    worst_pct = float("inf")

    for pos in closed_pos:
        pnl_pct = ((pos.exit_price - pos.entry_price) / pos.entry_price) * 100
        if pnl_pct > 0:
            wins += 1
        else:
            losses += 1
        if pnl_pct > best_pct:
            best_pct = pnl_pct
            best     = pos.ticker
        if pnl_pct < worst_pct:
            worst_pct = pnl_pct
            worst     = pos.ticker

    total_closed = wins + losses
    win_rate     = round((wins / total_closed) * 100, 1) if total_closed > 0 else None

    session.close()

    return {
        "open_positions":      len(open_pos),
        "closed_positions":    total_closed,
        "total_invested":      round(total_invested, 2),
        "current_value":       round(total_current, 2),
        "unrealised_pnl":      unrealised_pnl,
        "unrealised_pnl_pct":  unrealised_pnl_pct,
        "win_rate":            win_rate,
        "wins":                wins,
        "losses":              losses,
        "best_pick":           best,
        "best_pick_pct":       round(best_pct, 2) if best else None,
        "worst_pick":          worst,
        "worst_pick_pct":      round(worst_pct, 2) if worst else None,
    }


# ─── Quick test ──────────────────────────────────────────────────────────────
# Run with: uv run src/database/paper_trading.py

if __name__ == "__main__":
    print("Setting up database...")
    init_db()

    print("\nAdding a test position: WIPRO.NS (10 shares)...")
    pos = add_to_portfolio("WIPRO.NS", quantity=10, notes="Test buy")

    print("\nFetching live portfolio...")
    holdings = get_portfolio()
    for h in holdings:
        emoji = "🟢" if h["pnl_pct"] >= 0 else "🔴"
        print(f"  {emoji} {h['ticker']:15} | Entry: {h['entry_price']:>10,.2f} "
              f"| Current: {h['current_price']:>10,.2f} "
              f"| P&L: {h['pnl_pct']:>+6.2f}%")

    print("\nPortfolio metrics:")
    metrics = get_portfolio_metrics()
    for k, v in metrics.items():
        print(f"  {k:25} : {v}")