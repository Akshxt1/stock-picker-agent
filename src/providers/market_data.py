import os
from dataclasses import dataclass

import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv, find_dotenv

from src.providers.cache import get_cached, set_cached

load_dotenv(find_dotenv())


class ProviderError(Exception):
    pass


def _normalize_order(value: str, default: list[str]) -> list[str]:
    if not value:
        return default
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def _ticker_market(ticker: str) -> str:
    return "INDIA" if ticker.endswith((".NS", ".BO")) else "US"


def _period_to_outputsize(period: str) -> int:
    return {
        "1d": 5,
        "5d": 10,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
    }.get(period, 180)


def _df_to_payload(df: pd.DataFrame, source: str) -> dict:
    out = df.copy()
    out.index = out.index.astype(str)
    return {
        "source": source,
        "columns": list(out.columns),
        "index": list(out.index),
        "data": out.where(pd.notna(out), None).values.tolist(),
    }


def _payload_to_df(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(
        payload.get("data", []),
        index=pd.to_datetime(payload.get("index", [])),
        columns=payload.get("columns", []),
    )


@dataclass
class ProviderResult:
    source: str
    data: object


class BaseProvider:
    name = "base"

    def available(self) -> bool:
        return True

    def history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        raise ProviderError(f"{self.name} does not support history")

    def quote(self, ticker: str) -> dict:
        raise ProviderError(f"{self.name} does not support quotes")

    def fundamentals(self, ticker: str) -> dict:
        raise ProviderError(f"{self.name} does not support fundamentals")


class IIFLProvider(BaseProvider):
    name = "iifl"

    def available(self) -> bool:
        return bool(os.getenv("IIFL_APP_KEY") and os.getenv("IIFL_APP_SECRET_KEY"))

    def history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        raise ProviderError("IIFL provider is configured but endpoint mapping is pending.")

    def quote(self, ticker: str) -> dict:
        raise ProviderError("IIFL provider is configured but endpoint mapping is pending.")


class YFinanceProvider(BaseProvider):
    name = "yfinance"

    def history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=False)
        if hist.empty:
            raise ProviderError(f"No yfinance history for {ticker}")
        return hist

    def quote(self, ticker: str) -> dict:
        hist = self.history(ticker, "5d")
        close = hist["Close"].dropna()
        if close.empty:
            raise ProviderError(f"No yfinance quote for {ticker}")
        price = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) > 1 else price
        return {
            "ticker": ticker,
            "price": price,
            "previous_close": prev,
            "day_change_pct": ((price - prev) / prev * 100) if prev else 0.0,
        }

    def fundamentals(self, ticker: str) -> dict:
        info = yf.Ticker(ticker).info
        if not info:
            raise ProviderError(f"No yfinance fundamentals for {ticker}")
        return info


class TwelveDataProvider(BaseProvider):
    name = "twelvedata"
    base_url = "https://api.twelvedata.com"

    def available(self) -> bool:
        return bool(os.getenv("TWELVE_DATA_API_KEY"))

    def _params(self, ticker: str) -> dict:
        symbol = ticker.replace(".NS", "").replace(".BO", "")
        params = {"symbol": symbol, "apikey": os.getenv("TWELVE_DATA_API_KEY")}
        if ticker.endswith(".NS"):
            params["exchange"] = "NSE"
        elif ticker.endswith(".BO"):
            params["exchange"] = "BSE"
        return params

    def quote(self, ticker: str) -> dict:
        params = self._params(ticker)
        resp = requests.get(f"{self.base_url}/quote", params=params, timeout=12)
        data = resp.json()
        if data.get("status") == "error":
            raise ProviderError(data.get("message", "Twelve Data quote failed"))
        price = float(data.get("close") or data.get("price") or 0)
        if not price:
            raise ProviderError(f"No Twelve Data quote for {ticker}")
        prev = float(data.get("previous_close") or price)
        return {
            "ticker": ticker,
            "price": price,
            "previous_close": prev,
            "day_change_pct": ((price - prev) / prev * 100) if prev else 0.0,
        }

    def history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        params = self._params(ticker)
        params.update({"interval": "1day", "outputsize": _period_to_outputsize(period)})
        resp = requests.get(f"{self.base_url}/time_series", params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "error":
            raise ProviderError(data.get("message", "Twelve Data history failed"))
        values = data.get("values") or []
        if not values:
            raise ProviderError(f"No Twelve Data history for {ticker}")
        df = pd.DataFrame(values)
        df = df.rename(columns={
            "datetime": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[["Open", "High", "Low", "Close", "Volume"]]


class AlphaVantageProvider(BaseProvider):
    name = "alphavantage"
    base_url = "https://www.alphavantage.co/query"

    def available(self) -> bool:
        return bool(os.getenv("ALPHA_VANTAGE_API_KEY"))

    def _symbol(self, ticker: str) -> str:
        if ticker.endswith(".BO"):
            return ticker.replace(".BO", ".BSE")
        return ticker.replace(".NS", "")

    def quote(self, ticker: str) -> dict:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": self._symbol(ticker),
            "apikey": os.getenv("ALPHA_VANTAGE_API_KEY"),
        }
        data = requests.get(self.base_url, params=params, timeout=15).json()
        quote = data.get("Global Quote") or {}
        price = float(quote.get("05. price") or 0)
        if not price:
            raise ProviderError(f"No Alpha Vantage quote for {ticker}")
        prev = float(quote.get("08. previous close") or price)
        return {
            "ticker": ticker,
            "price": price,
            "previous_close": prev,
            "day_change_pct": ((price - prev) / prev * 100) if prev else 0.0,
        }

    def history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": self._symbol(ticker),
            "outputsize": "compact",
            "apikey": os.getenv("ALPHA_VANTAGE_API_KEY"),
        }
        data = requests.get(self.base_url, params=params, timeout=20).json()
        series = data.get("Time Series (Daily)") or {}
        if not series:
            raise ProviderError(f"No Alpha Vantage history for {ticker}")
        df = pd.DataFrame.from_dict(series, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index().rename(columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close",
            "6. volume": "Volume",
        })
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[["Open", "High", "Low", "Close", "Volume"]].tail(_period_to_outputsize(period))


class MarketDataClient:
    def __init__(self):
        self.providers = {
            "iifl": IIFLProvider(),
            "yfinance": YFinanceProvider(),
            "twelvedata": TwelveDataProvider(),
            "alphavantage": AlphaVantageProvider(),
        }

    def _order(self, ticker: str, data_type: str) -> list[str]:
        market = _ticker_market(ticker)
        env_key = f"{market}_{data_type}_PROVIDER_ORDER"
        default = (
            ["iifl", "yfinance", "twelvedata", "alphavantage"]
            if market == "INDIA"
            else ["yfinance", "twelvedata", "alphavantage"]
        )
        return _normalize_order(os.getenv(env_key), default)

    def history(self, ticker: str, period: str = "6mo", ttl_seconds: int = 21600) -> ProviderResult:
        cache_key = f"history:{ticker}:{period}"
        cached = get_cached(cache_key)
        if cached:
            return ProviderResult(cached.get("source", "cache"), _payload_to_df(cached))

        errors = []
        for name in self._order(ticker, "HISTORY"):
            provider = self.providers.get(name)
            if not provider or not provider.available():
                continue
            try:
                data = provider.history(ticker, period)
                set_cached(cache_key, provider.name, _df_to_payload(data, provider.name), ttl_seconds)
                return ProviderResult(provider.name, data)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        raise ProviderError("; ".join(errors) or f"No history provider available for {ticker}")

    def quote(self, ticker: str, ttl_seconds: int = 300) -> ProviderResult:
        cache_key = f"quote:{ticker}"
        cached = get_cached(cache_key)
        if cached:
            return ProviderResult(cached.get("source", "cache"), cached)

        errors = []
        for name in self._order(ticker, "QUOTE"):
            provider = self.providers.get(name)
            if not provider or not provider.available():
                continue
            try:
                data = provider.quote(ticker)
                payload = {"source": provider.name, **data}
                set_cached(cache_key, provider.name, payload, ttl_seconds)
                return ProviderResult(provider.name, payload)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        raise ProviderError("; ".join(errors) or f"No quote provider available for {ticker}")

    def fundamentals(self, ticker: str, ttl_seconds: int = 86400) -> ProviderResult:
        cache_key = f"fundamentals:{ticker}"
        cached = get_cached(cache_key)
        if cached:
            return ProviderResult(cached.get("source", "cache"), cached)

        errors = []
        for name in self._order(ticker, "FUNDAMENTALS"):
            provider = self.providers.get(name)
            if not provider or not provider.available():
                continue
            try:
                data = provider.fundamentals(ticker)
                payload = {"source": provider.name, **data}
                set_cached(cache_key, provider.name, payload, ttl_seconds)
                return ProviderResult(provider.name, payload)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        raise ProviderError("; ".join(errors) or f"No fundamentals provider available for {ticker}")


_client = MarketDataClient()


def market_data_client() -> MarketDataClient:
    return _client
