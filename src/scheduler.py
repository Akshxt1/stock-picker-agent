# src/scheduler.py
# Auto-scheduler using APScheduler — runs the crew on a weekly cadence.
# Called from app.py Settings page.

import json, os
from datetime import datetime
import streamlit as st

SCHED_FILE = os.path.join(os.path.dirname(__file__), "..", "scheduler_settings.json")

@st.cache_resource
def get_scheduler():
    """Single shared scheduler instance across Streamlit sessions."""
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.start()
    return scheduler

def run_scheduled_analysis():
    """The function that runs when the schedule fires."""
    from src.agents.crew import run_full_market_scan
    from src.database.paper_trading import save_picks

    print(f"\n[Scheduler] Auto-run triggered at {datetime.now()}")

    try:
        cfg     = _load_cfg()
        markets = cfg.get("markets", ["INDIA","US"])
        sizes   = cfg.get("sizes",   ["Large","Mid"]) or None

        for market in markets:
            secs = cfg.get(f"{market.lower()}_sectors") or None
            results = run_full_market_scan(market, sectors=secs, sizes=sizes)
            for r in results:
                if r.get("picks"):
                    save_picks(r)

        cfg["last_run"] = datetime.now().isoformat()
        _save_cfg(cfg)
        print(f"[Scheduler] Done. {len(markets)} markets scanned.")

    except Exception as e:
        print(f"[Scheduler] Error: {e}")

def schedule_job(scheduler, cfg: dict):
    """Register (or replace) the weekly cron job."""
    JOB_ID = "stock_picker_weekly"

    # Remove existing job if any
    if scheduler.get_job(JOB_ID):
        scheduler.remove_job(JOB_ID)

    if not cfg.get("enabled"):
        return

    from apscheduler.triggers.cron import CronTrigger
    scheduler.add_job(
        func        = run_scheduled_analysis,
        trigger     = CronTrigger(
            day_of_week = cfg.get("day",    "mon"),
            hour        = cfg.get("hour",   6),
            minute      = cfg.get("minute", 0),
        ),
        id          = JOB_ID,
        name        = "Stock Picker Weekly Scan",
        replace_existing = True,
        misfire_grace_time = 3600,   # 1 hour grace if server was down
    )
    print(f"[Scheduler] Scheduled: every {cfg['day']} at {cfg['hour']:02d}:{cfg['minute']:02d}")

def _load_cfg():
    if os.path.exists(SCHED_FILE):
        with open(SCHED_FILE) as f: return json.load(f)
    return {}

def _save_cfg(cfg):
    with open(SCHED_FILE, "w") as f: json.dump(cfg, f, indent=2)