# ◈ StockPicker Terminal

> AI-powered investment research and paper trading platform for Indian (NSE/BSE) and US (NYSE/NASDAQ) markets.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57+-red?style=flat-square&logo=streamlit)
![CrewAI](https://img.shields.io/badge/CrewAI-Multi--Agent-purple?style=flat-square)
![Claude](https://img.shields.io/badge/Claude-Haiku%20%7C%20Sonnet-orange?style=flat-square)
![Supabase](https://img.shields.io/badge/Supabase-Auth-green?style=flat-square&logo=supabase)

---

## What It Does

StockPicker Terminal runs a team of 4 AI agents that research, analyse, and score stocks across Indian and US markets. It then lets you track picks and simulate trades in a paper portfolio — all from a single dark-themed web app.

**4-Agent Pipeline**
1. **Researcher** — collects fundamentals, price data, 52-week range, news
2. **Technical Analyst** — calculates RSI, MACD, Bollinger Bands, EMA, ATR
3. **Sentiment Analyst** — scores news sentiment, flags red flags and catalysts
4. **Master Analyst** — applies a strict quality gate and outputs only Medium/High confidence Bullish picks as JSON

**Quality Gate** — picks are automatically rejected if:
- RSI > 75 (overbought) or < 25 (freefall)
- Triple bearish signal (EMA + MACD + RSI all down)
- Debt-to-Equity > 3
- Negative revenue growth
- Active legal/regulatory issues
- Low confidence → never recommended

---

## Features

| Feature | Details |
|---|---|
| 🤖 AI Analysis | 4-agent CrewAI pipeline powered by Claude |
| 📊 Stock Detail | Price chart, Technicals tab, News tab, Events tab |
| 💼 Paper Trading | Add/sell positions with live P&L, custom entry price |
| 🔐 Auth | Supabase email login, account types (Admin/Premium/Free/Guest) |
| 👥 Multi-user | Each user sees only their own portfolio |
| 🛡 Admin Dashboard | User management, API cost tracking, all activity |
| 📅 Auto-Scheduler | Weekly crew runs on a configurable day/time |
| 📈 Live Ticker | Animated stock ticker tape (India/US) |
| 🌐 Market Status | Real-time NSE/BSE and NYSE/NASDAQ open/close indicator |

---

## Tech Stack

```
Frontend     Streamlit + custom CSS (dark terminal UI)
AI Agents    CrewAI + Anthropic Claude (Haiku for analysis, Sonnet for complex tasks)
Data         yfinance (prices, fundamentals, news, events)
             pandas-ta (technical indicators)
             Finnhub (supplementary data)
Auth         Supabase (email/password, JWT sessions)
Database     SQLite (local) via SQLAlchemy
Scheduler    APScheduler (background weekly runs)
Charts       Plotly (interactive price charts)
```

---

## Project Structure

```
stock-picker-agent/
├── src/
│   ├── agents/
│   │   ├── agents.py              # 4 CrewAI agent definitions
│   │   ├── tasks.py               # Task prompts with strict quality gate
│   │   ├── crew.py                # Orchestrator + API cost logging
│   │   └── portfolio_analyzer.py  # Per-position AI analysis
│   ├── tools/
│   │   ├── stock_data.py          # yfinance fundamentals
│   │   ├── news_sentiment.py      # News + sentiment scoring
│   │   └── technical_indicators.py # RSI, MACD, BB, EMA, ATR
│   ├── data/
│   │   └── stock_universe.py      # ~200 tickers, India+US, by sector/size
│   ├── database/
│   │   ├── models.py              # SQLite schema (UserProfile, Pick, Portfolio, etc.)
│   │   └── paper_trading.py       # Portfolio CRUD with user isolation
│   ├── auth/
│   │   └── supabase_auth.py       # Supabase sign-up, sign-in, guest
│   ├── ui/
│   │   ├── app.py                 # Main Streamlit app
│   │   ├── login_page.py          # Login / Register / Guest UI
│   │   ├── admin_page.py          # Admin dashboard
│   │   └── stock_detail.py        # Groww-style stock detail page
│   └── scheduler.py               # APScheduler background jobs
├── .env                           # API keys (not committed)
├── scheduler_settings.json        # Auto-scheduler config (not committed)
├── railway.toml                   # Railway deployment config
├── Procfile                       # Alternative deployment
└── pyproject.toml
```

---

## Quickstart

### 1. Clone & install

```bash
git clone https://github.com/Akshxt1/stock-picker-agent.git
cd stock-picker-agent
uv sync
```

Or with pip:
```bash
pip install -r requirements.txt
```

### 2. Set up environment

Create a `.env` file in the project root:

```env
# Anthropic (required)
ANTHROPIC_API_KEY=sk-ant-...

# Supabase (required for auth)
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_ANON_KEY=eyJ...

# Finnhub (optional, improves data quality)
FINNHUB_API_KEY=...
```

### 3. Supabase setup (5 minutes)

1. Create a free project at [supabase.com](https://supabase.com)
2. Copy **Project URL** and **anon public key** from Settings → API
3. Go to **Authentication → Providers** → make sure **Email** is enabled
4. Optional: disable "Confirm email" under Authentication → Settings for local testing

### 4. Run

```bash
uv run streamlit run src/ui/app.py
```

App opens at `http://localhost:8501`

### 5. Make yourself Admin (first run)

After signing up, run this once:

```bash
uv run python make_admin.py
```

Or replace `YOUR_EMAIL` and run:

```python
# make_admin.py
from src.database.models import init_db, Session, UserProfile
init_db()
s = Session()
user = s.query(UserProfile).filter(UserProfile.email == "YOUR_EMAIL").first()
if user:
    user.account_type = "admin"
    s.commit()
    print(f"✅ {user.name} is now Admin")
s.close()
```

---

## Account Types

| Type | Analysis Runs | Portfolio | Admin Dashboard | Scheduler |
|---|---|---|---|---|
| **Admin** | Unlimited | Own only | ✓ Full access | ✓ |
| **Premium** | Unlimited | Own only | ✗ | ✓ |
| **Free** | 3 / week | Own only | ✗ | ✗ |
| **Guest** | None (read-only) | ✗ | ✗ | ✗ |

---

## Running an Analysis

1. Click **▶ Run** in the sidebar
2. Select Market (India / US), Sector, and Cap Size
3. Click **🚀 Launch Crew**
4. Wait 2–4 minutes while 4 agents work in sequence
5. Results appear under Recent Picks — only stocks that pass all quality gates

---

## Deployment

### Oracle Cloud Free Tier (static IP for IIFL)

Use this when you need a stable server IP for IIFL API whitelisting:

```text
docs/oracle-cloud-deploy.md
```

### Keep-alive (free — Streamlit Community Cloud)

1. Deploy on [share.streamlit.io](https://share.streamlit.io) → set main file to `src/ui/app.py`
2. Add secrets in the Streamlit dashboard (same keys as `.env`)
3. Sign up at [uptimerobot.com](https://uptimerobot.com) → add your app URL with a 5-minute ping interval

### Always-on (Railway ~$5/month)

```bash
# Files already included: railway.toml, Procfile
git push  # Railway auto-deploys from GitHub
```

Set environment variables in Railway dashboard → Variables tab.

For SQLite persistence on Railway: Settings → Add Volume → mount at `/app/src/database`

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Claude API key (get at console.anthropic.com) |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Supabase anonymous/public key |
| `FINNHUB_API_KEY` | Optional | Improves news and fundamental data |
| `IIFL_APP_KEY` | Optional | IIFL app key for India market-data provider |
| `IIFL_APP_SECRET_KEY` | Optional | IIFL app secret; keep server-side only |
| `TWELVE_DATA_API_KEY` | Optional | Twelve Data fallback for quote/history |
| `ALPHA_VANTAGE_API_KEY` | Optional | Alpha Vantage fallback for quote/history |

### Market Data Provider Order

The app now routes quote, history, and fundamentals requests through a provider layer with SQLite caching. Override provider order with comma-separated environment variables:

```env
INDIA_QUOTE_PROVIDER_ORDER=iifl,yfinance,twelvedata,alphavantage
INDIA_HISTORY_PROVIDER_ORDER=iifl,yfinance,twelvedata,alphavantage
INDIA_FUNDAMENTALS_PROVIDER_ORDER=yfinance,alphavantage
US_QUOTE_PROVIDER_ORDER=yfinance,twelvedata,alphavantage
US_HISTORY_PROVIDER_ORDER=yfinance,twelvedata,alphavantage
US_FUNDAMENTALS_PROVIDER_ORDER=yfinance,alphavantage
```

IIFL credentials can be stored now, but the IIFL provider remains disabled for data calls until its exact auth and market-data endpoints are mapped from the developer docs.

---

## Database Schema

| Table | Purpose |
|---|---|
| `user_profiles` | Mirrors Supabase auth, stores account_type |
| `picks` | AI-generated stock recommendations |
| `portfolio` | Paper trading positions (per user) |
| `transactions` | Buy/sell history |
| `api_usage` | API cost tracking per user/run |

---

## Screenshots

> Dashboard with live ticker tape and market status

> Stock detail page — Chart, Technicals, News, Events tabs (Groww-style)

> Admin dashboard — user management, per-user API cost breakdown

---

## Known Limitations

- **yfinance rate limits** — the app retries automatically but data may occasionally show `—` during market hours when rate limits are hit
- **SQLite on cloud** — SQLite works locally and on Railway with a volume. For high-traffic use, migrate to Supabase PostgreSQL
- **Streamlit session** — Streamlit Community Cloud puts apps to sleep after inactivity; use UptimeRobot to prevent this
- **Paper trading only** — no real brokerage integration; prices are from yfinance and may have a 15-minute delay

---

## Contributing

Pull requests welcome. For major changes, open an issue first.

```bash
git checkout -b feature/your-feature
git commit -m "feat: describe your change"
git push origin feature/your-feature
```

---

## Disclaimer

This tool is for **educational and research purposes only**. Nothing in this app constitutes financial advice. Always do your own research before investing. Past AI picks are not a guarantee of future performance.

---

## License

MIT © 2026 Akshat Gupta
