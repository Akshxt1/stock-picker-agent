"""Small shared helpers for the portfolio agent's Claude calls."""

import json
import os
import re


class AgentUnavailable(RuntimeError):
    """The AI returned something unusable (message is safe to show the user)."""


class NotConfigured(AgentUnavailable):
    """No ANTHROPIC_API_KEY on this server."""


def get_client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise NotConfigured("AI features are not configured on this server.")
    import anthropic
    return anthropic.Anthropic(api_key=key, timeout=120.0, max_retries=2)


def reply_text(msg) -> str:
    return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")


def json_from_text(text: str):
    """The first {...} object in a model reply, or None."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def clean_str(x, limit: int) -> str | None:
    """Whitespace-normalised text, shortened at a sentence (or word) boundary rather than mid-word."""
    if not isinstance(x, str):
        return None
    x = re.sub(r"\s+", " ", x).strip()
    if len(x) <= limit:
        return x or None
    cut = x[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if end >= limit * 0.5:
        return cut[:end + 1]
    return cut[:cut.rfind(" ")].rstrip(",;:") + "..." if " " in cut else cut


def clean_num(x, lo: float = 0.0, hi: float = 1e13) -> float | None:
    """A finite number within (lo, hi], tolerating '₹1,23,456.70'-style strings; otherwise None."""
    if isinstance(x, str):
        x = re.sub(r"[^\d.\-]", "", x.replace(",", ""))
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and lo < v <= hi else None
