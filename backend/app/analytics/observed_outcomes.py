"""Observed outcome frequencies — Karma V3.3-D (display/analytics only).

Replaces the misleading "EV = +0.4R" number with what plainly happened to
comparable published plans: how often they reached TP1 / TP2 / TP3 / the
stop, with sample sizes and Wilson intervals. Evidence for replacing EV:
in the 118-trade audit, higher retrospective EV meant FEWER TP2 hits and MORE
stop-outs (rho -0.25 / +0.24, p about 0.02) because EV mostly measures
reward/risk, which is largest for tight stops.

These are historical frequencies of resolved trades, not a forecast for any
particular new trade; no scoring/decision/trade-generation code is touched.
"""

import math

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

_TRADED = ("closed_win", "closed_loss")
MIN_SAMPLE = 10


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | tuple[None, None]:
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round(max(0.0, (c - h) / d) * 100, 1), round(min(1.0, (c + h) / d) * 100, 1))


def _rate(k: int, n: int) -> dict:
    lo, hi = _wilson(k, n)
    return {"count": k, "n": n, "pct": round(k / n * 100, 1) if n else None, "ci_95_pct": [lo, hi],
            "evidence": "INSUFFICIENT DATA" if n < MIN_SAMPLE else "OBSERVED"}


def outcome_rates(rows: list) -> dict:
    """Pure function over TradeOutcome-like rows (status/tp1_hit/tp2_hit/tp3_hit/stop_hit)."""
    n = len(rows)
    tp1 = [r for r in rows if r.tp1_hit]
    tp2 = [r for r in rows if r.tp2_hit]
    return {
        "n_entered_resolved": n,
        "tp1": _rate(len(tp1), n),
        "tp2": _rate(len(tp2), n),
        "tp3": _rate(sum(1 for r in rows if r.tp3_hit), n),
        "stop": _rate(sum(1 for r in rows if r.stop_hit), n),
        "tp2_given_tp1": _rate(sum(1 for r in tp1 if r.tp2_hit), len(tp1)),
        "tp3_given_tp2": _rate(sum(1 for r in tp2 if r.tp3_hit), len(tp2)),
        "final_loss_given_tp1": _rate(sum(1 for r in tp1 if r.status == "closed_loss"), len(tp1)),
    }


def observed_outcomes(direction: str | None = None, symbol: str | None = None) -> dict:
    session = SessionLocal()
    try:
        stmt = select(TradeOutcome).where(TradeOutcome.status.in_(_TRADED))
        if direction:
            stmt = stmt.where(TradeOutcome.direction == direction)
        if symbol:
            stmt = stmt.where(TradeOutcome.symbol == symbol.upper())
        rows = session.execute(stmt).scalars().all()
    finally:
        session.close()
    out = outcome_rates(rows)
    out["filters"] = {"direction": direction, "symbol": symbol.upper() if symbol else None}
    out["note"] = (
        "Historical frequencies for resolved trades that entered (not a forecast for any single trade). "
        "TP hits are counted against the target structure each plan had, and a meaningful share of exits "
        "occurred while the scanner was down, which can delay detection. Replaces the EV number, which was "
        "anti-correlated with TP2 and positively correlated with stop-outs in the audit."
    )
    return out
