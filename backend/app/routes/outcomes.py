import time

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.db import SessionLocal
from app.engine.trade_reports import monthly_breakdown, performance_digest, score_correlations
from app.models.db_models import TradeOutcome

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
async def outcome_correlations():
    return score_correlations()


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
