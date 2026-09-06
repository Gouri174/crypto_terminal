"""Failure Pattern Engine — Karma V3.0.

Classifies every resolved TradeOutcome into reusable pattern tags —
lifecycle-based (how far it got before failing/succeeding) and feature-
based (which already-known risk factors were present at entry, reusing
app/engine/red_flags.py's definitions rather than inventing new ones with
no evidence behind them). Nothing here changes scoring, confidence, or
which trades get taken; this is read-only classification for the
Performance Center dashboard and Trade Replay pages.

No new DB columns: every tag is computed live from already-stored fields
(entry_indicators, structure_score, historic_probability, tp1/2/3_hit,
stop_hit, direction, exit_time) — same "recompute on request" pattern as
every other analytics module in this codebase (see
performance_center.py's own module docstring for why).

Deliberately does NOT include failure categories with no real evidence in
this project's own history — e.g. an earlier draft roadmap suggested
"RSI>75 + CMF negative" as a category, but that exact combination had
ZERO occurrences across every resolved trade audited so far (see
karma_v2_1_model_improvement_report.md, Section 6). A category can't be
"mandatory" if the data never actually produced an example of it.
"""

from collections import Counter

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

# Imported lazily inside the functions that need it (not at module level)
# to avoid a circular import: performance_center.py's trade_replay() also
# imports FROM this module, the other direction.

_TRADED_STATUSES = ("closed_win", "closed_loss")


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


def _pct(n, d):
    return round(n / d * 100, 1) if d else None


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def _in_outage(exit_time: int | None, outages: list[dict]) -> bool:
    if exit_time is None:
        return False
    return any(o["start"] <= exit_time <= o["end"] for o in outages)


def lifecycle_pattern(row: TradeOutcome) -> str:
    """The PRIMARY, mutually-exclusive classification — how far the trade
    got before it resolved. Matches the win/loss clustering already
    validated in karma_v2_forensic_redesign.md Parts 4/5, formalized here
    as a reusable function instead of a one-off analysis script."""
    if row.status == "closed_win":
        if row.tp3_hit:
            return "ran_to_tp3"
        if row.tp2_hit:
            return "closed_at_tp2"
        if row.tp1_hit:
            return "closed_at_tp1"
        return "closed_win_no_tp_flag"  # max-holding-window edge case
    # closed_loss
    if row.tp2_hit and not row.tp3_hit:
        return "hit_tp2_then_reversed"
    if row.tp1_hit and not row.tp2_hit:
        return "reached_tp1_then_stopped"
    mfe = row.max_runup_pct or 0
    if mfe < 1.0:
        return "immediate_reversal"
    return "some_favorable_move_then_stopped"


def risk_tags(row: TradeOutcome, outages: list[dict] | None = None) -> list[str]:
    """SECONDARY tags — zero or more, feature-based, reusing
    red_flags.py's exact evidenced definitions plus two lifecycle-adjacent
    ones (short direction, scanner-outage-corrupted) that aren't per-trade
    "red flags" at issuance but are real, previously-documented risk
    factors for this specific project's history."""
    tags = []
    ei = row.entry_indicators or {}
    rsi = ei.get("rsi14")
    if rsi is not None and 30 <= rsi < 50:
        tags.append("rsi_chop_zone")
    if row.structure_score is not None and row.structure_score < 9:
        tags.append("weak_structure")
    if row.historic_probability is None:
        tags.append("no_historical_analogue")
    if row.direction == "short":
        tags.append("short_direction")
    if outages is not None and _in_outage(row.exit_time, outages):
        tags.append("scanner_outage_corrupted")
    return tags


def classify_trade(row: TradeOutcome, outages: list[dict] | None = None) -> dict:
    return {
        "trade_outcome_id": row.id, "symbol": row.symbol,
        "lifecycle_pattern": lifecycle_pattern(row),
        "risk_tags": risk_tags(row, outages),
    }


def failure_pattern_leaderboard(min_sample: int = 3) -> dict:
    """Losses grouped by lifecycle_pattern (mutually exclusive) and,
    separately, by each risk_tag (a loss can carry more than one) — count
    and avg return for each, gated behind min_sample. This is the
    leaderboard the Performance Center dashboard surfaces."""
    rows = _traded_rows()
    losses = [r for r in rows if r.status == "closed_loss"]
    from app.engine.performance_center import scanner_health  # lazy: see module-level note above

    outages = scanner_health().get("outages", [])

    by_lifecycle = Counter()
    lifecycle_returns = {}
    for r in losses:
        pattern = lifecycle_pattern(r)
        by_lifecycle[pattern] += 1
        lifecycle_returns.setdefault(pattern, []).append(r.realized_return_pct)

    lifecycle_table = [
        {"pattern": p, "n": n, "avg_return_pct": _avg(lifecycle_returns[p]), "reliable": n >= min_sample}
        for p, n in by_lifecycle.most_common()
    ]

    by_tag = Counter()
    tag_returns = {}
    for r in losses:
        for tag in risk_tags(r, outages):
            by_tag[tag] += 1
            tag_returns.setdefault(tag, []).append(r.realized_return_pct)

    tag_table = [
        {"tag": t, "n": n, "avg_return_pct": _avg(tag_returns[t]), "reliable": n >= min_sample}
        for t, n in by_tag.most_common()
    ]

    return {
        "n_losses": len(losses),
        "n_total_resolved": len(rows),
        "by_lifecycle_pattern": lifecycle_table,
        "by_risk_tag": tag_table,
        "note": "Only patterns/tags with real occurrences in this dataset are reported — nothing is a fixed example list.",
    }


def pattern_similarity(
    entry_indicators: dict | None,
    structure_score: float | None,
    historic_probability: float | None,
    direction: str | None,
    min_sample: int = 3,
) -> dict:
    """For a NEW or OPEN trade (before/without a resolved outcome): which
    risk_tags would this setup trigger, and what did resolved trades with
    at least one of the SAME tags actually do? Used by trade_replay() for
    closed trades and available for a live prediction's context too.

    Deliberately reports "shares >=1 tag" matches, not "identical tag set"
    — requiring an exact set match would fragment the already-small
    sample into slices too thin to report (see min_sample gating below)."""
    fake_row = TradeOutcome(
        entry_indicators=entry_indicators, structure_score=structure_score,
        historic_probability=historic_probability, direction=direction,
    )
    my_tags = set(risk_tags(fake_row))
    if not my_tags:
        return {"matched_tags": [], "note": "No known risk tags apply to this setup."}

    rows = _traded_rows()
    from app.engine.performance_center import scanner_health  # lazy: see module-level note above

    outages = scanner_health().get("outages", [])
    matches = [r for r in rows if my_tags & set(risk_tags(r, outages))]

    if len(matches) < min_sample:
        return {
            "matched_tags": sorted(my_tags), "n": len(matches),
            "note": f"Fewer than {min_sample} historical trades share any of these tags — insufficient to report a rate.",
        }

    wins = sum(1 for r in matches if r.status == "closed_win")
    return {
        "matched_tags": sorted(my_tags),
        "n": len(matches),
        "wins": wins,
        "losses": len(matches) - wins,
        "win_rate_pct": _pct(wins, len(matches)),
        "avg_return_pct": _avg([r.realized_return_pct for r in matches]),
    }
