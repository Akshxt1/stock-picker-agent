# Deployment

The backend is a single container image (`Dockerfile`) that runs anywhere Docker runs. It needs one thing
from the host: a **persistent Postgres** `DATABASE_URL`. In `APP_ENV=production` the app refuses to start
without it, so a misconfigured host fails loudly instead of quietly losing data on throwaway SQLite.

## Architecture

```
Vercel (Next.js)  ──►  API container (FastAPI, embedded job workers)  ──►  Postgres
                                  └─ optional: separate worker container(s)
```

- AI runs are **jobs** stored in Postgres (`jobs`, `job_events`). The API enqueues; a worker executes and
  writes progress events; the SSE endpoint replays them. A dropped connection or API restart no longer
  kills a run: reconnect with `GET /api/crew/jobs/{id}/stream`, or poll `GET /api/crew/jobs/{id}`.
- Workers heartbeat; a job whose worker died is re-queued once, then failed with the quota refunded.
- Weekly quotas are claimed with a single atomic `UPDATE`, so concurrent requests cannot overshoot them.
- Schema changes go through Alembic (`alembic/versions`). Migrations run automatically on startup.
  Create a new one with `uv run alembic revision -m "what changed"`.

## Run locally with Docker

```bash
cp .env.example .env        # fill in keys
docker compose up --build   # Postgres + API (embedded workers) on :8000
```

Scale AI throughput with dedicated workers:

```bash
JOB_WORKER_MODE=external docker compose --profile worker up --build --scale worker=2
```

## Hosting options (no Oracle / GCP needed)

| Option | Notes |
|---|---|
| **Neon** or **Supabase** (Postgres) | Free tiers. Supabase pauses idle free projects — keep it warm or use Neon. |
| **Hugging Face Spaces / Koyeb / Render** (API container) | Free tiers sleep when idle; fine because jobs live in Postgres. Set `PORT` if the host does not. |
| **Hetzner Cloud VPS** (~€4/mo) | Most dependable. Install Docker, `docker compose up -d`, put Caddy in front for HTTPS. Accepts ordinary cards/PayPal. |

Set `TRUST_PROXY=true` when behind a reverse proxy so rate limiting sees the real client IP.

## Health checks

- `GET /health` — liveness (no DB access).
- `GET /ready` — readiness: DB reachable, reports queued job count. Point the platform's health check at `/health`
  and your uptime monitor at `/ready`.

## Backups

Free database tiers can pause, expire, or be deleted when a subscription lapses. Take a nightly dump to storage
you control:

```bash
pg_dump "$DATABASE_URL" | gzip > stockpicker-$(date +%F).sql.gz
```

Run it from a GitHub Actions cron, or a host cron job, and upload to any object storage. Test a restore once.
