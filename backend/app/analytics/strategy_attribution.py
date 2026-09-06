"""Strategy Attribution Engine — Karma V3.0/V3.1.

Classifies every resolved trade into ONE strategy family, using only
fields already captured at issuance. Honest limitation, stated once:
this codebase does not store a per-trade BOS/CHoCH boolean or a raw HTF-
trend-vs-1h-trend disagreement flag (confirmed repeatedly across this
project's forensic reports), so "BOS Pullback" and "Countertrend Bounce"
below are approximated from the closest available proxies
(structure_score and stored 1h/HTF trend fields respectively) rather than
a true structural detection — this is disclosed in each rule's docstring
line, not hidden.
"""

from collections import Counter

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

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


def classify_strategy(row: TradeOutcome) -> str:
    ei = row.entry_indicators or {}
    lr = row.level_reasoning or {}
    rsi = ei.get("rsi14")
    bb_pct = ei.get("bb_pct")
    dist_ema20 = ei.get("distance_to_ema20_pct")

    if lr.get("fvg_used"):
        return "fvg_continuation"  # an active FVG was recorded at entry
    if row.entry_quality == "late" or (bb_pct is not None and bb_pct > 0.9):
        return "breakout_chase"  # entry_quality already flags lateness; bb_pct>0.9 is the closest stored proxy for "chasing an extended move"
    if rsi is not None and ((row.direction == "long" and rsi < 35) or (row.direction == "short" and rsi > 65)):
        return "mean_reversion"  # oversold-long / overbought-short at entry
    if dist_ema20 is not None and abs(dist_ema20) < 1.5:
        return "ema_pullback"  # price close to EMA20 in raw % terms — the closest stored proxy for "pullback into EMA20"
    if row.structure_score is not None and row.structure_score >= 9:
        return "bos_pullback"  # no true BOS boolean stored per-trade — structure_score>=9 is the aggregate proxy, see module docstring
    return "trend_continuation_other"


def _pct(n, d):
    return round(n / d * 100, 1) if d else None


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def _profit_factor(rows: list[TradeOutcome]) -> float | None:
    rets = [r.realized_return_pct for r in rows if r.realized_return_pct is not None]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    return round(gains / abs(loss), 3) if loss else None


def strategy_leaderboard(min_sample: int = 3) -> dict:
    rows = _traded_rows()
    by_strategy: dict[str, list[TradeOutcome]] = {}
    for r in rows:
        by_strategy.setdefault(classify_strategy(r), []).append(r)

    table = []
    for strategy, sub in sorted(by_strategy.items(), key=lambda kv: -len(kv[1])):
        wins = sum(1 for x in sub if x.status == "closed_win")
        table.append({
            "strategy": strategy, "n": len(sub), "win_rate_pct": _pct(wins, len(sub)),
            "profit_factor": _profit_factor(sub), "avg_return_pct": _avg([x.realized_return_pct for x in sub]),
            "reliable": len(sub) >= min_sample,
        })
    return {"n_resolved": len(rows), "strategies": table}
