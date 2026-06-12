# src/agents/crew.py

import json, re, time
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

    # PRODUCTION FIX: API Failure protection
    try:
        result = crew.kickoff()
    except Exception as e:
        print(f"  [crew error] API Failure: {e}")
        return {"error": f"API Error: {str(e)}", "market": market, "sector": sector, "size": size, "picks": []}

    # ── Log usage ─────────────────────────────────────────────────────────────
    if user_id or username:
        try:
            from src.database.models import log_api_usage
            usage = result.token_usage if hasattr(result, "token_usage") else None
            if usage:
                log_api_usage(
                    user_id       = user_id or "",
                    username      = username or "system",
                    model         = "claude-3-5-haiku-latest", # Fixed model logging
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
            "error": "JSON parsing failed due to severe LLM hallucination."}


# PRODUCTION FIX: Bulletproof JSON Extraction (Ignores conversational filler)
def _extract_json(text: str) -> dict | None:
    if not text: return None
    
    # Attempt direct parse first
    try: return json.loads(text.strip())
    except json.JSONDecodeError: pass
    
    # Mathematical boundary extraction (Finds outer {} brackets)
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            json_str = text[first_brace:last_brace+1]
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
    # Fallback to aggressive regex
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except json.JSONDecodeError: pass
        
    return None


def run_full_market_scan(market: str, sectors=None, sizes=None,
                          user_id=None, username=None) -> list:
    from src.data.stock_universe import get_all_sectors, get_all_sizes
    sectors = sectors or get_all_sectors(market)
    sizes   = sizes   or get_all_sizes(market)
    results = []
    
    # PRODUCTION FIX: Rate limiting to prevent Anthropic 429 Bans
    for i, sector in enumerate(sectors):
        for j, size in enumerate(sizes):
            res = run_stock_picker(market, sector, size, user_id=user_id, username=username)
            results.append(res)
            
            # Sleep for 10 seconds between crew runs to protect API token bucket limits
            if not (i == len(sectors) - 1 and j == len(sizes) - 1):
                print("  [rate limit] Pacing API calls, sleeping for 10s...")
                time.sleep(10)
                
    return results