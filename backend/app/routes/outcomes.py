import time

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.db import SessionLocal
from app.engine.trade_reports import (
    confidence_calibration,
    feature_importance,
    grade_calibration,
    monthly_breakdown,
    open_trade_count,
    performance_digest,
    signals_issued_summary,
)
from app.models.db_models import PredictionSnapshot, TradeOutcome

router = APIRouter()

_DAY_MS = 24 * 60 * 60 * 1000


def _serialize(row: TradeOutcome) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at,
        "symbol": row.symbol,
        "exchange": row.exchange,
        "spot_or_futures": row.spot_or_futures,
        "direction": row.direction,
        "timeframe": row.timeframe,
        "entry_low": row.entry_low,
        "entry_high": row.entry_high,
        "entry": row.entry,
        "stop_loss": row.stop_loss,
        "tp1": row.tp1,
        "tp2": row.tp2,
        "tp3": row.tp3,
        "entry_hit": row.entry_hit,
        "tp1_hit": row.tp1_hit,
        "tp2_hit": row.tp2_hit,
        "tp3_hit": row.tp3_hit,
        "stop_hit": row.stop_hit,
        "entry_time": row.entry_time,
        "exit_time": row.exit_time,
        "holding_minutes": row.holding_minutes,
        "status": row.status,
        "score": row.score,
        "confidence": row.confidence,
        "grade": row.grade,
        "ml_probability": row.ml_probability,
        "historic_probability": row.historic_probability,
        "market_regime": row.market_regime,
        "reasoning": row.reasoning,
        "realized_return_pct": row.realized_return_pct,
        "max_runup_pct": row.max_runup_pct,
        "max_drawdown_pct": row.max_drawdown_pct,
        "tp1_before_stop": row.tp1_before_stop,
        "key_score_component": row.key_score_component,
        "explanation_mentioned_key_factor": row.explanation_mentioned_key_factor,
        "counterfactual_direction": row.counterfactual_direction,
        "counterfactual_return_pct": row.counterfactual_return_pct,
        "counterfactual_note": row.counterfactual_note,
        "score_formula_version": row.score_formula_version,
        "prompt_version": row.prompt_version,
        "ml_model_version": row.ml_model_version,
    }


@router.get("/outcomes")
async def list_outcomes(
    status: str | None = None,
    symbol: str | None = None,
    limit: int = Query(default=50, le=500),
):
    session = SessionLocal()
    try:
        stmt = select(TradeOutcome).order_by(TradeOutcome.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(TradeOutcome.status == status)
        if symbol:
            stmt = stmt.where(TradeOutcome.symbol == symbol.upper())
        rows = session.execute(stmt).scalars().all()
    finally:
        session.close()
    return [_serialize(r) for r in rows]


@router.get("/outcomes/correlations")
async def outcome_correlations(limit: int | None = Query(default=None, description="Only the N most recent resolved trades")):
    """Which score components actually separate wins from losses — see
    app/engine/trade_reports.py:feature_importance for the method and its
    honest limits (not a significance test, gated behind a minimum sample
    size). `limit` narrows to the most recent N resolved trades, e.g.
    ?limit=100 for "what's mattered lately" instead of all-time."""
    return feature_importance(limit=limit)


@router.get("/digest/daily")
async def daily_digest():
    now_ms = int(time.time() * 1000)
    return performance_digest(now_ms - _DAY_MS, now_ms, "Last 24 hours")


@router.get("/digest/weekly")
async def weekly_report():
    now_ms = int(time.time() * 1000)
    start = now_ms - 7 * _DAY_MS
    digest = performance_digest(start, now_ms, "Last 7 days")
    return digest


@router.get("/digest/monthly")
async def monthly_report():
    now_ms = int(time.time() * 1000)
    start = now_ms - 30 * _DAY_MS
    digest = performance_digest(start, now_ms, "Last 30 days")
    digest["breakdown"] = monthly_breakdown(start, now_ms)
    return digest


@router.get("/digest/90day")
async def ninety_day_report():
    now_ms = int(time.time() * 1000)
    start = now_ms - 90 * _DAY_MS
    digest = performance_digest(start, now_ms, "Last 90 days")
    digest["breakdown"] = monthly_breakdown(start, now_ms)
    return digest


@router.get("/digest/signals/daily")
async def daily_signals():
    """Different from /digest/daily: scores signals ISSUED today (however
    they've resolved so far, including still-open ones), not signals that
    happened to RESOLVE today regardless of when they were picked. This is
    the "today's picks" report."""
    now_ms = int(time.time() * 1000)
    return signals_issued_summary(now_ms - _DAY_MS, now_ms, "Today's signals")


@router.get("/digest/signals/weekly")
async def weekly_signals():
    now_ms = int(time.time() * 1000)
    return signals_issued_summary(now_ms - 7 * _DAY_MS, now_ms, "This week's signals")


@router.get("/outcomes/open-count")
async def open_count():
    return open_trade_count()


@router.get("/outcomes/calibration/confidence")
async def confidence_calibration_route(min_sample: int = Query(default=5)):
    """Does a 90-confidence trade actually win more than a 60-confidence
    one? See app/engine/trade_reports.py:confidence_calibration — real
    trades only, honestly excludes rows predating the confidence field."""
    return confidence_calibration(min_sample=min_sample)


@router.get("/outcomes/calibration/grade")
async def grade_calibration_route(min_sample: int = Query(default=5)):
    return grade_calibration(min_sample=min_sample)


@router.get("/outcomes/{trade_outcome_id}/snapshots")
async def outcome_snapshots(trade_outcome_id: int):
    """The append-only validation history for one TradeOutcome — every
    scan cycle's deterministic check (price, pnl%, distance to targets)
    since the plan was issued. See app/engine/trade_outcomes.py:record_snapshot."""
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(PredictionSnapshot)
                .where(PredictionSnapshot.trade_outcome_id == trade_outcome_id)
                .order_by(PredictionSnapshot.timestamp)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "current_price": r.current_price,
            "current_pnl_pct": r.current_pnl_pct,
            "distance_to_tp1_pct": r.distance_to_tp1_pct,
            "distance_to_tp2_pct": r.distance_to_tp2_pct,
            "distance_to_stop_pct": r.distance_to_stop_pct,
            "confidence": r.confidence,
            "grade": r.grade,
            "market_regime": r.market_regime,
            "status": r.status,
            "reason": r.reason,
        }
        for r in rows
    ]
