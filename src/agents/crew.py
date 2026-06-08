# src/agents/crew.py  (updated — logs API cost per user)

import json, re
from datetime import datetime
from crewai import Crew, Process
from src.agents.tasks import create_tasks
from src.data.stock_universe import get_stocks


def run_stock_picker(market: str, sector: str, size: str,
                     user_id: str = None, username: str = None) -> dict:
    print(f"\n{'='*60}")
    print(f"  {market} | {sector} | {size} Cap  —  by {username or 'system'}")
    print(f"{'='*60}\n")

    tickers = get_stocks(market, sector, size)
    if not tickers:
        return {"error": f"No tickers for {market}/{sector}/{size}",
                "market": market, "sector": sector, "size": size}

    print(f"  Tickers ({len(tickers)}): {tickers}\n")
    task_r, task_t, task_s, task_m, agents = create_tasks(market, sector, size, tickers)

    crew = Crew(
        agents=[agents["researcher"], agents["data_analyst"],
                agents["sentiment_analyst"], agents["master_analyst"]],
        tasks=[task_r, task_t, task_s, task_m],
        process=Process.sequential, verbose=True,
    )

    result = crew.kickoff()

    # ── Log usage ─────────────────────────────────────────────────────────────
    if user_id or username:
        try:
            from src.database.models import log_api_usage
            usage = result.token_usage if hasattr(result, "token_usage") else None
            if usage:
                log_api_usage(
                    user_id       = user_id or "",
                    username      = username or "system",
                    model         = "claude-haiku-4-5-20251001",
                    input_tokens  = getattr(usage, "prompt_tokens", 0),
                    output_tokens = getattr(usage, "completion_tokens", 0),
                    agent         = "full_crew",
                    run_context   = f"{market} · {sector} · {size}",
                )
        except Exception as e:
            print(f"  [cost log] {e}")

    raw    = str(result.raw)
    parsed = _extract_json(raw)
    if parsed:
        print(f"\n  ✓ {len(parsed.get('picks',[]))} picks found.")
        return parsed
    return {"market": market, "sector": sector, "size": size,
            "analysis_date": datetime.today().strftime("%Y-%m-%d"),
            "raw_output": raw, "picks": [],
            "error": "JSON parsing failed"}


def _extract_json(text: str) -> dict | None:
    try: return json.loads(text.strip())
    except json.JSONDecodeError: pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except json.JSONDecodeError: pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except json.JSONDecodeError: pass
    return None


def run_full_market_scan(market: str, sectors=None, sizes=None,
                          user_id=None, username=None) -> list:
    from src.data.stock_universe import get_all_sectors, get_all_sizes
    sectors = sectors or get_all_sectors(market)
    sizes   = sizes   or get_all_sizes(market)
    results = []
    for sector in sectors:
        for size in sizes:
            results.append(run_stock_picker(market, sector, size,
                                             user_id=user_id, username=username))
    return results