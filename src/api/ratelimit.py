"""Small in-process sliding-window rate limiter (per client IP).

Per-instance only: with N replicas the effective limit is N x the setting. That
is still enough to blunt scraping and runaway clients; put a shared limiter at
the edge (Cloudflare etc.) if you need a hard global cap.
"""

import os
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

EXEMPT_PATHS = {"/", "/health", "/ready"}
# Path prefix -> (max requests, window seconds). First match wins.
LIMITS = [
    ("/api/auth/", (20, 60)),     # login / signup brute-force protection
    ("/api/crew/", (10, 60)),     # these start paid LLM work
    ("/api/",      (240, 60)),
]


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[tuple[str, str], deque] = defaultdict(deque)
        self._trust_proxy = os.getenv("TRUST_PROXY", "").lower() in ("1", "true", "yes")
        self._enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in ("0", "false", "no")
        self._last_sweep = time.monotonic()

    def _client(self, request) -> str:
        if self._trust_proxy:
            fwd = request.headers.get("x-forwarded-for")
            if fwd:
                return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < 300:
            return
        self._last_sweep = now
        for key in [k for k, dq in self._hits.items() if not dq or now - dq[-1] > 120]:
            del self._hits[key]

    async def dispatch(self, request, call_next):
        path = request.url.path
        if not self._enabled or request.method == "OPTIONS" or path in EXEMPT_PATHS:
            return await call_next(request)
        for prefix, (limit, window) in LIMITS:
            if path.startswith(prefix):
                break
        else:
            return await call_next(request)

        now = time.monotonic()
        self._sweep(now)
        dq = self._hits[(self._client(request), prefix)]
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= limit:
            retry = max(1, int(window - (now - dq[0])))
            return JSONResponse({"detail": "Too many requests. Slow down."},
                                status_code=429, headers={"Retry-After": str(retry)})
        dq.append(now)
        return await call_next(request)
