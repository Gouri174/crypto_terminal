"""Trading Engine V2 — Performance Center API.

Every route here is read-only measurement, composed entirely from
app/engine/performance_center.py. Nothing writes to scoring, confidence,
ML, entry/SL/TP generation, entry_quality thresholds, or lifecycle logic —
see that module's own docstring for the full contract.
"""

from fastapi import APIRouter, HTTPException

from app.analytics import decision_audit, karma_explain, missed_opportunity, position_sizing, strategy_attribution, trade_quality
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


# ---------------------------------------------------------------------------
# Karma V3.0 additions
# ---------------------------------------------------------------------------

@router.get("/performance/failure-patterns")
async def failure_pattern_leaderboard(min_sample: int = 3):
    """Every resolved loss classified into a lifecycle pattern (mutually
    exclusive) and zero or more risk tags — see
    app/analytics/failure_patterns.py. Only patterns with real occurrences
    in this dataset are ever reported."""
    return pc.failure_pattern_leaderboard(min_sample=min_sample)


@router.get("/performance/coin-reliability")
async def coin_reliability_leaderboard(prior_strength: int | None = None):
    """Bayesian-shrunk per-symbol reliability score — see
    app/analytics/reliability.py. Every symbol with >=1 resolved trade is
    included (unlike coin_leaderboard's min_sample gate); thin samples are
    shrunk toward the pooled win rate rather than hidden or overstated."""
    return pc.coin_reliability_leaderboard(prior_strength=prior_strength)


@router.get("/performance/position-size")
async def position_size(capital: float, risk_pct: float, stop_distance_pct: float, max_leverage: float | None = None):
    """Pure arithmetic, no ML, no execution — recommends a position size
    for a given capital/risk-tolerance/stop-distance combination. Never
    places an order."""
    return position_sizing.recommend_position_size(capital, risk_pct, stop_distance_pct, max_leverage)


# ---------------------------------------------------------------------------
# Karma V3.1 additions
# ---------------------------------------------------------------------------

@router.get("/performance/trade-quality/{trade_outcome_id}")
async def trade_quality_score(trade_outcome_id: int):
    """The 0-100 Trade Quality composite — synthesizes entry_quality, EV,
    reliability, calibrated confidence, structure, and red flags. See
    app/analytics/trade_quality.py for the fixed (not ML-tuned) formula."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.db_models import TradeOutcome

    session = SessionLocal()
    try:
        row = session.execute(select(TradeOutcome).where(TradeOutcome.id == trade_outcome_id)).scalar_one_or_none()
    finally:
        session.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No TradeOutcome with id={trade_outcome_id}")
    return trade_quality.trade_quality_for_row(row)


@router.get("/performance/confidence-display")
async def confidence_display(raw_confidence: int):
    """Reliability-adjusted confidence: raw / calibrated / ±uncertainty /
    sample size — see app/engine/calibration.py:confidence_display()."""
    return calibration.confidence_display(raw_confidence)


@router.get("/performance/explain/{trade_outcome_id}")
async def explain_trade(trade_outcome_id: int):
    """Karma Explain — bullish/risk evidence, historical context, failure-
    pattern similarity, and (for open trades) an action plan with
    conditional triggers. Pure synthesis of already-existing modules, see
    app/analytics/karma_explain.py."""
    result = karma_explain.explain_trade(trade_outcome_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No TradeOutcome with id={trade_outcome_id}")
    return result


@router.get("/performance/decision-audit")
async def decision_audit_leaderboard(min_sample: int = 3):
    """accepted_because / rejected_checks / warnings per resolved trade,
    aggregated by condition combination — computed by re-running
    decision.py's existing, UNMODIFIED market_checklist() against stored
    score breakdowns. See app/analytics/decision_audit.py."""
    return decision_audit.decision_audit_leaderboard(min_sample=min_sample)


@router.get("/performance/strategy-attribution")
async def strategy_leaderboard(min_sample: int = 3):
    """Every resolved trade classified into one strategy family from
    already-stored fields — see app/analytics/strategy_attribution.py for
    the honest disclosure of which categories are approximated proxies
    (this codebase has no per-trade BOS/CHoCH boolean)."""
    return strategy_attribution.strategy_leaderboard(min_sample=min_sample)


@router.get("/performance/missed-opportunity-status")
async def missed_opportunity_status():
    """RECORDER progress only — see app/analytics/missed_opportunity.py.
    Refuses to report a rate/conclusion below 500 resolved rows, per
    explicit instruction. Recording isn't wired into the live scan loop
    yet (that needs a small addition to background_scanner.py, which is
    under this session's 30-day freeze) — this reports whatever has been
    recorded manually/independently so far."""
    return missed_opportunity.missed_opportunity_summary()
