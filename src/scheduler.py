# src/scheduler.py

import time
import schedule
from datetime import datetime
from src.database.models import Session, SystemSettings
from src.agents.crew import run_full_market_scan

def job():
    print(f"[{datetime.now()}] Running scheduled market scan...")
    
    # Read settings dynamically from Database instead of ephemeral JSON
    with Session() as sess:
        setting = sess.query(SystemSettings).filter(SystemSettings.key == "scheduler_config").first()
        if not setting or not setting.value:
            print("No configuration found in DB.")
            return
        config = setting.value

    if not config.get("enabled"):
        print("Scheduler is disabled in configuration.")
        return

    markets = config.get("markets", ["INDIA", "US"])
    sizes = config.get("sizes", ["Large", "Mid"])
    
    for mkt in markets:
        sectors = config.get(f"{mkt.lower()}_sectors", [])
        if not sectors:
            from src.data.stock_universe import INDIAN_STOCKS, US_STOCKS
            sectors = list(INDIAN_STOCKS.keys()) if mkt == "INDIA" else list(US_STOCKS.keys())
        
        # Run the massive scan (the agent crew handles the API rate limiting internally)
        run_full_market_scan(market=mkt, sectors=sectors, sizes=sizes, username="AutoScheduler")
    
    # Update last run time in the database
    config["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with Session() as sess:
        setting = sess.query(SystemSettings).filter(SystemSettings.key == "scheduler_config").first()
        if setting:
            setting.value = config
            sess.commit()

def get_scheduler():
    """Returns the configured schedule object based on DB settings"""
    schedule.clear()
    
    with Session() as sess:
        setting = sess.query(SystemSettings).filter(SystemSettings.key == "scheduler_config").first()
        if not setting or not setting.value:
            return schedule
        config = setting.value

    if config.get("enabled"):
        day = config.get("day", "mon").lower()
        hour = str(config.get("hour", 6)).zfill(2)
        minute = str(config.get("minute", 0)).zfill(2)
        time_str = f"{hour}:{minute}"

        day_map = {
            "mon": schedule.every().monday, "tue": schedule.every().tuesday,
            "wed": schedule.every().wednesday, "thu": schedule.every().thursday,
            "fri": schedule.every().friday, "sat": schedule.every().saturday,
            "sun": schedule.every().sunday,
        }
        
        job_schedule = day_map.get(day, schedule.every().monday)
        job_schedule.at(time_str).do(job)
        print(f"Scheduled for {day.title()} at {time_str}")

    return schedule

def start_worker():
    """
    Run this as a standalone worker process on your cloud host.
    Command: `uv run python src/scheduler.py`
    """
    print("Starting Auto-Scheduler Worker Process...")
    while True:
        s = get_scheduler()
        s.run_pending()
        time.sleep(60) # Sleeps 60s (Prevents massive CPU drain while waiting)

if __name__ == "__main__":
    start_worker()# src/scheduler.py

import time
import schedule
from datetime import datetime
from src.database.models import Session, SystemSettings
from src.agents.crew import run_full_market_scan

def job():
    print(f"[{datetime.now()}] Running scheduled market scan...")
    
    # Read settings dynamically from Database instead of ephemeral JSON
    with Session() as sess:
        setting = sess.query(SystemSettings).filter(SystemSettings.key == "scheduler_config").first()
        if not setting or not setting.value:
            print("No configuration found in DB.")
            return
        config = setting.value

    if not config.get("enabled"):
        print("Scheduler is disabled in configuration.")
        return

    markets = config.get("markets", ["INDIA", "US"])
    sizes = config.get("sizes", ["Large", "Mid"])
    
    for mkt in markets:
        sectors = config.get(f"{mkt.lower()}_sectors", [])
        if not sectors:
            from src.data.stock_universe import INDIAN_STOCKS, US_STOCKS
            sectors = list(INDIAN_STOCKS.keys()) if mkt == "INDIA" else list(US_STOCKS.keys())
        
        # Run the massive scan (the agent crew handles the API rate limiting internally)
        run_full_market_scan(market=mkt, sectors=sectors, sizes=sizes, username="AutoScheduler")
    
    # Update last run time in the database
    config["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with Session() as sess:
        setting = sess.query(SystemSettings).filter(SystemSettings.key == "scheduler_config").first()
        if setting:
            setting.value = config
            sess.commit()

def get_scheduler():
    """Returns the configured schedule object based on DB settings"""
    schedule.clear()
    
    with Session() as sess:
        setting = sess.query(SystemSettings).filter(SystemSettings.key == "scheduler_config").first()
        if not setting or not setting.value:
            return schedule
        config = setting.value

    if config.get("enabled"):
        day = config.get("day", "mon").lower()
        hour = str(config.get("hour", 6)).zfill(2)
        minute = str(config.get("minute", 0)).zfill(2)
        time_str = f"{hour}:{minute}"

        day_map = {
            "mon": schedule.every().monday, "tue": schedule.every().tuesday,
            "wed": schedule.every().wednesday, "thu": schedule.every().thursday,
            "fri": schedule.every().friday, "sat": schedule.every().saturday,
            "sun": schedule.every().sunday,
        }
        
        job_schedule = day_map.get(day, schedule.every().monday)
        job_schedule.at(time_str).do(job)
        print(f"Scheduled for {day.title()} at {time_str}")

    return schedule

def start_worker():
    """
    Run this as a standalone worker process on your cloud host.
    Command: `uv run python src/scheduler.py`
    """
    print("Starting Auto-Scheduler Worker Process...")
    while True:
        s = get_scheduler()
        s.run_pending()
        time.sleep(60) # Sleeps 60s (Prevents massive CPU drain while waiting)

if __name__ == "__main__":
    start_worker()