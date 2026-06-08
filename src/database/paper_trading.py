# src/database/paper_trading.py  — FINAL VERSION
# Fully user-aware. Each user has their own isolated portfolio.

import yfinance as yf
from datetime import datetime
from sqlalchemy import or_
from src.database.models import engine, Session, init_db, Pick, Portfolio, Transaction


def save_picks(crew_output: dict, run_by_user_id: str = None) -> list:
    session  = Session()
    saved    = []
    market   = crew_output.get("market", "")
    sector   = crew_output.get("sector", "")
    size     = crew_output.get("size", "")
    date_str = crew_output.get("analysis_date", datetime.today().strftime("%Y-%m-%d"))

    for p in crew_output.get("picks", []):
        pick = Pick(
            ticker           = p.get("ticker", ""),
            company          = p.get("company", ""),
            market           = market, sector=sector, size=size,
            currency         = p.get("currency", "USD"),
            price_at_pick    = p.get("current_price", 0.0),
            why_buy          = p.get("why_buy", []),
            why_not_buy      = p.get("why_not_buy", []),
            technical_signal = p.get("technical_signal", ""),
            sentiment        = p.get("sentiment", ""),
            confidence       = p.get("confidence", ""),
            analysis_date    = date_str,
            run_by_user_id   = run_by_user_id,
        )
        session.add(pick)
        saved.append(pick)

    session.commit()
    for pick in saved:
        session.refresh(pick)
    session.close()
    print(f"  Saved {len(saved)} picks.")
    return saved


def add_to_portfolio(
    ticker:       str,
    quantity:     float,
    user_id:      str   = None,
    username:     str   = None,
    pick_id:      int   = None,
    notes:        str   = None,
    custom_price: float = None,
    custom_date:  str   = None,
) -> Portfolio:
    """
    Add a stock to a specific user's paper portfolio.
    user_id  — Supabase UUID of the user
    username — display name for readable logs
    """
    session = Session()
    stock   = yf.Ticker(ticker)
    info    = stock.info

    # Entry price
    if custom_price and custom_price > 0:
        entry_price = round(custom_price, 2)
    else:
        hist = stock.history(period="1d")
        if hist.empty:
            session.close()
            raise ValueError(f"Could not fetch live price for {ticker}. Check the ticker symbol.")
        entry_price = round(float(hist["Close"].iloc[-1]), 2)

    # Entry date
    try:
        entry_dt = datetime.strptime(custom_date, "%Y-%m-%d") if custom_date else datetime.utcnow()
    except (ValueError, TypeError):
        entry_dt = datetime.utcnow()

    invested_amount = round(entry_price * quantity, 2)
    currency        = info.get("currency", "USD")
    company         = info.get("longName", ticker)
    sector          = info.get("sector", "Unknown")
    market          = "INDIA" if (ticker.endswith(".NS") or ticker.endswith(".BO")) else "US"

    position = Portfolio(
        user_id         = user_id,
        username        = username,
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
        entry_date      = entry_dt,
    )
    session.add(position)
    session.flush()

    session.add(Transaction(
        user_id      = user_id,
        username     = username,
        portfolio_id = position.id,
        ticker       = ticker,
        action       = "BUY",
        price        = entry_price,
        quantity     = quantity,
        amount       = invested_amount,
        currency     = currency,
        timestamp    = entry_dt,
        notes        = notes or ("Custom price" if custom_price else "Live price"),
    ))

    # Mark pick as in_portfolio ONLY for this user
    # (we don't set the global flag anymore — each user tracks separately)
    session.commit()
    session.refresh(position)
    print(f"  ✓ {username or 'anon'} bought {ticker} × {quantity} @ {currency} {entry_price:,.2f}")
    session.close()
    return position


def sell_position(portfolio_id: int, notes: str = None,
                  custom_price: float = None) -> dict:
    session  = Session()
    position = session.get(Portfolio, portfolio_id)

    if not position:
        session.close()
        raise ValueError(f"Position {portfolio_id} not found")
    if not position.is_open:
        session.close()
        raise ValueError(f"{position.ticker} is already closed")

    if custom_price and custom_price > 0:
        exit_price = round(custom_price, 2)
    else:
        hist       = yf.Ticker(position.ticker).history(period="1d")
        exit_price = round(float(hist["Close"].iloc[-1]), 2) if not hist.empty else position.entry_price

    pnl_amount = round((exit_price - position.entry_price) * position.quantity, 2)
    pnl_pct    = round(((exit_price - position.entry_price) / position.entry_price) * 100, 2)

    position.is_open    = False
    position.exit_price = exit_price
    position.exit_date  = datetime.utcnow()

    session.add(Transaction(
        user_id      = position.user_id,
        username     = position.username,
        portfolio_id = portfolio_id,
        ticker       = position.ticker,
        action       = "SELL",
        price        = exit_price,
        quantity     = position.quantity,
        amount       = round(exit_price * position.quantity, 2),
        currency     = position.currency,
        notes        = notes or ("Custom price" if custom_price else "Live price"),
    ))
    session.commit()

    result = {
        "ticker": position.ticker, "entry_price": position.entry_price,
        "exit_price": exit_price,  "quantity": position.quantity,
        "pnl_amount": pnl_amount,  "pnl_pct": pnl_pct,
        "currency": position.currency,
    }
    em = "🟢" if pnl_amount >= 0 else "🔴"
    print(f"  {em} {position.ticker} sold @ {exit_price:,.2f} | P&L: {pnl_pct:+.2f}%")
    session.close()
    return result


def get_portfolio(market: str = None, username: str = None) -> list[dict]:
    """
    Returns open positions for a specific user.
    username here is actually the user_id (Supabase UUID).
    Falls back to showing unassigned positions too (backward compat).
    """
    session   = Session()
    query     = session.query(Portfolio).filter(Portfolio.is_open == True)

    if market:
        query = query.filter(Portfolio.market == market.upper())

    if username:
        # Match by user_id OR by username display name OR unassigned (legacy)
        query = query.filter(
            or_(
                Portfolio.user_id == username,
                Portfolio.username == username,
                Portfolio.user_id == None,
            )
        )

    positions = query.all()
    results   = []

    for pos in positions:
        try:
            hist          = yf.Ticker(pos.ticker).history(period="1d")
            current_price = round(float(hist["Close"].iloc[-1]), 2) if not hist.empty else pos.entry_price
        except Exception:
            current_price = pos.entry_price

        current_value = round(current_price * pos.quantity, 2)
        pnl_amount    = round(current_value - pos.invested_amount, 2)
        pnl_pct       = round((pnl_amount / pos.invested_amount) * 100, 2) if pos.invested_amount else 0
        days_held     = (datetime.utcnow() - pos.entry_date).days

        results.append({
            "id":            pos.id,
            "ticker":        pos.ticker,
            "company":       pos.company,
            "market":        pos.market,
            "sector":        pos.sector,
            "currency":      pos.currency,
            "user_id":       pos.user_id,
            "username":      pos.username,
            "entry_price":   pos.entry_price,
            "current_price": current_price,
            "quantity":      pos.quantity,
            "invested":      pos.invested_amount,
            "current_value": current_value,
            "pnl_amount":    pnl_amount,
            "pnl_pct":       pnl_pct,
            "days_held":     days_held,
            "entry_date":    pos.entry_date.strftime("%Y-%m-%d"),
        })

    session.close()
    return results


def get_portfolio_metrics(username: str = None) -> dict:
    session = Session()
    oq = session.query(Portfolio).filter(Portfolio.is_open == True)
    cq = session.query(Portfolio).filter(Portfolio.is_open == False)

    if username:
        oq = oq.filter(or_(Portfolio.user_id==username,
                            Portfolio.username==username,
                            Portfolio.user_id==None))
        cq = cq.filter(or_(Portfolio.user_id==username,
                            Portfolio.username==username,
                            Portfolio.user_id==None))

    open_pos   = oq.all()
    closed_pos = cq.all()

    total_inv = total_cur = 0
    for pos in open_pos:
        try:
            hist = yf.Ticker(pos.ticker).history(period="1d")
            cp   = float(hist["Close"].iloc[-1]) if not hist.empty else pos.entry_price
        except Exception:
            cp = pos.entry_price
        total_inv += pos.invested_amount
        total_cur += cp * pos.quantity

    wins = losses = 0
    best = worst  = None
    bp = float("-inf"); wp = float("inf")

    for pos in closed_pos:
        if pos.entry_price and pos.exit_price:
            pct = ((pos.exit_price - pos.entry_price) / pos.entry_price) * 100
            if pct > 0: wins   += 1
            else:       losses += 1
            if pct > bp: bp = pct; best  = pos.ticker
            if pct < wp: wp = pct; worst = pos.ticker

    total_closed   = wins + losses
    unrealised_pnl = round(total_cur - total_inv, 2)

    session.close()
    return {
        "open_positions":     len(open_pos),
        "closed_positions":   total_closed,
        "total_invested":     round(total_inv, 2),
        "current_value":      round(total_cur, 2),
        "unrealised_pnl":     unrealised_pnl,
        "unrealised_pnl_pct": round(unrealised_pnl / total_inv * 100, 2) if total_inv else 0,
        "win_rate":           round(wins / total_closed * 100, 1) if total_closed else None,
        "wins": wins, "losses": losses,
        "best_pick":      best,
        "best_pick_pct":  round(bp, 2) if best  else None,
        "worst_pick":     worst,
        "worst_pick_pct": round(wp, 2) if worst else None,
    }