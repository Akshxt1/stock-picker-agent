# ◈ The Great Ponzi — AI Stock Picker

> AI-powered investment research and paper-trading platform for Indian (NSE/BSE) and US (NYSE/NASDAQ) markets.
> **FastAPI** backend + **Next.js** frontend, driven by a 4-agent **CrewAI** pipeline on **Claude**.

![Python](https://img.shields.io/badge/Python-3.13+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=nextdotjs)
![CrewAI](https://img.shields.io/badge/CrewAI-Multi--Agent-purple?style=flat-square)
![Claude](https://img.shields.io/badge/Claude-Haiku%20%7C%20Sonnet-orange?style=flat-square)
![Supabase](https://img.shields.io/badge/Supabase-Auth-3ECF8E?style=flat-square&logo=supabase)

---

## What It Does

A team of 4 AI agents researches, analyses, and scores stocks across Indian and US markets, then lets you track picks and run a paper portfolio — all from a dark-themed Next.js web app talking to a FastAPI backend.

### The 4-Agent Pipeline
1. **Researcher** — discovers tickers and collects fundamentals, price/momentum, 52-week range, and news
2. **Data Analyst** — computes RSI, MACD, Bollinger Bands, EMA 20/50, ATR and a technical score
3. **Sentiment Analyst** — scores news sentiment, flags red flags and catalysts
4. **Master Analyst (CEO)** — applies a strict quality gate and emits only Medium/High-confidence picks as JSON, each with a `why_buy` / `why_not_buy` brief

**Quality gate** auto-rejects: RSI > 75 or < 25 · triple-bearish (EMA + MACD + RSI down) · Debt/Equity > 3 · negative revenue growth · active legal/regulatory issues · low confidence.

---

## Features

| Feature | Details |
|---|---|
| 🤖 AI Stock Picker | 4-agent CrewAI pipeline, streamed live to the UI via SSE |
| 🔬 Deep Analysis | Run the full crew on a single stock on demand (counts toward your quota) |
| 📈 Live Dashboard | Live NIFTY / SENSEX / S&P 500 / NASDAQ index cards, market-aware Top Movers & News (IND / US / Both) |
| 📊 Stock Detail | Price chart + AI Analysis · Technicals · News · Events tabs (Groww/INDmoney-style) |
| 💼 Portfolio | Hero summary (value / invested / returns), per-holding live P&L & analysis, IND/US/All tabs, live ₹⇄$ FX toggle |
| 🌍 Market Scoping | India runs stay on the India page, US on the US page — no cross-leak |
| 🔐 Auth & Isolation | Supabase JWT login; each user sees only their own picks & portfolio |
| 🧾 Run Attribution + Dedup | Picks tagged with who ran them; same-combo same-day runs replace rather than duplicate |
| 🛡 Admin Dashboard | User management, per-user API cost tracking, run log (admin-only) |
| 🔢 Account Quotas | Weekly crew-run and deep-analysis limits per account type |

---

## Tech Stack

```
Frontend     Next.js 14 (App Router) · React · Tailwind · Radix UI · Recharts
Backend      FastAPI · Uvicorn · Server-Sent Events (live agent stream)
AI Agents    CrewAI + Anthropic Claude (Haiku for analysis, Sonnet for the CEO decision)
Market Data  Finnhub (US) · yfinance (India + fallback) · TwelveData / Alpha Vantage (fallback)
             pandas-ta (technical indicators)
Auth         Supabase (email/password, JWT)
Database     SQLite (local) / Supabase Postgres (prod) via SQLAlchemy, with a market-data cache
```

Market data flows through a cached multi-provider layer (`src/providers/market_data.py`): **US → Finnhub → yfinance**, **India → yfinance → TwelveData → Alpha Vantage**. (IIFL's legacy API was decommissioned and removed from the chain.)

---

## Project Structure

```
stock-picker-agent/
├── src/
│   ├── api/                     # FastAPI backend
│   │   ├── main.py              # app + router registration
│   │   └── routes/
│   │       ├── auth.py          # Supabase login / current-user dependency
│   │       ├── crew.py          # SSE: market-scan + single-stock deep analysis
│   │       ├── stock.py         # quote / history / technicals / news / events / ai
│   │       ├── portfolio.py     # holdings + per-holding & whole-portfolio analysis
│   │       ├── market.py        # status / indices / movers / news / fx
│   │       ├── picks.py         # saved picks (per user)
│   │       ├── universe.py      # sectors & sizes
│   │       └── admin.py         # admin-only: users, usage, runs, logs
│   ├── agents/
│   │   ├── agents.py            # 4 CrewAI agent definitions
│   │   ├── tasks.py             # market-scan + single-stock task pipelines
│   │   └── crew.py              # orchestrator + JSON extraction + cost logging
│   ├── tools/                   # CrewAI tools: stock data, news, technicals, discovery
│   ├── providers/               # cached multi-provider market-data layer
│   ├── data/stock_universe.py   # sectors / cap-size buckets
│   └── database/                # SQLAlchemy models + paper-trading logic
├── frontend/                    # Next.js app (app/, components/, lib/)
├── railway.toml                 # Railway deploy (runs the FastAPI app)
├── run_api.ps1                  # local dev: uvicorn with --reload-dir src
└── pyproject.toml
```

---

## Quickstart

### 1. Backend

```bash
git clone https://github.com/Akshxt1/stock-picker-agent.git
cd stock-picker-agent
uv sync                       # install Python deps from uv.lock
```

Create a `.env` in the project root (see `.env.example`):

```env
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...      # admin user management
FINNHUB_API_KEY=...                   # US quotes/fundamentals/news
# optional fallbacks
TWELVE_DATA_API_KEY=...
ALPHA_VANTAGE_API_KEY=...
```

Run the API (Windows PowerShell helper keeps reloads scoped to `src/`):

```powershell
./run_api.ps1
```

Or directly:

```bash
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src
```

> ⚠️ Always use `--reload-dir src`. Plain `--reload` also watches `frontend/.next/`, which the Next.js dev server rewrites constantly — that thrashes the reloader and serves stale routes.

API runs at `http://localhost:8000` (`/docs` for the OpenAPI UI).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App opens at `http://localhost:3000`. It expects the API at `http://localhost:8000` (override via `NEXT_PUBLIC_API_URL`).

### 3. Supabase setup (5 minutes)

1. Create a free project at [supabase.com](https://supabase.com)
2. Copy **Project URL**, **anon public key**, and **service_role key** from Settings → API
3. Authentication → Providers → enable **Email**
4. (Local testing) Authentication → Settings → optionally disable "Confirm email"

The admin account is bootstrapped by email (`akshatgupta428@gmail.com`); change `ADMIN_EMAIL` in `src/api/routes/auth.py` and `admin.py` to your own.

---

## Account Types & Limits

| Type | Crew Runs / week | Deep + Portfolio Analyses / week | Admin Dashboard |
|---|---|---|---|
| **Admin** | Unlimited | Unlimited | ✓ |
| **Premium** | 5 | 5 | ✗ |
| **Trial** | 2 | 3 | ✗ |
| **Guest** | None (read-only) | None | ✗ |

- **Crew run** = a market scan (Researcher → … → CEO across a sector/size).
- **Deep/portfolio analysis** = full-crew analysis of one stock, or an "Analyze Portfolio" sweep. Both draw from the same weekly quota. The quick per-holding verdict is free.

---

## Running an Analysis

1. Go to **IND Market** or **US Market** (or the Dashboard picker)
2. Pick a Sector and Cap Size, hit **Run Analysis**
3. Watch the 4 agents work live in the activity timeline
4. Passing stocks render as clickable cards → open one for chart, technicals, news, events, and the AI brief
5. On any stock page, hit **Run Deep Analysis** to run the full crew on just that ticker

---

## Key API Endpoints

```
GET  /api/crew/stream?market=&sector=&size=     # SSE market scan
GET  /api/crew/stock-stream?ticker=             # SSE single-stock deep analysis
GET  /api/stock/{ticker}/quote|history|technicals|news|events|ai
GET  /api/market/status|indices|movers|news|fx
GET  /api/picks?market=                         # current user's saved picks
GET  /api/portfolio?market=                     # holdings w/ live price + P&L
POST /api/portfolio/{id}/analyze                # quick per-holding verdict
POST /api/portfolio/analyze-all                 # analyze whole portfolio (1 quota run)
GET  /api/admin/users|usage|runs|logs           # admin only
```

All protected routes require a Supabase `Authorization: Bearer <jwt>` header.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Claude API key |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Admin user management |
| `FINNHUB_API_KEY` | Recommended | US quotes, fundamentals, company news |
| `TWELVE_DATA_API_KEY` | Optional | Quote/history fallback |
| `ALPHA_VANTAGE_API_KEY` | Optional | Quote/history fallback |
| `DATABASE_URL` | Optional | Postgres URL for prod (defaults to local SQLite) |
| `NEXT_PUBLIC_API_URL` | Optional | Frontend → API base URL (defaults to `http://localhost:8000`) |

### Provider order overrides

```env
US_QUOTE_PROVIDER_ORDER=finnhub,yfinance,twelvedata,alphavantage
INDIA_QUOTE_PROVIDER_ORDER=yfinance,twelvedata,alphavantage
# …also *_HISTORY_PROVIDER_ORDER and *_FUNDAMENTALS_PROVIDER_ORDER
```

---

## Database Schema

| Table | Purpose |
|---|---|
| `user_profiles` | Mirrors Supabase auth; account_type + weekly run counters |
| `picks` | AI-generated recommendations (per user, with attribution) |
| `portfolio` | Paper-trading positions + saved per-holding analysis |
| `transactions` | Buy/sell history |
| `api_usage` | Token usage & cost per user/run |
| `market_data_cache` | Cached provider responses (quote/history/fundamentals) |

---

## Deployment

The backend deploys on **Railway** (config in `railway.toml`):

```toml
[deploy]
startCommand = "uvicorn src.api.main:app --host 0.0.0.0 --port $PORT"
```

Set the env vars in Railway → Variables. For SQLite persistence, add a Volume mounted at `/app/src/database` (or set `DATABASE_URL` to a Supabase Postgres connection string). Deploy the `frontend/` separately (e.g. Vercel) with `NEXT_PUBLIC_API_URL` pointing at the API.

---

## Known Limitations

- **yfinance rate limits** — the provider layer retries and falls back, but Indian data may briefly show `—` during peak hours.
- **Finnhub free tier** — covers US fully; Indian (NSE) symbols 403, so India stays on yfinance. Finnhub daily candles are paid-tier, so history uses yfinance.
- **SQLite on cloud** — fine locally and on Railway with a volume; for higher traffic migrate to Supabase Postgres via `DATABASE_URL`.
- **Paper trading only** — no brokerage integration; prices may be ~15 min delayed.

---

## Disclaimer

For **educational and research purposes only**. Nothing here is financial advice. Always do your own research. Past AI picks do not guarantee future performance.

---

## License

MIT © 2026 Akshat Gupta
