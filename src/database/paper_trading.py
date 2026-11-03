# src/database/paper_trading.py

from src.database.models import Session, Pick


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