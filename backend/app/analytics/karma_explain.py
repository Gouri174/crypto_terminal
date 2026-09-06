"""Karma Explain — Karma V3.1.

Synthesizes bullish evidence, risk evidence, historical context, failure-
pattern similarity, and (for open trades) an action plan — all from
modules that already exist. Nothing here computes anything new; it's a
narrative assembly layer over decision_audit.py, failure_patterns.py,
expected_value.py, reliability.py, and trade_manager.py.
"""

from sqlalchemy import select

from app.analytics.decision_audit import audit_trade
from app.analytics.failure_patterns import pattern_similarity
from app.analytics.reliability import symbol_reliability
from app.db import SessionLocal
from app.engine.red_flags import RED_FLAG_DEFINITIONS
from app.models.db_models import TradeOutcome

_BULLISH_LABELS = {
    "trend_pass": "Multi-timeframe trend confirms.",
    "structure_pass": "Structure confirms (fresh trend break and/or FVG present).",
    "volume_pass": "Volume/flow confirms.",
    "funding_pass": "Funding is acceptable (not crowded).",
    "history_pass": "Historical analogue supports this direction.",
    "regime_pass": "Aligned with the overall market regime.",
    "risk_pass": "No extreme-volatility risk penalty applied.",
}
_WEAK_LABELS = {
    "trend_pass": "Trend did not confirm.",
    "structure_pass": "Structure was weak or unconfirmed.",
    "volume_pass": "Volume/flow did not confirm.",
    "funding_pass": "Funding was elevated/crowded.",
    "history_pass": "No historical analogue supported this direction (or none exists).",
    "regime_pass": "Not aligned with the overall market regime.",
    "risk_pass": "An extreme-volatility risk penalty was applied.",
}


def explain_trade(trade_outcome_id: int) -> dict | None:
    session = SessionLocal()
    try:
        row = session.get(TradeOutcome, trade_outcome_id)
    finally:
        session.close()
    if row is None:
        return None

    audit = audit_trade(row)
    bullish = [_BULLISH_LABELS[c] for c in audit["accepted_because"] if c in _BULLISH_LABELS]
    weak = [_WEAK_LABELS[c] for c in audit["rejected_checks"] if c in _WEAK_LABELS]
    warnings = [RED_FLAG_DEFINITIONS[w]["description"] for w in audit["warnings"] if w in RED_FLAG_DEFINITIONS]

    similarity = pattern_similarity(row.entry_indicators, row.structure_score, row.historic_probability, row.direction)
    reliability = symbol_reliability(symbol=row.symbol)

    action_plan = None
    if row.status in ("pending", "open"):
        from app.engine.trade_manager import compute_management_decision, conditional_triggers, stage_probabilities
        from app.engine.trade_outcomes import _compute_stage

        stage = _compute_stage(row)
        probs = stage_probabilities(row, stage)
        decision, reason = compute_management_decision(row, stage, probs, None)
        action_plan = {
            "stage": stage, "recommendation": decision, "reason": reason,
            "conditional_triggers": conditional_triggers(row, stage),
        }
    elif row.status in ("closed_win", "closed_loss"):
        action_plan = {"stage": "EXITED", "recommendation": row.status, "reason": "Trade already resolved — see outcome fields."}

    return {
        "trade_outcome_id": row.id, "symbol": row.symbol, "direction": row.direction,
        "bullish_evidence": bullish,
        "bullish_evidence_count": f"{len(bullish)}/{len(_BULLISH_LABELS)}",
        "risk_evidence": weak + warnings,
        "historical_context": similarity,
        "reliability": {"score": reliability.get("reliability_score"), "sample_size": reliability.get("n")},
        "expected_value": row.expected_value,
        "claude_summary": row.reasoning,
        "action_plan": action_plan,
    }
