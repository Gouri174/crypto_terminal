"""Shared "does this need a fresh Claude call" decision.

Used by BOTH the background scanner and the on-demand /api/analyze/{symbol}
endpoint, so opening a coin's detail page can't bypass the same cost
controls the scanner already enforces. Before this existed, /api/analyze
called Claude on every single hit — refresh the page, pay again — which
was the single biggest source of unnecessary spend in the app.

Deliberately doesn't track raw price delta or regime label as separate
trigger conditions. A price move that doesn't shift the score or the
deterministic direction isn't a change to the trade thesis worth paying to
re-explain, and a regime shift already flows into the score through its
own regime component — tracking either separately would just duplicate
what the score-change and direction-change checks already catch.
"""

from app.config import LLM_MAX_AGE_SECONDS, LLM_SCORE_CHANGE_THRESHOLD


def should_reexplain(
    cached_plan: dict | None,
    last_llm_score: float | None,
    trade_plan_updated_at: int | None,
    new_total: float,
    new_direction: str,
    now_ms: int,
) -> bool:
    if cached_plan is None:
        return True
    if last_llm_score is None or abs(new_total - last_llm_score) >= LLM_SCORE_CHANGE_THRESHOLD:
        return True
    if cached_plan.get("recommendation") != new_direction:
        return True
    if trade_plan_updated_at is None or (now_ms - trade_plan_updated_at) > LLM_MAX_AGE_SECONDS * 1000:
        return True
    return False
