# src/agents/crew.py

import json, re, time
from datetime import datetime
from crewai import Crew, Process
from src.agents.tasks import create_tasks


def run_stock_picker(market: str, sector: str, size: str,
                     user_id: str = None, username: str = None) -> dict:
    print(f"\n{'='*60}")
    print(f"  {market} | {sector} | {size} Cap  —  by {username or 'system'}")
    print(f"  Agent will discover stocks autonomously.")
    print(f"{'='*60}\n")

    # No more get_stocks() — tasks.py no longer takes a tickers argument
    task_r, task_t, task_s, task_m, agents = create_tasks(market, sector, size)

    crew = Crew(
        agents=[
            agents["researcher"],
            agents["data_analyst"],
            agents["sentiment_analyst"],
            agents["master_analyst"],
        ],
        tasks=[task_r, task_t, task_s, task_m],
        process=Process.sequential,
        verbose=True,
    )

    try:
        result = crew.kickoff()
    except Exception as e:
        print(f"  [crew error] API Failure: {e}")
        return {
            "error":  f"API Error: {str(e)}",
            "market": market,
            "sector": sector,
            "size":   size,
            "picks":  [],
        }

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
        print(f"\n  ✓ {len(parsed.get('picks', []))} picks found.")
        return parsed

    return {
        "market":        market,
        "sector":        sector,
        "size":          size,
        "analysis_date": datetime.today().strftime("%Y-%m-%d"),
        "raw_output":    raw,
        "picks":         [],
        "error":         "JSON parsing failed — LLM output was not valid JSON.",
    }


def _extract_json(text: str) -> dict | None:
    if not text:
        return None

    # Attempt direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Find outermost { } boundaries
    first_brace = text.find("{")
    last_brace  = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    # Fallback: extract from markdown code block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    return None


def run_full_market_scan(market: str, sectors=None, sizes=None,
                         user_id=None, username=None) -> list:
    # Import sector/size helpers — stock_universe.py can still hold these
    # even though it no longer provides per-sector ticker lists
    try:
        from src.data.stock_universe import get_all_sectors, get_all_sizes
        sectors = sectors or get_all_sectors(market)
        sizes   = sizes   or get_all_sizes(market)
    except ImportError:
        sectors = sectors or ["Technology", "Banking", "Pharma", "FMCG", "Auto"]
        sizes   = sizes   or ["Large", "Mid", "Small"]

    results = []
    total   = len(sectors) * len(sizes)
    count   = 0

    for sector in sectors:
        for size in sizes:
            count += 1
            print(f"\n  [{count}/{total}] {market} · {sector} · {size}")
            res = run_stock_picker(
                market, sector, size,
                user_id=user_id, username=username,
            )
            results.append(res)

            # Rate-limit between crew runs to protect Anthropic token bucket
            if count < total:
                print("  [rate limit] Sleeping 10s before next run...")
                time.sleep(10)

    return results