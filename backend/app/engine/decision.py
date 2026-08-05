"""Deterministic trade decisions the LLM must not override.

Direction (long/short/no_trade), the market checklist, and the letter
grade are all computed here from the same inputs scoring.py already
produces. Claude's job is to explain these, never to choose them — that's
what "decision consistency" means in this app: a fixed pipeline (trend ->
structure -> volume -> funding -> history -> ML -> risk -> confidence),
with Claude only at the very end, explaining a result it didn't produce.
"""

from app.engine.scoring import _tf

# Below this score, even a directionally-aligned setup isn't worth issuing
# — the components agree it's weak, not just that a direction can be read.
MIN_SCORE_FOR_TRADE = 45.0


def decide_direction(features: dict, breakdown: dict) -> str:
    """Majority vote of 1h/4h/1d trend-vs-EMA50, gated by a minimum score.
    A tie (e.g. one timeframe each way with the third missing) or a score
    below MIN_SCORE_FOR_TRADE is "no_trade" — a real answer, not a
    fallback."""
    votes = [
        _tf(features, tf).get("trend_vs_ema50")
        for tf in ("1h", "4h", "1d")
        if _tf(features, tf).get("trend_vs_ema50")
    ]
    if not votes:
        return "no_trade"

    above, below = votes.count("above"), votes.count("below")
    if above == below:
        return "no_trade"
    if breakdown.get("total", 0) < MIN_SCORE_FOR_TRADE:
        return "no_trade"
    return "long" if above > below else "short"


def market_checklist(breakdown: dict, history_stats: dict | None) -> dict:
    """Each check is a plain threshold on an already-computed score
    component or stat — transparent and inspectable, not a black box.
    Thresholds are a first pass, not tuned against outcome data yet (there
    wasn't any until TradeOutcome existed)."""
    return {
        "trend_confirms": breakdown.get("trend", 0) >= 15,
        "structure_confirms": breakdown.get("structure", 0) >= 8,
        "volume_confirms": breakdown.get("volume", 0) >= 5,
        "funding_acceptable": breakdown.get("funding", 0) >= 5,
        "history_acceptable": bool(history_stats) and history_stats.get("win_rate", 0) >= 50,
        "regime_acceptable": breakdown.get("regime", 0) >= 0,
        "risk_acceptable": breakdown.get("risk", 0) >= -10,
    }


def trade_grade(confidence: int) -> str:
    if confidence >= 85:
        return "A+"
    if confidence >= 75:
        return "A"
    if confidence >= 65:
        return "B+"
    if confidence >= 55:
        return "B"
    if confidence >= 45:
        return "C"
    return "Avoid"
