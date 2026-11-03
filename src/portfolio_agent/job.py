"""The strategy as a background job (kind 'portfolio_strategy'), so a slow AI call never holds a web request open."""

import logging

from src.portfolio_agent import analysis, strategy
from src.portfolio_agent.llm import AgentUnavailable

logger = logging.getLogger("stockpicker.portfolio_agent")

KIND = "portfolio_strategy"


def run(params: dict, sink) -> dict:
    """params: {holdings, goal, risk}. `sink(event)` records progress for the status endpoint."""
    try:
        sink({"type": "progress", "text": "Loading live prices and risk data..."})
        result = analysis.analyze(params["holdings"])
        sink({"type": "progress", "text": "Writing your plan..."})
        plan = strategy.generate(result, params.get("goal", ""), params.get("risk", "moderate"))
        return {"analysis": result, "strategy": plan}
    except (AgentUnavailable, analysis.AnalysisError):
        raise                                    # messages are written to be shown to the user
    except Exception:
        logger.exception("portfolio strategy job failed")
        raise RuntimeError("Something went wrong building your plan. Please try again.") from None
