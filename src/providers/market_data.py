import os
import time
import threading
import datetime
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv, find_dotenv

from src.providers.cache import get_cached, set_cached

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


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
    """
    IIFL Securities market data provider.
    Calls the IIFL OpenAPI directly (no IIFLapis SDK) using AES-256-CBC auth.

    Required env vars:
        IIFL_USER_ID      – client code (e.g. AKSHGUP5)
        IIFL_PASSWORD     – trading account password
        IIFL_API_KEY      – App Key (also used as OCP subscription key)
        IIFL_SECRET_KEY   – App Secret Key (AES encryption key)
        IIFL_APP_NAME     – registered app name
        IIFL_APP_SOURCE   – "WEB" (default)
        IIFL_DOB          – date of birth YYYYMMDD for My2PIN (optional)
    """

    name = "iifl"

    _BASE_URLS = [
        "https://openapi.iifl.com/openapi/prod",
        "https://dataservice.iifl.in/openapi/prod",
    ]
    _SCRIPMASTER_URL = "http://content.indiainfoline.com/IIFLTT/Scripmaster.csv"
    _SCRIP_CACHE     = Path(__file__).parent / "_iifl_scripmaster.csv"

    def __init__(self):
        self._user_id   = os.getenv("IIFL_USER_ID", "")
        self._password  = os.getenv("IIFL_PASSWORD", "")
        self._api_key   = os.getenv("IIFL_API_KEY", "")
        self._enc_key   = os.getenv("IIFL_SECRET_KEY", "")
        self._app_name  = os.getenv("IIFL_APP_NAME", "")
        self._app_source= os.getenv("IIFL_APP_SOURCE", "WEB")
        self._dob       = os.getenv("IIFL_DOB", "")

        self._jwt: str | None = None
        self._jwt_expiry: float = 0.0
        self._lock = threading.Lock()
        self._scrip_df: pd.DataFrame | None = None
        self._base_url: str = self._BASE_URLS[0]

    def available(self) -> bool:
        return bool(self._user_id and self._password and self._api_key and self._enc_key)

    # ── Encryption (matches IIFLapis/auth.py exactly) ─────────────────────────

    def _encrypt(self, text: str) -> str:
        from Crypto.Cipher import AES
        import base64
        from pbkdf2 import PBKDF2
        iv       = bytes([83, 71, 26, 58, 54, 35, 22, 11,
                          83, 71, 26, 58, 54, 35, 22, 11])
        key_gen  = PBKDF2(self._enc_key, iv)
        aes_iv   = key_gen.read(16)
        aes_key  = key_gen.read(32)
        cipher   = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_len  = 16 - len(text) % 16
        padded   = bytes(text + chr(pad_len) * pad_len, encoding="utf-8")
        return base64.b64encode(cipher.encrypt(padded)).decode("utf-8")

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _ocp_headers(self) -> dict:
        return {"Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": self._api_key}

    def _jwt_headers(self) -> dict:
        return {"Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": self._api_key,
                "x-clientcode": self._user_id,
                "x-auth-token": self._jwt or ""}

    def _head_block(self, request_code: str) -> dict:
        return {
            "appName":     self._app_name,
            "appVer":      "1.0",
            "key":         self._api_key,
            "osName":      "Android",
            "requestCode": request_code,
            "userId":      self._user_id,
            "password":    self._password,   # plain text per IIFL SDK (only body fields are encrypted)
        }

    # ── Session management ────────────────────────────────────────────────────

    def _login(self) -> None:
        payload = {
            "head": self._head_block("IIFLMarRQLoginRequestV4"),
            "body": {
                "ClientCode":     self._encrypt(self._user_id),
                "Password":       self._encrypt(self._password),
                "My2PIN":         self._encrypt(self._dob) if self._dob else "",
                "LocalIP":        "192.168.10.10",
                "PublicIP":       "192.168.10.10",
                "HDSerailNumber": " ",   # note IIFL SDK has this exact typo
                "MACAddress":     " ",
                "MachineID":      " ",
                "VersionNo":      "1.0.16.0",
                "RequestNo":      "1",
                "ConnectionType": "1",
            },
        }
        last_err = "no endpoints reachable"
        for base in self._BASE_URLS:
            try:
                resp = requests.post(f"{base}/LoginRequest", json=payload,
                                     headers=self._ocp_headers(), timeout=15)
                if resp.status_code >= 500:
                    last_err = f"HTTP {resp.status_code} from {base}"
                    continue
                data  = resp.json()
                token = data.get("body", {}).get("Token", "")
                msg   = data.get("body", {}).get("Msg", "")
                if token:
                    self._jwt        = token
                    self._jwt_expiry = time.time() + 6600
                    self._base_url   = base
                    logger.info("IIFL session OK via %s for %s", base, self._user_id)
                    return
                last_err = msg or f"no token from {base}: {resp.text[:200]}"
            except Exception as exc:
                last_err = str(exc)
        raise ProviderError(f"IIFL login failed: {last_err}")

    def _ensure_session(self) -> None:
        with self._lock:
            if not self._jwt or time.time() >= self._jwt_expiry:
                self._login()

    # ── ScripMaster ───────────────────────────────────────────────────────────

    def _scrip_master(self) -> pd.DataFrame:
        if self._scrip_df is not None:
            return self._scrip_df
        if self._SCRIP_CACHE.exists():
            if time.time() - self._SCRIP_CACHE.stat().st_mtime < 86400:
                self._scrip_df = pd.read_csv(self._SCRIP_CACHE, low_memory=False)
                return self._scrip_df
        logger.info("Downloading IIFL ScripMaster CSV…")
        df = pd.read_csv(self._SCRIPMASTER_URL, low_memory=False)
        df.to_csv(self._SCRIP_CACHE, index=False)
        self._scrip_df = df
        return df

    def _to_scripcode(self, ticker: str) -> tuple[str, str, str]:
        """Return (exch, exchType, scripcode_str) for an NSE/BSE ticker.

        ScripMaster columns: Exch(N/B), ExchType(C), Scripcode, Name(symbol), Series(EQ/BE)
        """
        if ticker.endswith(".BO"):
            exch, sym = "B", ticker[:-3]
        else:
            exch, sym = "N", ticker.replace(".NS", "")
        exch_type = "C"

        df        = self._scrip_master()
        sym_upper = sym.upper()
        base_mask = (df["Exch"] == exch) & (df["ExchType"] == exch_type)

        # Exact symbol match with preferred equity series
        for series in ("EQ", "BE", "N1", ""):
            if series:
                hit = df[base_mask & (df["Name"].str.upper() == sym_upper)
                         & (df["Series"] == series)]
            else:
                hit = df[base_mask & (df["Name"].str.upper() == sym_upper)]
            if not hit.empty:
                return exch, exch_type, str(int(hit.iloc[0]["Scripcode"]))

        raise ProviderError(f"IIFL: ScripCode not found for {ticker}")

    # ── Quote (MarketFeed) ────────────────────────────────────────────────────

    def quote(self, ticker: str) -> dict:
        self._ensure_session()
        exch, exch_type, scripcode = self._to_scripcode(ticker)
        payload = {
            "head": self._head_block("IIFLMarRQMarketFeed"),
            "body": {
                "ClientCode":      self._user_id,
                "MarketFeedData":  [{"Exch": exch, "ExchType": exch_type,
                                     "ScripCode": int(scripcode)}],
                "Count":           1,
                "ClientLoginType": 0,
                "LastRequestTime": f"/Date({int(time.time())})/",
                "RefreshRate":     "H",
            },
        }
        resp = requests.post(f"{self._base_url}/MarketFeed", json=payload,
                             headers=self._jwt_headers(), timeout=12)
        resp.raise_for_status()
        feeds = resp.json().get("body", {}).get("Data", [])
        if not feeds:
            raise ProviderError(f"IIFL: empty market feed for {ticker}")
        f     = feeds[0]
        price = float(f.get("LastRate") or 0)
        prev  = float(f.get("PClose")   or price)
        if not price:
            raise ProviderError(f"IIFL: zero price for {ticker}")
        return {
            "ticker":         ticker,
            "price":          price,
            "previous_close": prev,
            "day_change_pct": ((price - prev) / prev * 100) if prev else 0.0,
            "open":           f.get("OpenRate"),
            "high":           f.get("High"),
            "low":            f.get("Low"),
            "volume":         f.get("TtlTrdQnty"),
        }

    # ── History (historical candles) ──────────────────────────────────────────

    def history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        self._ensure_session()
        exch, exch_type, scripcode = self._to_scripcode(ticker)
        days  = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}.get(period, 180)
        end   = datetime.date.today()
        start = end - datetime.timedelta(days=days)
        url   = (f"{self._base_url}/historical/{exch}/{exch_type}/{scripcode}/1D"
                 f"?from={start}&end={end}")
        resp  = requests.get(url, headers=self._jwt_headers(), timeout=20)
        resp.raise_for_status()
        candles = resp.json().get("candles", [])
        if not candles:
            raise ProviderError(f"IIFL: no historical data for {ticker}")
        df = pd.DataFrame(candles, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[["Open", "High", "Low", "Close", "Volume"]]


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


class FinnhubProvider(BaseProvider):
    """
    Finnhub.io market data provider — covers US stocks fully on the free tier.
    Indian (NSE) tickers return 403 on free tier, so this provider is only used
    for US tickers (enforced via _order() in MarketDataClient).

    Required env var: FINNHUB_API_KEY
    """

    name = "finnhub"
    _BASE = "https://finnhub.io/api/v1"

    def available(self) -> bool:
        return bool(os.getenv("FINNHUB_API_KEY"))

    def _get(self, path: str, params: dict) -> dict:
        params["token"] = os.getenv("FINNHUB_API_KEY")
        resp = requests.get(f"{self._BASE}/{path}", params=params, timeout=12)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _sym(ticker: str) -> str:
        return ticker.split(".")[0] if "." in ticker else ticker

    def quote(self, ticker: str) -> dict:
        sym = self._sym(ticker)
        data = self._get("quote", {"symbol": sym})
        price = float(data.get("c") or 0)
        if not price:
            raise ProviderError(f"Finnhub: no quote for {sym}")
        prev = float(data.get("pc") or price)
        return {
            "ticker": ticker,
            "price": price,
            "previous_close": prev,
            "day_change_pct": float(data.get("dp") or 0),
            "open": data.get("o"),
            "high": data.get("h"),
            "low": data.get("l"),
        }

    def fundamentals(self, ticker: str) -> dict:
        sym = self._sym(ticker)

        profile = self._get("stock/profile2", {"symbol": sym})
        if not profile or not profile.get("name"):
            raise ProviderError(f"Finnhub: no profile for {sym}")

        m_resp = self._get("stock/metric", {"symbol": sym, "metric": "all"})
        m = m_resp.get("metric", {})

        def _dec(key: str):
            v = m.get(key)
            return v / 100.0 if isinstance(v, (int, float)) else None

        def _de(key: str):
            v = m.get(key)
            # Finnhub returns D/E as plain ratio (0.26); yfinance returns ratio×100 (26.0)
            return v * 100.0 if isinstance(v, (int, float)) else None

        cap_m = profile.get("marketCapitalization")
        return {
            "shortName":         profile.get("name", ticker),
            "longName":          profile.get("name", ticker),
            "sector":            profile.get("finnhubIndustry", ""),
            "industry":          profile.get("finnhubIndustry", ""),
            "marketCap":         cap_m * 1_000_000 if cap_m else None,
            "trailingPE":        m.get("peBasicExclExtraTTM"),
            "priceToBook":       m.get("pbQuarterly") or m.get("pbAnnual"),
            "returnOnEquity":    _dec("roeTTM"),
            "debtToEquity":      _de("totalDebt/totalEquityAnnual"),
            "revenueGrowth":     _dec("revenueGrowthTTMYoy"),
            "trailingEps":       m.get("epsBasicExclExtraItemsTTM"),
            "fiftyTwoWeekHigh":  m.get("52WeekHigh"),
            "fiftyTwoWeekLow":   m.get("52WeekLow"),
            "dividendYield":     _dec("dividendYieldIndicatedAnnual"),
        }


class MarketDataClient:
    def __init__(self):
        self.providers = {
            "iifl":         IIFLProvider(),
            "yfinance":     YFinanceProvider(),
            "twelvedata":   TwelveDataProvider(),
            "alphavantage": AlphaVantageProvider(),
            "finnhub":      FinnhubProvider(),
        }

    def _order(self, ticker: str, data_type: str) -> list[str]:
        market = _ticker_market(ticker)
        env_key = f"{market}_{data_type}_PROVIDER_ORDER"
        # US: Finnhub first (real-time, reliable free tier for NYSE/NASDAQ).
        # India: yfinance only — Finnhub free tier 403s all NSE tickers.
        # IIFL's legacy OpenAPI decommissioned; kept for future Capital Connect rewrite.
        # Override via env, e.g. US_QUOTE_PROVIDER_ORDER=yfinance,finnhub
        if market == "US":
            default = ["finnhub", "yfinance", "twelvedata", "alphavantage"]
        else:
            default = ["yfinance", "twelvedata", "alphavantage"]
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
