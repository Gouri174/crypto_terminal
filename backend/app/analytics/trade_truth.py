"""Trade Truth Engine — Karma V3.2 Phase A.

Classifies every resolved TradeOutcome into one forensic verdict — richer
than win/loss, distinguishing a good entry with a bad exit from a genuinely
bad structural call. Builds on app/analytics/failure_patterns.py's
lifecycle_pattern()/risk_tags() rather than recomputing the same
win/loss-path logic a second time.

Two verdicts have real, disclosed limitations rather than silently
guessing:

- "late_entry" (entry_quality == "late"): this codebase structurally
  BLOCKS a late-classified setup from ever becoming a new TradeOutcome
  row (background_scanner.py forces needs_llm=False on "late" — see
  entry_quality.py and every prior forensic report this project has run,
  all of which independently confirmed TradeOutcome.entry_quality is
  never "late" in practice). This verdict therefore can exist in the
  taxonomy but will never actually be assigned to a real row today.
- "early_stop" ("stopped out, then price reached TP1 afterwards" per the
  original spec): this app has NO post-close price tracking —
  update_open_trades() stops checking a symbol once it closes, so
  "what happened after the stop" genuinely isn't observable. This verdict
  is replaced with a disclosed, WEAKER, but real proxy:
  "near_miss_early_stop" — price got within 80% of the distance to TP1
  (using the already-tracked max_runup_pct) before ultimately reversing to
  the stop, without ever actually crossing TP1. This is a "got close, then
  reversed" fact, not a "TP1 would have hit anyway" fact.
"""

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

_TRADED_STATUSES = ("closed_win", "closed_loss")
PERFECT_TRADE_MAX_DRAWDOWN_PCT = -2.0  # shallow MAE — a threshold, disclosed, not tuned against outcome data
NEAR_MISS_FRACTION = 0.8


def _traded_rows() -> list[TradeOutcome]:
    session = SessionLocal()
    try:
        return (
            session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(_TRADED_STATUSES)))
            .scalars()
            .all()
        )
    finally:
        session.close()


def _in_outage(exit_time: int | None, outages: list[dict]) -> bool:
    if exit_time is None:
        return False
    return any(o["start"] <= exit_time <= o["end"] for o in outages)


def _distance_to_tp1_pct(row: TradeOutcome) -> float | None:
    if row.tp1 is None or not row.entry:
        return None
    return abs(row.tp1 - row.entry) / row.entry * 100


def classify_truth(row: TradeOutcome, outages: list[dict] | None = None) -> dict:
    from app.analytics.failure_patterns import lifecycle_pattern

    outages = outages or []
    pattern = lifecycle_pattern(row)

    if row.status == "closed_stale":
        verdict = "never_triggered"
        explanation = "Never entered within the max holding window — no trade to evaluate."
    elif _in_outage(row.exit_time, outages):
        verdict = "infrastructure_failure"
        explanation = "Exit occurred inside a verified scanner monitoring gap — the outcome reflects unmonitored slippage, not the trading decision."
    elif row.entry_quality == "late":
        verdict = "late_entry"
        explanation = "Classified late at entry — the setup direction stood, but entry timing was already extended."
    elif pattern == "ran_to_tp3" or pattern == "closed_at_tp2":
        shallow = row.max_drawdown_pct is not None and row.max_drawdown_pct >= PERFECT_TRADE_MAX_DRAWDOWN_PCT
        if shallow:
            verdict = "perfect_trade"
            explanation = f"Reached its outermost target ({pattern}) with shallow drawdown (MAE {row.max_drawdown_pct}%)."
        else:
            verdict = "good_trade"
            explanation = f"Reached its outermost target ({pattern}) but with real drawdown along the way (MAE {row.max_drawdown_pct}%)."
    elif pattern == "closed_at_tp1":
        verdict = "good_trade"
        explanation = "Closed at TP1 (its only/outermost defined target)."
    elif pattern in ("reached_tp1_then_stopped", "hit_tp2_then_reversed"):
        verdict = "good_entry_bad_exit"
        explanation = f"Reached a real target ({pattern.replace('_', ' ')}) before reversing all the way to the stop."
    elif pattern == "immediate_reversal":
        verdict = "bad_structure_call"
        explanation = f"Never reached TP1 and showed minimal favorable movement (MFE {row.max_runup_pct}%) before stopping — wrong from close to the start."
    else:  # "some_favorable_move_then_stopped"
        dist = _distance_to_tp1_pct(row)
        mfe = row.max_runup_pct
        if dist and mfe is not None and mfe >= NEAR_MISS_FRACTION * dist:
            verdict = "near_miss_early_stop"
            explanation = f"Got within {NEAR_MISS_FRACTION*100:.0f}% of the distance to TP1 (MFE {mfe}% vs {round(dist,2)}% needed) before reversing to the stop — a real near-miss, not a post-close observation (this app doesn't track price after a trade closes)."
        else:
            verdict = "bad_structure_call"
            explanation = f"Some favorable movement (MFE {mfe}%) but well short of TP1 before stopping."

    return {
        "trade_outcome_id": row.id, "symbol": row.symbol, "verdict": verdict, "explanation": explanation,
        "supporting_metrics": {
            "mfe_pct": row.max_runup_pct, "mae_pct": row.max_drawdown_pct,
            "tp1_hit": row.tp1_hit, "tp2_hit": row.tp2_hit, "tp3_hit": row.tp3_hit,
            "stop_hit": row.stop_hit, "holding_minutes": row.holding_minutes,
        },
    }


_LESSON_BY_VERDICT = {
    "perfect_trade": ["Nothing to change — this is the system working as designed."],
    "good_trade": ["Consider whether trailing the stop further could have captured more of the move."],
    "good_entry_bad_exit": ["Move stop to breakeven once TP1 is reached — see trade_manager.py's existing recommendation for this exact stage."],
    "near_miss_early_stop": ["Stop may have been too tight for this setup's volatility — check entry_to_sl_atr against similar winning trades."],
    "bad_structure_call": ["Entry likely lacked real structural confirmation — check structure_score and risk_tags for this trade."],
    "late_entry": ["Structurally rare in this app's own data — entry_quality=late blocks a new plan before it can be issued."],
    "infrastructure_failure": ["Not a strategy problem — see scanner uptime, not entry/exit logic."],
    "never_triggered": ["No trade occurred — nothing to learn from the strategy side."],
}


def truth_for_trade(trade_outcome_id: int) -> dict | None:
    from app.engine.performance_center import scanner_health

    session = SessionLocal()
    try:
        row = session.get(TradeOutcome, trade_outcome_id)
    finally:
        session.close()
    if row is None or row.status not in _TRADED_STATUSES + ("closed_stale",):
        return None

    outages = scanner_health().get("outages", [])
    result = classify_truth(row, outages)
    result["lessons"] = _LESSON_BY_VERDICT.get(result["verdict"], [])
    return result


def truth_leaderboard(min_sample: int = 3) -> dict:
    from collections import Counter

    from app.engine.performance_center import scanner_health

    outages = scanner_health().get("outages", [])
    rows = _traded_rows()
    counts = Counter()
    for r in rows:
        counts[classify_truth(r, outages)["verdict"]] += 1

    return {
        "n_resolved": len(rows),
        "by_verdict": [
            {"verdict": v, "n": n, "reliable": n >= min_sample}
            for v, n in counts.most_common()
        ],
    }
