"""Decision Audit — Karma V3.1.

"accepted_because" / "rejected_checks" for every resolved trade, computed
by calling decision.py's EXISTING, UNMODIFIED market_checklist() against
each TradeOutcome row's already-stored score breakdown — this is a read,
not a change, and decision.py itself is untouched (frozen, per the
current 30-day freeze). No new capture, no new DB columns: the checklist
was always computable from data already on the row, it just had never
been re-run and aggregated into a leaderboard before.

Also derives a small set of "warnings" from already-stored
entry_indicators (reusing red_flags.py's evidenced definitions) — kept
separate from accepted_because/rejected_checks since a warning isn't a
pass/fail checklist item, it's an observed risk factor.
"""

from collections import Counter

from sqlalchemy import select

from app.db import SessionLocal
from app.engine.decision import market_checklist
from app.engine.red_flags import RED_FLAG_DEFINITIONS, compute_red_flags
from app.models.db_models import TradeOutcome

_TRADED_STATUSES = ("closed_win", "closed_loss")
_CHECKLIST_TO_LABEL = {
    "trend_confirms": "trend_pass", "structure_confirms": "structure_pass",
    "volume_confirms": "volume_pass", "funding_acceptable": "funding_pass",
    "history_acceptable": "history_pass", "regime_acceptable": "regime_pass",
    "risk_acceptable": "risk_pass",
}


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


def _breakdown_from_row(row: TradeOutcome) -> dict:
    return {
        "trend": row.trend_score, "momentum": row.momentum_score, "volume": row.volume_score,
        "funding": row.funding_score, "structure": row.structure_score, "history": row.history_score,
        "regime": row.regime_score, "ml": row.ml_score, "sentiment": row.sentiment_score,
        "liquidity": row.liquidity_score, "risk": row.risk_score, "total": row.score,
    }


def audit_trade(row: TradeOutcome) -> dict:
    breakdown = _breakdown_from_row(row)
    history_stats = {"win_rate": row.historic_probability * 100} if row.historic_probability is not None else None
    checklist = market_checklist(breakdown, history_stats)

    accepted_because = [_CHECKLIST_TO_LABEL[k] for k, passed in checklist.items() if passed]
    rejected_checks = [_CHECKLIST_TO_LABEL[k] for k, passed in checklist.items() if not passed]

    red_flags = compute_red_flags(row.entry_indicators, row.structure_score, row.historic_probability)
    warnings = red_flags["red_flags"]

    return {
        "trade_outcome_id": row.id, "symbol": row.symbol,
        "accepted_because": accepted_because,
        "rejected_checks": rejected_checks,
        "warnings": warnings,
        "checklist": checklist,
    }


def _pct(n, d):
    return round(n / d * 100, 1) if d else None


def decision_audit_leaderboard(min_sample: int = 3) -> dict:
    """Groups resolved trades by their SET of passed checklist items
    (e.g. "trend_pass+volume_pass+funding_pass") and reports win rate per
    combination — the exact "Condition -> Win Rate" table requested.
    Combinations with fewer than min_sample trades are reported (nothing
    hidden) but flagged unreliable rather than implying a real rate."""
    rows = _traded_rows()
    by_combo: dict[str, list[TradeOutcome]] = {}
    audits_by_id = {}
    for r in rows:
        audit = audit_trade(r)
        audits_by_id[r.id] = audit
        combo = "+".join(sorted(audit["accepted_because"])) or "none"
        by_combo.setdefault(combo, []).append(r)

    table = []
    for combo, combo_rows in sorted(by_combo.items(), key=lambda kv: -len(kv[1])):
        wins = sum(1 for r in combo_rows if r.status == "closed_win")
        table.append({
            "condition": combo, "n": len(combo_rows),
            "win_rate_pct": _pct(wins, len(combo_rows)),
            "reliable": len(combo_rows) >= min_sample,
        })

    warning_counts = Counter()
    warning_returns = {}
    for r in rows:
        for w in audits_by_id[r.id]["warnings"]:
            warning_counts[w] += 1
            warning_returns.setdefault(w, []).append(r.realized_return_pct)

    return {
        "n_resolved": len(rows),
        "by_accepted_condition": table,
        "warning_frequency": dict(warning_counts),
        "known_warning_definitions": {k: v["description"] for k, v in RED_FLAG_DEFINITIONS.items()},
    }
