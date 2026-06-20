"""
src/api/routes/crew.py

GET /api/crew/stream?market=INDIA&sector=Telecom&size=Mid
  → Server-Sent Events stream.
    The frontend reads this like a chat stream (same idea as ChatGPT).

Each SSE event is a JSON object:
  { "type": "agent",    "agent": "Researcher",  "text": "Calling discover_stocks..." }
  { "type": "task",     "task": "Task 1 done",  "text": "Found 10 stocks..."        }
  { "type": "done",     "picks": [...]                                               }
  { "type": "error",    "text": "Something went wrong"                              }
"""

import json
import queue
import threading

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse

from src.agents.crew import run_stock_picker, run_single_stock_analysis
from src.api.routes.auth import get_current_user

router = APIRouter()


_PHASES = ["Researcher", "Data Analyst", "Sentiment Analyst", "Master Analyst"]


import re as _re


def _clean_md(text: str, limit: int = 180) -> str:
    """Strip markdown noise (##, **, ---, tables, backticks) → a short clean line."""
    t = str(text)
    t = _re.sub(r"```.*?```", " ", t, flags=_re.DOTALL)      # code blocks
    t = t.replace("\\n", " ")
    t = _re.sub(r"[#*`>|]+", " ", t)                         # md markers + table pipes
    t = _re.sub(r"-{2,}", " ", t)                            # horizontal rules
    t = _re.sub(r"\s+", " ", t).strip()
    return t[:limit] + ("…" if len(t) > limit else "")


def _format_step(step_output) -> dict:
    """Turn a raw CrewAI step into a clean {kind, tool, text} payload."""
    tool       = getattr(step_output, "tool", None)
    tool_input = getattr(step_output, "tool_input", None)
    thought    = (getattr(step_output, "thought", None) or "").strip()
    output     = getattr(step_output, "output", None)

    if tool:
        ti = str(tool_input).strip() if tool_input else ""
        ti = ti.strip("{}").replace('"', "").replace("'", "")
        return {"kind": "tool", "tool": str(tool), "text": (ti[:120] if ti else "")}
    if output:
        return {"kind": "answer", "tool": None, "text": _clean_md(output, 220)}
    if thought:
        return {"kind": "thought", "tool": None, "text": _clean_md(thought, 160)}
    return {"kind": "thought", "tool": None, "text": _clean_md(step_output, 140)}


def _make_callbacks(msg_queue: queue.Queue):
    """Build (step_callback, task_callback) that emit clean, agent-labelled events.

    Phase tracking lets us attribute steps to the right agent even when CrewAI
    doesn't attach the agent to a step.
    """
    state = {"phase": 0}

    def step_callback(step_output):
        try:
            payload = _format_step(step_output)
            payload["type"]  = "step"
            payload["agent"] = _PHASES[min(state["phase"], len(_PHASES) - 1)]
            msg_queue.put(payload)
        except Exception:
            pass

    def task_callback(task_output):
        try:
            done_agent = _PHASES[min(state["phase"], len(_PHASES) - 1)]
            state["phase"] += 1
            msg_queue.put({"type": "task", "agent": done_agent, "text": f"{done_agent} finished."})
        except Exception:
            pass

    return step_callback, task_callback


def _crew_event_stream(market: str, sector: str, size: str,
                       user_id: str, username: str):
    """
    Runs the CrewAI pipeline in a background thread and yields SSE events
    as the agents work. Exactly like how ChatGPT streams its response.
    """
    msg_queue: queue.Queue = queue.Queue()
    step_callback, task_callback = _make_callbacks(msg_queue)

    # ── Run crew in a separate thread so we don't block FastAPI ──────────────
    def run_thread():
        try:
            result = run_stock_picker(
                market, sector, size,
                user_id=user_id,
                username=username,
                step_callback=step_callback,
                task_callback=task_callback,
            )
            # Persist picks per run (tagged with market/date/user) and emit the
            # normalized, DB-backed picks so the UI can make them clickable.
            try:
                from src.database.paper_trading import save_picks
                saved = save_picks(result, run_by_user_id=user_id, run_by_username=username)
                if saved:
                    result["picks"] = saved
            except Exception as e:
                print(f"  [save_picks] {e}")
            msg_queue.put({"type": "done", "result": result})
        except Exception as e:
            msg_queue.put({"type": "error", "text": str(e)})

    thread = threading.Thread(target=run_thread, daemon=True)
    thread.start()

    # ── Yield SSE events until crew finishes ─────────────────────────────────
    # SSE format: each message is  "data: <json>\n\n"
    while True:
        try:
            msg = msg_queue.get(timeout=360)   # 6-minute safety timeout
        except queue.Empty:
            yield "data: " + json.dumps({"type": "error", "text": "Timed out"}) + "\n\n"
            break

        yield "data: " + json.dumps(msg) + "\n\n"

        if msg["type"] in ("done", "error"):
            break


@router.get("/stream")
def stream_crew(
    market:   str = Query(...),
    sector:   str = Query(...),
    size:     str = Query(...),
    user      = Depends(get_current_user),
):
    """
    Streams crew analysis as Server-Sent Events.
    Enforces per-account weekly run limits before starting.
    """
    # Rate limit check
    account_type = user.get("account_type", "trial")
    if account_type == "guest":
        raise HTTPException(status_code=403, detail="Guest accounts cannot run analysis. Please sign up.")

    try:
        from src.database.models import increment_run_count
        allowed = increment_run_count(user["user_id"])
        if not allowed:
            from src.database.models import ACCOUNT_LIMITS
            limit = ACCOUNT_LIMITS.get(account_type, {}).get("crew_runs", 0)
            raise HTTPException(
                status_code=429,
                detail=f"Weekly run limit reached ({limit} runs for {account_type} plan). Resets next Monday."
            )
    except HTTPException:
        raise
    except Exception:
        pass  # If DB check fails, allow the run

    return StreamingResponse(
        _crew_event_stream(
            market, sector, size,
            user_id=user["user_id"],
            username=user["name"],
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # tells nginx NOT to buffer SSE
        },
    )


# ── Single-stock Deep Analysis (full crew on one ticker) ──────────────────────

def _single_stock_event_stream(ticker: str, user_id: str, username: str):
    """Runs the 4-agent crew on ONE ticker and streams clean SSE events."""
    msg_queue: queue.Queue = queue.Queue()
    step_callback, task_callback = _make_callbacks(msg_queue)

    def run_thread():
        try:
            result = run_single_stock_analysis(
                ticker, user_id=user_id, username=username,
                step_callback=step_callback, task_callback=task_callback,
            )
            # Persist the brief so the stock's AI tab shows it afterwards.
            try:
                from src.database.paper_trading import save_picks
                saved = save_picks(result, run_by_user_id=user_id, run_by_username=username)
                if saved:
                    result["picks"] = saved
            except Exception as e:
                print(f"  [save_picks/deep] {e}")
            msg_queue.put({"type": "done", "result": result})
        except Exception as e:
            msg_queue.put({"type": "error", "text": str(e)})

    thread = threading.Thread(target=run_thread, daemon=True)
    thread.start()

    while True:
        try:
            msg = msg_queue.get(timeout=360)
        except queue.Empty:
            yield "data: " + json.dumps({"type": "error", "text": "Timed out"}) + "\n\n"
            break
        yield "data: " + json.dumps(msg) + "\n\n"
        if msg["type"] in ("done", "error"):
            break


@router.get("/stock-stream")
def stream_single_stock(
    ticker: str = Query(...),
    user    = Depends(get_current_user),
):
    """Streams a full 4-agent Deep Analysis for one ticker.

    Counts as 1 against the account's weekly portfolio/deep-analysis quota.
    """
    account_type = user.get("account_type", "trial")
    if account_type == "guest":
        raise HTTPException(status_code=403, detail="Guest accounts cannot run analysis. Please sign up.")

    try:
        from src.database.models import increment_portfolio_run_count, ACCOUNT_LIMITS
        if not increment_portfolio_run_count(user["user_id"]):
            limit = ACCOUNT_LIMITS.get(account_type, {}).get("portfolio_runs", 0)
            raise HTTPException(
                status_code=429,
                detail=f"Weekly analysis limit reached ({limit} deep/portfolio runs for {account_type} plan). Resets next Monday."
            )
    except HTTPException:
        raise
    except Exception:
        pass  # if the counter check fails, allow the run

    return StreamingResponse(
        _single_stock_event_stream(ticker, user_id=user["user_id"], username=user["name"]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
