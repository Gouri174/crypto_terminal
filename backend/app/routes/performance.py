"""Trading Engine V2 — Performance Center API.

Every route here is read-only measurement, composed entirely from
app/engine/performance_center.py. Nothing writes to scoring, confidence,
ML, entry/SL/TP generation, entry_quality thresholds, or lifecycle logic —
see that module's own docstring for the full contract.
"""

from fastapi import APIRouter, HTTPException

from app.engine import calibration
from app.engine import performance_center as pc
from app.engine import trade_reports

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


# ---------------------------------------------------------------------------
# Karma V2.1 Phase 7 additions
# ---------------------------------------------------------------------------

@router.get("/performance/calibration-table")
async def calibration_table(min_sample: int = 5):
    """V2.1 Phase 4: confidence-bucket calibration table (predicted vs
    observed win rate, 95% CI) — see app/engine/calibration.py."""
    return calibration.calibration_table(min_sample=min_sample)


@router.get("/performance/ev-leaderboard")
async def ev_leaderboard(min_sample: int = 1):
    """V2.1 Phase 1/7: ranks resolved trades by their stored
    expected_value.expected_r against what actually happened, and reports
    corr(score, expected_r) — the same score-vs-EV disagreement check from
    the V2.1 forensic report, kept live as new trades resolve."""
    return pc.ev_leaderboard(min_sample=min_sample)


@router.get("/performance/red-flag-leaderboard")
async def red_flag_leaderboard():
    """V2.1 Phase 6/7: win rate and avg return by red_flag_score (0-3)."""
    return pc.red_flag_leaderboard()


@router.get("/performance/feature-importance")
async def feature_importance(min_sample: int = 20, limit: int | None = None):
    """Reuses trade_reports.py's existing feature_importance() rather than
    duplicating it — this route just exposes it under /performance for
    Phase 7's requested dashboard surface."""
    return trade_reports.feature_importance(min_sample=min_sample, limit=limit)
