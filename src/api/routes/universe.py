"""
src/api/routes/universe.py

GET /api/universe/sectors?market=INDIA         — available sectors for a market
GET /api/universe/sizes?market=INDIA           — available cap sizes for a market
GET /api/universe/search?q=...&market=INDIA    — search stocks by ticker or company name
"""

from fastapi import APIRouter, Query
from src.data.stock_universe import INDIAN_STOCKS, US_STOCKS, TICKER_NAMES

router = APIRouter()

_SECTORS = {
    "INDIA": [
        "Telecom", "Banking", "IT", "Pharma", "FMCG",
        "Auto", "Energy", "Metals", "Realty", "Infrastructure",
        "Chemicals", "Consumer Discretionary",
    ],
    "US": [
        "Technology", "Healthcare", "Financials", "Energy",
        "Consumer Staples", "Consumer Discretionary",
        "Industrials", "Materials", "Utilities", "Real Estate",
        "Communication Services",
    ],
}

_SIZES = {
    "INDIA": ["Large", "Mid", "Small"],
    "US":    ["Mega", "Large", "Mid", "Small"],
}


@router.get("/sectors")
def sectors(market: str = Query("INDIA")):
    return _SECTORS.get(market.upper(), _SECTORS["INDIA"])


@router.get("/sizes")
def sizes(market: str = Query("INDIA")):
    return _SIZES.get(market.upper(), _SIZES["INDIA"])


@router.get("/search")
def search_stocks(q: str = Query(""), market: str = Query("INDIA"), limit: int = Query(10)):
    """Search stocks in the universe by ticker substring or company name."""
    q = q.strip()
    if not q:
        return []

    universe = INDIAN_STOCKS if market.upper() == "INDIA" else US_STOCKS
    q_lower = q.lower()
    seen: set[str] = set()
    results = []

    for sector, sizes_map in universe.items():
        for size, tickers in sizes_map.items():
            for ticker in tickers:
                if ticker in seen:
                    continue
                company_name = TICKER_NAMES.get(ticker, ticker.replace(".NS", ""))
                if q_lower in ticker.lower() or q_lower in company_name.lower():
                    seen.add(ticker)
                    results.append({
                        "ticker": ticker,
                        "company_name": company_name,
                        "sector": sector,
                        "size": size,
                        "market": market.upper(),
                    })
                    if len(results) >= limit:
                        return results

    return results
