# src/database/paper_trading.py  — v4
# Fixes: strict user filtering, rate-limit retry, AI analysis saved to portfolio

import time
import yfinance as yf
from datetime import datetime
from sqlalchemy import or_
from src.database.models import Session, init_db, Pick, Portfolio, Transaction


# ── Retry wrapper for yfinance rate limits ────────────────────────────────────
def _fetch_price(ticker: str, retries: int = 4, delay: float = 3.0) -> float:
    """
    Fetches the latest close price with retry on rate-limit errors.
    Raises ValueError if price cannot be fetched after all retries.
    """
    for attempt in range(retries):
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if not hist.empty:
                return round(float(hist["Close"].iloc[-1]), 2)
        except Exception as e:
            msg = str(e).lower()
            if "rate" in msg or "429" in msg or "too many" in msg:
                if attempt < retries - 1:
                    wait = delay * (attempt + 1)
                    print(f"  [yfinance] Rate limited for {ticker}. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
            raise
    raise ValueError(f"Could not fetch price for {ticker} after {retries} attempts.")


def _fetch_info(ticker: str) -> dict:
    """Fetch ticker info with retry."""
    for attempt in range(3):
        try:
            return yf.Ticker(ticker).info or {}
        except Exception as e:
            if "rate" in str(e).lower() and attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                return {}
    return {}


# ── Save picks ────────────────────────────────────────────────────────────────
def save_picks(crew_output: dict, run_by_user_id: str = None) -> list:
    session  = Session()
    saved    = []
    market   = crew_output.get("market", "")
    sector   = crew_output.get("sector", "")
    size     = crew_output.get("size", "")
    # Always use today's date — never trust the LLM's date output
    date_str = datetime.today().strftime("%Y-%m-%d")

    for p in crew_output.get("picks", []):
        pick = Pick(
            ticker=p.get("ticker",""), company=p.get("company",""),
            market=market, sector=sector, size=size,
            currency=p.get("currency","USD"),
            price_at_pick=p.get("current_price",0.0),
            why_buy=p.get("why_buy",[]), why_not_buy=p.get("why_not_buy",[]),
            technical_signal=p.get("technical_signal",""),
            sentiment=p.get("sentiment",""), confidence=p.get("confidence",""),
            analysis_date=date_str, run_by_user_id=run_by_user_id,
        )
        session.add(pick); saved.append(pick)

    session.commit()
    for pick in saved: session.refresh(pick)
    session.close()
    print(f"  Saved {len(saved)} picks.")
    return saved


# ── Add to portfolio ──────────────────────────────────────────────────────────
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
    session = Session()
    info    = _fetch_info(ticker)

    entry_price = round(custom_price, 2) if (custom_price and custom_price > 0) \
                  else _fetch_price(ticker)

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
        user_id=user_id, username=username, pick_id=pick_id,
        ticker=ticker, company=company, market=market,
        sector=sector, currency=currency,
        entry_price=entry_price, quantity=quantity,
        invested_amount=invested_amount, is_open=True, entry_date=entry_dt,
    )
    session.add(position); session.flush()

    session.add(Transaction(
        user_id=user_id, username=username,
        portfolio_id=position.id, ticker=ticker,
        action="BUY", price=entry_price, quantity=quantity,
        amount=invested_amount, currency=currency, timestamp=entry_dt,
        notes=notes or ("Custom price" if custom_price else "Live price"),
    ))
    session.commit(); session.refresh(position)
    print(f"  ✓ {username or 'anon'} bought {ticker} × {quantity} @ {currency} {entry_price:,.2f}")
    session.close()
    return position


# ── Sell position ─────────────────────────────────────────────────────────────
def sell_position(portfolio_id: int, notes: str = None,
                  custom_price: float = None) -> dict:
    session  = Session()
    position = session.get(Portfolio, portfolio_id)
    if not position:
        session.close(); raise ValueError(f"Position {portfolio_id} not found")
    if not position.is_open:
        session.close(); raise ValueError(f"{position.ticker} is already closed")

    exit_price = round(custom_price, 2) if (custom_price and custom_price > 0) \
                 else _fetch_price(position.ticker)

    pnl_amount = round((exit_price - position.entry_price) * position.quantity, 2)
    pnl_pct    = round(((exit_price - position.entry_price) / position.entry_price) * 100, 2)

    position.is_open    = False
    position.exit_price = exit_price
    position.exit_date  = datetime.utcnow()

    session.add(Transaction(
        user_id=position.user_id, username=position.username,
        portfolio_id=portfolio_id, ticker=position.ticker,
        action="SELL", price=exit_price, quantity=position.quantity,
        amount=round(exit_price * position.quantity, 2),
        currency=position.currency,
        notes=notes or ("Custom price" if custom_price else "Live price"),
    ))
    session.commit()
    result = {"ticker":position.ticker,"entry_price":position.entry_price,
              "exit_price":exit_price,"quantity":position.quantity,
              "pnl_amount":pnl_amount,"pnl_pct":pnl_pct,"currency":position.currency}
    print(f"  {'🟢' if pnl_amount>=0 else '🔴'} {position.ticker} @ {exit_price:,.2f} | {pnl_pct:+.2f}%")
    session.close()
    return result


# ── Save AI analysis result to a portfolio position ───────────────────────────
def save_ai_analysis(portfolio_id: int, analysis: dict):
    """
    Saves the AI Hold/Sell/Buy More recommendation to the portfolio row.
    Adds ai_action, ai_confidence, ai_summary, ai_stop_loss, ai_target_price columns.
    """
    from sqlalchemy import text
    # Ensure columns exist
    with Session().bind.connect() as conn:
        for col, col_type in [
            ("ai_action",     "VARCHAR(20)"),
            ("ai_confidence", "VARCHAR(20)"),
            ("ai_summary",    "TEXT"),
            ("ai_stop_loss",  "FLOAT"),
            ("ai_target",     "FLOAT"),
            ("ai_date",       "VARCHAR(20)"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE portfolio ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                pass

    session = Session()
    pos     = session.get(Portfolio, portfolio_id)
    if pos:
        try:
            pos.ai_action     = analysis.get("action")
            pos.ai_confidence = analysis.get("confidence")
            pos.ai_summary    = analysis.get("summary")
            sl = analysis.get("stop_loss")
            tp = analysis.get("target_price")
            pos.ai_stop_loss  = float(sl) if sl and str(sl).lower() not in ("null","none","") else None
            pos.ai_target     = float(tp) if tp and str(tp).lower() not in ("null","none","") else None
            pos.ai_date       = datetime.today().strftime("%Y-%m-%d")
            session.commit()
        except Exception as e:
            print(f"  [save_ai] {e}")
    session.close()


# ── Get portfolio (STRICT user filtering — no null fallback) ──────────────────
def get_portfolio(market: str = None, username: str = None) -> list[dict]:
    """
    Returns open positions for a specific user ONLY.
    No fallback to null user_id — each user sees only their own positions.
    """
    session   = Session()
    query     = session.query(Portfolio).filter(Portfolio.is_open == True)
    if market:
        query = query.filter(Portfolio.market == market.upper())
    if username:
        # Match user_id OR username (display name) — but NOT null anymore
        query = query.filter(
            or_(Portfolio.user_id  == username,
                Portfolio.username == username)
        )
    positions = query.all()
    results   = []

    for pos in positions:
        try:
            current_price = _fetch_price(pos.ticker)
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
            # AI analysis if available
            "ai_action":     getattr(pos, "ai_action",     None),
            "ai_confidence": getattr(pos, "ai_confidence", None),
            "ai_summary":    getattr(pos, "ai_summary",    None),
            "ai_stop_loss":  getattr(pos, "ai_stop_loss",  None),
            "ai_target":     getattr(pos, "ai_target",     None),
            "ai_date":       getattr(pos, "ai_date",       None),
        })

    session.close()
    return results


# ── Metrics (strict per-user) ─────────────────────────────────────────────────
def get_portfolio_metrics(username: str = None) -> dict:
    session = Session()
    oq = session.query(Portfolio).filter(Portfolio.is_open == True)
    cq = session.query(Portfolio).filter(Portfolio.is_open == False)
    if username:
        oq = oq.filter(or_(Portfolio.user_id==username, Portfolio.username==username))
        cq = cq.filter(or_(Portfolio.user_id==username, Portfolio.username==username))
    open_pos   = oq.all()
    closed_pos = cq.all()

    total_inv = total_cur = 0
    for pos in open_pos:
        try:    cp = _fetch_price(pos.ticker)
        except: cp = pos.entry_price
        total_inv += pos.invested_amount
        total_cur += cp * pos.quantity

    wins = losses = 0; best = worst = None; bp = float("-inf"); wp = float("inf")
    for pos in closed_pos:
        if pos.entry_price and pos.exit_price:
            pct = ((pos.exit_price - pos.entry_price) / pos.entry_price) * 100
            if pct > 0: wins += 1
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
        "best_pick": best, "best_pick_pct":  round(bp, 2) if best  else None,
        "worst_pick": worst,"worst_pick_pct": round(wp, 2) if worst else None,
    }