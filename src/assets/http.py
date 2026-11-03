"""Shared HTTP session with retries/backoff for the public asset APIs."""

import threading

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = 15


class UpstreamError(Exception):
    """An upstream data API failed or returned something unusable."""


def build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.8, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET",), respect_retry_after_header=True)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = "stock-picker-agent/2.1"
    return s


def get_json(session: requests.Session, url: str, **kwargs):
    try:
        r = session.get(url, timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError) as e:
        raise UpstreamError(f"{url}: {e}") from e


class KeyedLock:
    """One lock per key, so concurrent requests for the same uncached resource trigger a
    single upstream call (the rest wait, then read the cache). Public APIs like CoinGecko
    rate limit hard, and the UI fires history + metrics for the same series at once."""

    def __init__(self):
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}

    def __call__(self, key: str) -> threading.Lock:
        with self._guard:
            if len(self._locks) > 2048:          # bound memory; idle locks are safe to drop
                self._locks = {k: v for k, v in self._locks.items() if v.locked()}
            return self._locks.setdefault(key, threading.Lock())
