"""Provider health checks, so an expired or revoked API token is noticed, not discovered
as mysteriously stale data.

Upstox is the primary India source; when its token dies the app silently falls back to
Yahoo, which is much weaker for Indian fundamentals. This module:

  * probes Upstox with a cheap authenticated call (cached, so /ready polling is free),
  * reads the token's `exp` claim to warn before it expires,
  * logs loudly (ERROR) when the state gets worse, and re-warns on a schedule,
  * runs hourly in the background (start_monitor) and is exposed via /ready and
    /api/admin/provider-health.
"""

import base64
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger("stockpicker.health")

UPSTOX_PROBE = "https://api.upstox.com/v2/market/status/NSE"
CACHE_SECONDS = 300
MONITOR_EVERY = 3600
WARN_DAYS = 30          # start warning this long before expiry
REWARN_SECONDS = 6 * 3600

_lock = threading.Lock()
_cache: dict[str, tuple[float, dict]] = {}
_last_status: dict[str, str] = {}
_last_warned: dict[str, float] = {}


def token_expiry(token: str) -> datetime | None:
    """`exp` claim of a JWT (no signature check; used only for warnings)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp")
        return datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
    except Exception:
        return None


def check_upstox(timeout: float = 5.0) -> dict:
    token = os.getenv("UPSTOX_ANALYTICS_TOKEN", "").strip()
    if not token:
        return {"provider": "upstox", "status": "not_configured",
                "detail": "UPSTOX_ANALYTICS_TOKEN is not set; India data falls back to Yahoo."}

    out: dict = {"provider": "upstox"}
    exp = token_expiry(token)
    if exp:
        days = (exp - datetime.now(timezone.utc)).days
        out["token_expires_at"] = exp.isoformat()
        out["days_until_expiry"] = days
        if days < 0:
            return {**out, "status": "token_expired",
                    "detail": "Upstox token has expired. Generate a new Analytics Token and update the env var."}

    try:
        r = requests.get(UPSTOX_PROBE, timeout=timeout,
                         headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    except requests.RequestException as e:
        return {**out, "status": "unreachable", "detail": f"Upstox API not reachable: {type(e).__name__}"}

    if r.status_code in (401, 403):
        return {**out, "status": "token_invalid",
                "detail": "Upstox rejected the token (revoked or expired). Generate a new Analytics Token."}
    if r.status_code >= 400:
        return {**out, "status": "degraded", "detail": f"Upstox API returned HTTP {r.status_code}."}

    if "days_until_expiry" in out and out["days_until_expiry"] <= WARN_DAYS:
        return {**out, "status": "expiring_soon",
                "detail": f"Upstox token expires in {out['days_until_expiry']} days."}
    return {**out, "status": "ok"}


CHECKS = {"upstox": check_upstox}
_OK = {"ok", "not_configured"}


def _log_transition(name: str, result: dict) -> None:
    status = result["status"]
    now = time.monotonic()
    with _lock:
        prev = _last_status.get(name)
        _last_status[name] = status
        due = now - _last_warned.get(name, 0) > REWARN_SECONDS
        if status != "ok" and (prev != status or due):
            _last_warned[name] = now
            level = logging.WARNING if status in ("expiring_soon", "not_configured") else logging.ERROR
            logger.log(level, "PROVIDER HEALTH %s: %s — %s", name, status, result.get("detail", ""))
        elif status == "ok" and prev not in (None, "ok"):
            logger.info("PROVIDER HEALTH %s recovered (was %s)", name, prev)


def provider_health(refresh: bool = False) -> dict:
    """{name: result}. Cached for a few minutes unless refresh=True."""
    out = {}
    now = time.monotonic()
    for name, fn in CHECKS.items():
        with _lock:
            hit = _cache.get(name)
        if hit and not refresh and now - hit[0] < CACHE_SECONDS:
            out[name] = hit[1]
            continue
        try:
            result = fn()
        except Exception as e:  # a broken probe must never take down /ready
            result = {"provider": name, "status": "degraded", "detail": f"health probe failed: {e}"}
        with _lock:
            _cache[name] = (time.monotonic(), result)
        _log_transition(name, result)
        out[name] = result
    return out


def overall(results: dict) -> str:
    return "ok" if all(r["status"] in _OK for r in results.values()) else "degraded"


def start_monitor() -> threading.Event:
    """Background thread: re-check every hour so expiry/revocation is logged without traffic."""
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            try:
                provider_health(refresh=True)
            except Exception:
                logger.exception("provider monitor failed")
            stop.wait(MONITOR_EVERY)

    threading.Thread(target=loop, daemon=True, name="provider-monitor").start()
    return stop
