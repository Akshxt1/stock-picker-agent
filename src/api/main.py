"""
src/api/main.py  — FastAPI backend
Run locally:  uvicorn src.api.main:app --reload --port 8000
Railway:      uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database.models import init_db

from src.api.routes.crew      import router as crew_router
from src.api.routes.picks     import router as picks_router
from src.api.routes.portfolio import router as portfolio_router
from src.api.routes.auth      import router as auth_router
from src.api.routes.market    import router as market_router
from src.api.routes.universe  import router as universe_router
from src.api.routes.admin     import router as admin_router
from src.api.routes.stock     import router as stock_router

# ── Logging to file ───────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("stockpicker")

# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.database.models import engine
    init_db()
    # Print (not just log) so the active DB backend is always visible in Railway
    # logs — confirms whether Postgres or the ephemeral SQLite fallback is in use.
    print(f"StockPicker API started — DB backend: {engine.url.get_backend_name()} "
          f"(host={engine.url.host or 'local file'})", flush=True)
    yield

app = FastAPI(title="StockPicker API", version="2.0.0", lifespan=lifespan)

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


@app.get("/")
def root():
    return {"status": "ok", "service": "StockPicker API v2"}
