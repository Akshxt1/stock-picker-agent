# src/database/paper_trading.py

from datetime import datetime, timezone
from src.database.models import Session, Portfolio, Transaction, Pick


def _live_price(ticker: str) -> float | None:
    """Fetch the latest traded price: Upstox for India, yfinance for US."""
    try:
        if ticker.endswith((".NS", ".BO")):
            from src.providers import market_data_client
            upstox = market_data_client().providers.get("upstox")
            if upstox and upstox.available():
                q = upstox.quote(ticker)
                price = q.get("price")
                if price:
                    return float(price)
        # US or India fallback
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _fmt_pct(v):
    """yfinance decimal fraction → percentage string (0.2141 → '21.41%')."""
    return f"{v * 100:.2f}%" if isinstance(v, (int, float)) else None


def _fmt_de(v):
    """yfinance debtToEquity (ratio×100) → plain ratio string (335.5 → '3.35')."""
    return f"{v / 100:.2f}" if isinstance(v, (int, float)) else None


def _enrich_pick_fundamentals(item: dict) -> dict:
    """Fill ROE / D-E / RevGrowth / P-E / current_price from live market data.

    The LLM is unreliable at copying exact figures, so we authoritatively
    overwrite these fields with real values from the cached market data client.
    Any field we can't fetch keeps whatever the LLM provided (or stays None).
    """
    ticker = item.get("ticker")
    if not ticker:
        return item
    try:
        from src.providers import market_data_client
        client = market_data_client()

        try:
            info = client.fundamentals(ticker).data or {}
        except Exception:
            info = {}

        if info:
            roe = _fmt_pct(info.get("returnOnEquity"))
            de  = _fmt_de(info.get("debtToEquity"))
            rev = _fmt_pct(info.get("revenueGrowth"))
            pe  = info.get("trailingPE")
            if roe: item["roe"] = roe
            if de:  item["debt_to_equity"] = de
            if rev: item["revenue_growth"] = rev
            if isinstance(pe, (int, float)): item["pe_ratio"] = f"{pe:.2f}"
            if info.get("shortName") and not item.get("company"):
                item["company"] = info.get("shortName")

        # Always refresh live price so the card shows a real number.
        try:
            price = client.quote(ticker).data.get("price")
            if isinstance(price, (int, float)) and price > 0:
                item["current_price"] = round(float(price), 2)
        except Exception:
            pass
    except Exception:
        pass
    return item

def add_to_portfolio(ticker: str, quantity: float, user_id: str, username: str, custom_price: float = None, custom_date: str = None, notes: str = None, pick_id: int = None):
    """Adds a new open position to the paper trading portfolio and logs the transaction."""
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")

    with Session() as session:
        # Determine current asset price if not overridden manually
        if custom_price is not None and custom_price > 0:
            entry_price = custom_price
        else:
            try:
                entry_price = _live_price(ticker)
                if not entry_price:
                    raise ValueError(f"Could not retrieve a live price for ticker: {ticker}")
            except ValueError:
                raise
            except Exception as e:
                raise ValueError(f"Failed to fetch live market price for {ticker}: {str(e)}")

        # Parse entry date
        entry_date = datetime.now(timezone.utc)
        if custom_date:
            try:
                entry_date = datetime.strptime(custom_date.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD.")

        # Determine currency/market segment based on ticker syntax
        currency = "INR" if ticker.endswith((".NS", ".BO")) else "USD"
        market = "INDIA" if currency == "INR" else "US"

        # Check if an open position for this ticker already exists for this exact user
        existing = session.query(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.ticker == ticker,
            Portfolio.is_open == True
        ).first()

        if existing:
            # Average out the cost basis
            total_cost = (existing.entry_price * existing.quantity) + (entry_price * quantity)
            existing.quantity += quantity
            existing.entry_price = total_cost / existing.quantity
        else:
            # Create a brand new portfolio record
            position = Portfolio(
                user_id=user_id,
                username=username,
                ticker=ticker,
                market=market,
                currency=currency,
                quantity=quantity,
                entry_price=entry_price,
                entry_date=entry_date.replace(tzinfo=None),
                is_open=True,
                pick_id=pick_id,
                notes=notes
            )
            session.add(position)

        # Log the itemized trade in our append-only transactions history table
        tx = Transaction(
            user_id=user_id,
            username=username,
            ticker=ticker,
            action="BUY",
            quantity=quantity,
            price=entry_price,
            notes=notes
        )
        session.add(tx)
        session.commit()

def sell_position(position_id: int, notes: str = None, custom_price: float = None) -> dict:
    """Closes or scales down a portfolio position safely, enforcing owned limits."""
    with Session() as session:
        pos = session.get(Portfolio, position_id)
        if not pos or not pos.is_open:
            raise ValueError("Position not found or already closed.")

        # Resolve asset execution price
        if custom_price is not None and custom_price > 0:
            exit_price = custom_price
        else:
            exit_price = _live_price(pos.ticker) or pos.entry_price

        # Close position record completely
        pos.is_open = False
        pos.exit_price = exit_price
        pos.exit_date = datetime.now(timezone.utc).replace(tzinfo=None)
        if notes:
            pos.notes = f"{pos.notes} | Sell Notes: {notes}" if pos.notes else notes

        # Log out structural P&L metrics for the UI callback alert
        pnl_amount = (exit_price - pos.entry_price) * pos.quantity
        pnl_pct = ((exit_price - pos.entry_price) / pos.entry_price) * 100 if pos.entry_price else 0.0

        tx = Transaction(
            user_id=pos.user_id,
            username=pos.username,
            ticker=pos.ticker,
            action="SELL",
            quantity=pos.quantity,
            price=exit_price,
            notes=notes
        )
        session.add(tx)
        session.commit()

        return {
            "ticker": pos.ticker,
            "quantity": pos.quantity,
            "pnl_amount": pnl_amount,
            "pnl_pct": pnl_pct
        }

def get_portfolio(market: str = None, user_id: str = None) -> list:
    """Fetches all open positions with up-to-date live market valuations."""
    with Session() as session:
        query = session.query(Portfolio).filter(Portfolio.is_open == True)
        if market:
            query = query.filter(Portfolio.market == market)
        if user_id:
            query = query.filter(Portfolio.user_id == user_id)
        positions = query.all()

        output = []
        for p in positions:
            current_price = _live_price(p.ticker) or p.entry_price

            invested = p.entry_price * p.quantity
            current_value = current_price * p.quantity
            pnl_amount = current_value - invested
            pnl_pct = (pnl_amount / invested * 100) if invested else 0.0
            days_held = (datetime.now() - p.entry_date).days

            output.append({
                "id": p.id, "ticker": p.ticker, "company": p.ticker, "market": p.market,
                "currency": p.currency, "quantity": p.quantity, "entry_price": p.entry_price,
                "current_price": current_price, "invested": invested, "current_value": current_value,
                "pnl_amount": pnl_amount, "pnl_pct": pnl_pct, "days_held": max(0, days_held)
            })
        return output

def get_portfolio_metrics(user_id: str = None) -> dict:
    """Calculates win rate, best/worst closed trades, and overall book stats."""
    with Session() as session:
        open_q = session.query(Portfolio).filter(Portfolio.is_open == True)
        closed_q = session.query(Portfolio).filter(Portfolio.is_open == False)
        
        if user_id:
            open_q = open_q.filter(Portfolio.user_id == user_id)
            closed_q = closed_q.filter(Portfolio.user_id == user_id)

        open_positions = open_q.count()
        closed_positions = closed_q.all()

        wins = 0
        losses = 0
        best_pick = None
        best_pct = -99999.0
        worst_pick = None
        worst_pct = 99999.0

        for cp in closed_positions:
            pct = ((cp.exit_price - cp.entry_price) / cp.entry_price * 100) if cp.entry_price else 0.0
            if pct >= 0:
                wins += 1
            else:
                losses += 1

            if pct > best_pct:
                best_pct = pct
                best_pick = cp.ticker
            if pct < worst_pct:
                worst_pct = pct
                worst_pick = cp.ticker

        total_closed = wins + losses
        win_rate = round((wins / total_closed * 100), 1) if total_closed > 0 else None

        # Add live evaluations for open totals
        open_items = get_portfolio(user_id=user_id)
        total_inv = sum(i["invested"] for i in open_items)
        total_val = sum(i["current_value"] for i in open_items)
        pnl = total_val - total_inv
        pnl_pct = (pnl / total_inv * 100) if total_inv else 0.0

        return {
            "open_positions": open_positions,
            "closed_positions": total_closed,
            "total_invested": total_inv,
            "current_value": total_val,
            "unrealised_pnl": pnl,
            "unrealised_pnl_pct": pnl_pct,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "best_pick": best_pick,
            "best_pick_pct": best_pct if best_pick else None,
            "worst_pick": worst_pick,
            "worst_pick_pct": worst_pct if worst_pick else None
        }

def save_picks(crew_result: dict, run_by_user_id: str = None,
               run_by_username: str = None) -> list:
    """Saves generated crew picks to the history database.

    Dedup: re-running the same user + market + sector + size on the same day
    REPLACES the prior picks instead of accumulating duplicates.

    Returns the saved picks as normalized dicts (with DB ids) so callers can
    hand the frontend fully-shaped, clickable picks.
    """
    from src.database.models import _pick_to_dict

    if not crew_result or "picks" not in crew_result:
        return []

    market   = crew_result.get("market")
    sector   = crew_result.get("sector")
    size     = crew_result.get("size")
    analysis_date = crew_result.get("analysis_date")

    saved = []
    with Session() as session:
        # Remove any prior same-combo, same-day picks for this user (dedup).
        if run_by_user_id and analysis_date:
            session.query(Pick).filter(
                Pick.run_by_user_id == run_by_user_id,
                Pick.market == market,
                Pick.sector == sector,
                Pick.size == size,
                Pick.analysis_date == analysis_date,
            ).delete(synchronize_session=False)

        for item in crew_result["picks"]:
            item = _enrich_pick_fundamentals(item)
            pick = Pick(
                market=crew_result.get("market"),
                sector=crew_result.get("sector"),
                size=crew_result.get("size"),
                analysis_date=crew_result.get("analysis_date"),
                ticker=item.get("ticker"),
                company=item.get("company"),
                current_price=item.get("current_price"),
                currency=item.get("currency"),
                why_buy=item.get("why_buy"),
                why_not_buy=item.get("why_not_buy"),
                technical_signal=item.get("technical_signal"),
                sentiment=item.get("sentiment"),
                confidence=item.get("confidence"),
                roe=item.get("roe"),
                debt_to_equity=item.get("debt_to_equity"),
                revenue_growth=item.get("revenue_growth"),
                pe_ratio=item.get("pe_ratio"),
                stop_loss_pct=item.get("stop_loss_pct"),
                target_pct=item.get("target_pct"),
                price_at_pick=item.get("current_price"),
                run_by_user_id=run_by_user_id,
                run_by_username=run_by_username,
            )
            session.add(pick)
            saved.append(pick)
        session.commit()
        return [_pick_to_dict(p) for p in saved]