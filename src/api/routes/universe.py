"""
src/api/routes/universe.py

GET /api/universe/sectors?market=INDIA  — available sectors for a market
GET /api/universe/sizes?market=INDIA    — available cap sizes for a market
"""

from fastapi import APIRouter, Query

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
