"""Trading Engine V2 — Performance Center API.

Every route here is read-only measurement, composed entirely from
app/engine/performance_center.py. Nothing writes to scoring, confidence,
ML, entry/SL/TP generation, entry_quality thresholds, or lifecycle logic —
see that module's own docstring for the full contract.
"""

from fastapi import APIRouter, HTTPException

from app.engine import performance_center as pc

router = APIRouter()


@router.get("/performance/scanner-health")
async def scanner_health(gap_threshold_minutes: int = 10):
    """Section 1: heartbeat timeline, outage detection, uptime %."""
    return pc.scanner_health(gap_threshold_minutes=gap_threshold_minutes)


@router.get("/performance/stop-execution")
async def stop_execution(outage_gap_threshold_minutes: int = 10):
    """Section 2: stop slippage distribution — overall, by direction, by
    symbol, by volatility bucket, and during outages vs normal uptime."""
    return pc.stop_execution_audit(outage_gap_threshold_minutes=outage_gap_threshold_minutes)


@router.get("/performance/tp-continuation")
async def tp_continuation():
    """Section 3: per-trade and aggregate TP1->TP2->TP3 continuation,
    return-to-entry/return-to-stop probabilities, avg continuation/pullback."""
    return pc.tp_continuation_analytics()


@router.get("/performance/confidence-lab")
async def confidence_lab(min_bucket_n: int = 5):
    """Section 4: confidence-bucket calibration, Brier score, Expected
    Calibration Error."""
    return pc.confidence_lab(min_bucket_n=min_bucket_n)


@router.get("/performance/coin-leaderboard")
async def coin_leaderboard(min_sample: int = 3):
    """Section 5: per-symbol profit factor / win rate / avg return /
    avg confidence / avg MFE-MAE, gated behind a configurable min sample."""
    return pc.coin_leaderboard(min_sample=min_sample)


@router.get("/performance/trade-replay/{trade_outcome_id}")
async def trade_replay(trade_outcome_id: int):
    """Section 6: full replay payload for one TradeOutcome — entry
    indicators, Claude reasoning, prediction timeline, TP/SL events, exit
    reason. Ready for a frontend replay view."""
    result = pc.trade_replay(trade_outcome_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No TradeOutcome with id={trade_outcome_id}")
    return result


@router.get("/performance/trade-manager")
async def trade_manager():
    """Section 7: analytics-only view of every currently open/pending
    trade — distances to targets, confidence/trend/structure/regime
    change since entry, and a suggested Hold/Move Stop/Exit
    Partial/Exit Full recommendation. Nothing here executes anything."""
    return pc.open_trade_management_analytics()
