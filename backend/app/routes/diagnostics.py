"""Deep trade intelligence / forensic analysis API.

Every route here is read-only measurement — nothing writes to scoring,
confidence, ML, entry/SL/TP generation, or lifecycle logic. Composes
app/engine/forensic_diagnostics.py (new analyses) with the existing
app/engine/trade_reports.py functions (confidence/grade calibration,
entry-quality performance, momentum buckets, direction breakdown, signal
counts) rather than duplicating anything already built.
"""

import time

from fastapi import APIRouter

from app.engine import forensic_diagnostics as fd
from app.engine import trade_reports
from app.engine.background_scanner import load_current_regime

router = APIRouter()

_DAY_MS = 86_400_000


@router.get("/diagnostics/trades")
async def diagnostics_trades():
    """Section 1/2/11/12/13/17 of the forensic spec: full per-trade autopsy,
    TP/SL path classification, holding-time buckets, stop/target R:R,
    time-of-day, and an approximated (clearly labeled) entry-shift
    counterfactual."""
    return {
        "autopsies": fd.trade_autopsies(),
        "tp_sl_path_analysis": fd.tp_sl_path_analysis(),
        "holding_time_analysis": fd.holding_time_analysis(),
        "stop_target_analysis": fd.stop_target_analysis(),
        "time_of_day_analysis": fd.time_of_day_analysis(),
        "counterfactual_entry_shift": fd.counterfactual_entry_shift(),
    }


@router.get("/diagnostics/patterns")
async def diagnostics_patterns():
    """Section 14/15/16: feature-interaction discovery (searched across ALL
    resolved trades, not cherry-picked), multi-tag failure clustering, and
    "would this hypothetical filter have excluded this loss" — explicitly
    NOT the same as "should this become a rule."""
    return {
        "feature_interaction_discovery": fd.feature_interaction_discovery(),
        "failure_clustering": fd.failure_clustering(),
        "what_would_have_saved_this_trade": fd.what_would_have_saved_this_trade(),
    }


@router.get("/diagnostics/calibration")
async def diagnostics_calibration(min_sample: int = 5):
    """Section 5: confidence and grade calibration (existing trade_reports
    functions, not duplicated). ML-probability calibration is reported
    honestly as unavailable when no resolved trade has a stored
    ml_probability — never computed from a missing value."""
    return {
        "confidence_calibration": trade_reports.confidence_calibration(min_sample=min_sample),
        "grade_calibration": trade_reports.grade_calibration(min_sample=min_sample),
        "ml_probability_calibration": fd.ml_probability_calibration(min_sample=min_sample),
    }


@router.get("/diagnostics/entry-quality")
async def diagnostics_entry_quality(min_sample: int = 5):
    """Section 3/4: entry-quality performance, momentum-score buckets (the
    exact 0-7/8-11/12-14/15 ranges), and the momentum x structure
    cross-tabulation."""
    return {
        "entry_quality_performance": trade_reports.entry_quality_performance(min_sample=min_sample),
        "momentum_score_buckets": trade_reports.momentum_score_bucket_performance(min_sample=min_sample),
        "momentum_interaction_analysis": fd.momentum_interaction_analysis(),
    }


@router.get("/diagnostics/direction")
async def diagnostics_direction(days: int = 30):
    """Section 7: long vs short outcomes (published trades) AND how many
    long/short/no_trade candidates the engine generated across the full
    scanned universe in the window — the two questions "genuinely long-
    favoring market" vs "engine only selects longs" vs "shorts filtered
    out" need both numbers, not just one."""
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days * _DAY_MS
    return {
        "resolved_trade_outcomes_by_direction": trade_reports.direction_breakdown(start_ms, now_ms),
        "full_universe_signal_counts": trade_reports.signal_direction_counts(start_ms, now_ms),
    }


@router.get("/diagnostics/regime")
async def diagnostics_regime():
    """Section 8: per-regime (risk_on/risk_off/mixed) outcome breakdown —
    new, since monthly_breakdown() only ever surfaces the single BEST
    regime, not each one's own stats."""
    return {"regime_performance": fd.regime_performance(), "current_regime": load_current_regime()}


@router.get("/diagnostics/correlation")
async def diagnostics_correlation(window_hours: int = 4):
    """Section 9: are resolved trades independent predictions, or several
    correlated bets on the same market move (same-window entries)?"""
    return fd.correlation_concentration_analysis(window_ms=window_hours * 3_600_000)


@router.get("/diagnostics/ranking")
async def diagnostics_ranking():
    """Section 18: LIMITED ranking backtest — re-slices actually-published
    trades by their own rank at issuance (ScanSnapshot). Not a full-
    universe top-N simulation; see the function's own "note" field for
    exactly why."""
    return fd.ranking_backtest()


@router.get("/diagnostics/daily-report")
async def diagnostics_daily_report():
    """Section 19: the daily market-regime report — designed to run once a
    day, not built as a scheduled job yet (this app has no cron/scheduler
    infra, same reasoning as ml_retrain.py's own deferred-scheduling note).
    V1.1 extended it with a 24h signal funnel and today's score/confidence/
    R:R/entry-quality/momentum/structure/evidence-support breakdowns."""
    return fd.daily_market_regime_report(load_current_regime())


@router.get("/diagnostics/funnel")
async def diagnostics_funnel(days: int = 1):
    """V1.1 section 3: Universe -> Candidates -> Top-N pool -> Published ->
    Triggered -> Resolved, as distinct symbol counts — read left to right
    for whether the bottleneck is too many candidates, poor ranking, poor
    entries, or poor trade management."""
    now_ms = int(time.time() * 1000)
    return fd.signal_funnel_report(now_ms - days * _DAY_MS, now_ms)


@router.get("/diagnostics/why-not/{symbol}")
async def diagnostics_why_not(symbol: str, top_n: int = 3):
    """V1.1 section 8: for a symbol's most recent scan, the next `top_n`
    ranked candidates from the SAME cycle and deterministic reasons
    (score/confidence/structure/entry_quality comparisons, never Claude)
    for why they ranked lower."""
    return fd.why_not_comparison(symbol, top_n=top_n)


@router.get("/diagnostics/milestones")
async def diagnostics_milestones():
    """V1.1 section 15: fixed resolved-trade-count milestones (10/25/50/
    100/250/500) and what becomes reasonable to test at each — a lookup
    table, not a statistical-significance claim."""
    return fd.data_milestones()
