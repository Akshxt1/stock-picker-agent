"""Asset identity: one canonical symbol string per tradable thing, any asset class.

Symbol grammar (kept compatible with the existing stock tickers):

    RELIANCE.NS, TCS.BO, AAPL       equities / ETFs / US mutual funds (unchanged)
    CRYPTO:bitcoin                  crypto, by CoinGecko coin id
    MF:118989                       Indian mutual fund, by AMFI scheme code

US mutual funds and ETFs share the plain-ticker form, so they are told apart
from stocks by an explicit `asset_class` (e.g. stored on the portfolio row).
"""

from dataclasses import dataclass
from enum import Enum


class AssetClass(str, Enum):
    EQUITY = "EQUITY"
    CRYPTO = "CRYPTO"
    FUND = "FUND"


# Standard chart periods (yfinance-style) -> calendar days. "max" is capped by providers.
PERIOD_DAYS = {
    "1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
    "1y": 365, "2y": 730, "5y": 1825, "max": 36500,
}


def period_days(period: str) -> int:
    return PERIOD_DAYS.get(period, 180)


@dataclass(frozen=True)
class AssetRef:
    symbol: str            # canonical, as stored/passed around
    asset_class: AssetClass
    market: str            # INDIA | US | CRYPTO
    currency: str          # native quote currency
    provider_id: str       # id for the class-specific provider (coin id, scheme code, ticker)

    @property
    def display(self) -> str:
        return self.provider_id if self.asset_class != AssetClass.CRYPTO else self.provider_id.upper()


def parse_symbol(symbol: str, asset_class: str | AssetClass | None = None) -> AssetRef:
    """Resolve a user/portfolio symbol to an AssetRef. Raises ValueError on bad input."""
    raw = (symbol or "").strip()
    if not raw:
        raise ValueError("Empty symbol")

    head, sep, tail = raw.partition(":")
    prefix = head.upper() if sep else ""

    if prefix == "CRYPTO":
        coin_id = tail.strip().lower()
        if not coin_id or not all(c.isalnum() or c in "-_" for c in coin_id):
            raise ValueError(f"Invalid crypto id: {tail!r}")
        return AssetRef(f"CRYPTO:{coin_id}", AssetClass.CRYPTO, "CRYPTO", "USD", coin_id)

    if prefix == "MF":
        code = tail.strip()
        if not code.isdigit():
            raise ValueError(f"Invalid mutual fund scheme code: {tail!r}")
        return AssetRef(f"MF:{code}", AssetClass.FUND, "INDIA", "INR", code)

    if sep:
        raise ValueError(f"Unknown symbol prefix: {head!r}")

    ticker = raw.upper()
    if not all(c.isalnum() or c in ".-^=" for c in ticker):
        raise ValueError(f"Invalid ticker: {raw!r}")
    market, currency = ("INDIA", "INR") if ticker.endswith((".NS", ".BO")) else ("US", "USD")
    cls = AssetClass(asset_class) if asset_class else AssetClass.EQUITY
    if cls == AssetClass.CRYPTO:
        raise ValueError("Crypto symbols must use the CRYPTO:<id> form")
    return AssetRef(ticker, cls, market, currency, ticker)
