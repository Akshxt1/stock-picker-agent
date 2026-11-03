"""Turn raw CrewAI step/task callbacks into clean, agent-labelled progress events."""

import re

PHASES = ["Researcher", "Data Analyst", "Sentiment Analyst", "Master Analyst"]


def clean_md(text: str, limit: int = 180) -> str:
    """Strip markdown noise (##, **, ---, tables, backticks) → a short clean line."""
    t = str(text)
    t = re.sub(r"```.*?```", " ", t, flags=re.DOTALL)      # code blocks
    t = t.replace("\\n", " ")
    t = re.sub(r"[#*`>|]+", " ", t)                         # md markers + table pipes
    t = re.sub(r"-{2,}", " ", t)                            # horizontal rules
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit] + ("…" if len(t) > limit else "")


def format_step(step_output) -> dict:
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
        return {"kind": "answer", "tool": None, "text": clean_md(output, 220)}
    if thought:
        return {"kind": "thought", "tool": None, "text": clean_md(thought, 160)}
    return {"kind": "thought", "tool": None, "text": clean_md(step_output, 140)}


def make_callbacks(sink):
    """Build (step_callback, task_callback) that emit events via `sink(payload)`.

    Phase tracking lets us attribute steps to the right agent even when CrewAI
    doesn't attach the agent to a step.
    """
    state = {"phase": 0}

    def step_callback(step_output):
        try:
            payload = format_step(step_output)
            payload["type"]  = "step"
            payload["agent"] = PHASES[min(state["phase"], len(PHASES) - 1)]
            sink(payload)
        except Exception:
            pass

    def task_callback(task_output):
        try:
            done_agent = PHASES[min(state["phase"], len(PHASES) - 1)]
            state["phase"] += 1
            sink({"type": "task", "agent": done_agent, "text": f"{done_agent} finished."})
        except Exception:
            pass

    return step_callback, task_callback
