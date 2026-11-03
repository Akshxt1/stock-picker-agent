"""
src/api/main.py  — FastAPI backend
Run locally:  uvicorn src.api.main:app --reload --port 8000
Railway:      uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.database.models import init_db
from src.api.logging_config import configure_logging
from src.api.ratelimit import RateLimitMiddleware

from src.api.routes.crew      import router as crew_router
from src.api.routes.picks     import router as picks_router
from src.api.routes.portfolio import router as portfolio_router
from src.api.routes.auth      import router as auth_router
from src.api.routes.market    import router as market_router
from src.api.routes.universe  import router as universe_router
from src.api.routes.admin     import router as admin_router
from src.api.routes.stock     import router as stock_router
from src.api.routes.assets    import router as assets_router

# ── Logging ───────────────────────────────────────────────────────────────────

configure_logging()
logger = logging.getLogger("stockpicker")

# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.database.models import engine
    init_db()
    # Print (not just log) so the active DB backend is always visible in host
    # logs — confirms Postgres vs. the ephemeral SQLite dev fallback.
    print(f"StockPicker API started — DB backend: {engine.url.get_backend_name()} "
          f"(host={engine.url.host or 'local file'})", flush=True)
    stop_workers = None
    if os.getenv("JOB_WORKER_MODE", "embedded").lower() == "embedded":
        from src.jobs.worker import start_embedded_workers
        stop_workers = start_embedded_workers()
    stop_monitor = None
    if os.getenv("PROVIDER_MONITOR", "true").lower() not in ("0", "false", "no"):
        from src.providers.health import start_monitor
        stop_monitor = start_monitor()
    yield
    if stop_workers:
        stop_workers.set()
    if stop_monitor:
        stop_monitor.set()

app = FastAPI(title="StockPicker API", version="2.1.0", lifespan=lifespan)

# ── CORS ──────────────────────────────────────────────────────────────────────

_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in _raw.split(",") if o.strip()]

# A wildcard origin cannot be combined with credentialed requests — browsers
# reject it and it's a security foot-gun. Fail safe by disabling credentials
# in that case rather than silently shipping a broken/insecure CORS policy.
_allow_credentials = "*" not in origins
if not _allow_credentials:
    logger.warning("ALLOWED_ORIGINS contains '*'; disabling credentialed CORS. "
                   "Set explicit origins in production.")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(auth_router,      prefix="/api/auth")
app.include_router(crew_router,      prefix="/api/crew")
app.include_router(picks_router,     prefix="/api/picks")
app.include_router(portfolio_router, prefix="/api/portfolio")
app.include_router(market_router,    prefix="/api/market")
app.include_router(universe_router,  prefix="/api/universe")
app.include_router(admin_router,     prefix="/api/admin")
app.include_router(stock_router,     prefix="/api/stock")
app.include_router(assets_router,    prefix="/api/assets")


@app.get("/")
def root():
    return {"status": "ok", "service": "StockPicker API v2"}


@app.get("/health")
def health():
    """Liveness: the process is up. Never touches the DB, so it can't flap."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness: the DB answers and the job queue is readable.

    Data providers are reported but never fail readiness (the app falls back to other
    sources); `data_status` turns "degraded" when e.g. the Upstox token is dead.
    """
    from sqlalchemy import text, func
    from src.database.models import Session, Job
    try:
        with Session() as sess:
            sess.execute(text("SELECT 1"))
            queued = sess.query(func.count(Job.id)).filter(Job.status == "queued").scalar()
    except Exception as e:
        logger.error("readiness check failed: %s", e)
        return JSONResponse({"status": "unavailable"}, status_code=503)
    from src.providers.health import provider_health, overall
    providers = provider_health()
    return {"status": "ready", "queued_jobs": queued,
            "data_status": overall(providers), "providers": providers}
