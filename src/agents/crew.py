# src/agents/crew.py
#
# This is the main orchestrator — it creates the Crew, runs the agents
# in the right order, and returns the final stock picks as structured JSON.
#
# Flow:
#   1. Pick a market + sector + size combination
#   2. Get the list of tickers from the stock universe
#   3. Create and run the 4-agent crew
#   4. Parse and return the Master Analyst's JSON output

import json
import re
from datetime import datetime

from crewai import Crew, Process

from src.agents.tasks        import create_tasks
from src.data.stock_universe import get_stocks


def run_stock_picker(market: str, sector: str, size: str) -> dict:
    """
    Runs the full 4-agent crew for one market + sector + size combination.

    Args:
        market : "INDIA" or "US"
        sector : e.g. "Technology", "Banking", "Healthcare"
        size   : "Large", "Mid", "Small", "Mega"

    Returns:
        dict with the Master Analyst's picks in structured format,
        or an error dict if something went wrong.

    Example:
        result = run_stock_picker("INDIA", "Technology", "Large")
        print(result["picks"])
    """

    print(f"\n{'='*60}")
    print(f"  Starting analysis: {market} | {sector} | {size} Cap")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── Step 1: Get tickers for this combination ───────────────────────────
    tickers = get_stocks(market, sector, size)

    if not tickers:
        return {
            "error":  f"No tickers found for {market} / {sector} / {size}",
            "market": market,
            "sector": sector,
            "size":   size,
        }

    print(f"  Tickers to analyse ({len(tickers)}): {tickers}\n")

    # ── Step 2: Create tasks and agents ───────────────────────────────────
    task_research, task_technical, task_sentiment, task_master, agents = create_tasks(
        market=market,
        sector=sector,
        size=size,
        tickers=tickers,
    )

    # ── Step 3: Assemble the Crew ──────────────────────────────────────────
    # Process.sequential = agents run one after another in order
    # Each agent reads the outputs of the tasks listed in its context field
    crew = Crew(
        agents=[
            agents["researcher"],
            agents["data_analyst"],
            agents["sentiment_analyst"],
            agents["master_analyst"],
        ],
        tasks=[
            task_research,
            task_technical,
            task_sentiment,
            task_master,
        ],
        process=Process.sequential,   # tasks run in order: 1 → 2 → 3 → 4
        verbose=True,
    )

    # ── Step 4: Run the crew ───────────────────────────────────────────────
    print("  Launching crew... (this takes 1-3 minutes)\n")
    result = crew.kickoff()

    # ── Step 5: Parse the JSON output from Master Analyst ─────────────────
    raw_output = str(result.raw)
    parsed     = extract_json(raw_output)

    if parsed:
        print(f"\n  ✓ Analysis complete. {len(parsed.get('picks', []))} picks found.")
        return parsed
    else:
        # If JSON parsing fails, return raw text so nothing is lost
        print("\n  ⚠ Could not parse JSON. Returning raw output.")
        return {
            "market":        market,
            "sector":        sector,
            "size":          size,
            "analysis_date": datetime.today().strftime("%Y-%m-%d"),
            "raw_output":    raw_output,
            "picks":         [],
            "error":         "JSON parsing failed — check raw_output field",
        }


def extract_json(text: str) -> dict | None:
    """
    Tries to extract a JSON object from the LLM's text output.
    LLMs sometimes wrap JSON in markdown code blocks — this handles that.
    """
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding any { ... } block in the text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def run_full_market_scan(market: str, sectors: list = None, sizes: list = None) -> list:
    """
    Runs the crew across multiple sectors and sizes for a full weekly scan.

    Args:
        market  : "INDIA" or "US"
        sectors : list of sectors to scan. None = all sectors.
        sizes   : list of sizes to scan. None = all sizes.

    Returns:
        List of result dicts, one per sector+size combination.

    Example (scan Indian tech stocks only):
        results = run_full_market_scan("INDIA", sectors=["Technology"], sizes=["Large", "Mid"])
    """
    from src.data.stock_universe import get_all_sectors, get_all_sizes

    sectors = sectors or get_all_sectors(market)
    sizes   = sizes   or get_all_sizes(market)

    all_results = []

    for sector in sectors:
        for size in sizes:
            result = run_stock_picker(market, sector, size)
            all_results.append(result)

    print(f"\n{'='*60}")
    print(f"  Full scan complete. {len(all_results)} combinations analysed.")
    print(f"{'='*60}\n")

    return all_results


# ─── Quick test ─────────────────────────────────────────────────────────────
# This runs ONE sector+size combo as a smoke test.
# Run with: uv run src/agents/crew.py
# NOTE: This will call the Claude API and use a small amount of your credits.

if __name__ == "__main__":
    print("Running smoke test: Indian Large Cap Technology stocks...\n")

    result = run_stock_picker(
        market="INDIA",
        sector="Technology",
        size="Large",
    )

    print("\n" + "="*60)
    print("FINAL OUTPUT FROM MASTER ANALYST")
    print("="*60)
    print(json.dumps(result, indent=2))