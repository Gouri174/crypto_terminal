"""Deep trade intelligence / forensic analysis — measurement only.

Everything here READS TradeOutcome/PredictionSnapshot/ScanSnapshot and
computes statistics. Nothing here writes to those tables, changes
scoring.py's weights, confidence.py's formula, entry/SL/TP generation,
ml_model.py, or lifecycle.py. This module's only job is to answer "why is
the system winning or losing," using only data already stored — never
reconstructed from current prices, never guessed.

Every report function:
  - reads from timestamped, already-stored fields only
  - returns NULL/None for anything not stored, never a fabricated value
  - labels findings CONFIRMED / POSSIBLE / INSUFFICIENT DATA where the
    calling report layer (routes/diagnostics.py or the written-up findings)
    interprets them — this module reports numbers and sample sizes, not
    verdicts, so the labeling logic stays auditable in one place (the
    final report), not scattered across report functions.

Complements, not duplicates, trade_reports.py: confidence_calibration(),
grade_calibration(), entry_quality_performance(),
momentum_score_bucket_performance(), signal_direction_counts(),
direction_breakdown(), feature_importance(), evidence_coverage(),
momentum_vs_runup(), momentum_vs_time_to_tp1() already exist there and are
reused here, not reimplemented.
"""

import statistics
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.engine import trade_reports
from app.models.db_models import ScanSnapshot, TradeOutcome

_RESOLVED_STATUSES = ("closed_win", "closed_loss", "closed_stale")
_TRADED_STATUSES = ("closed_win", "closed_loss")
_MIN_GROUP_SAMPLE = 3


def _resolved_rows(traded_only: bool = False) -> list[TradeOutcome]:
    session = SessionLocal()
    try:
        statuses = _TRADED_STATUSES if traded_only else _RESOLVED_STATUSES
        return session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(statuses))).scalars().all()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. Complete trade autopsy
# ---------------------------------------------------------------------------

def _tp_sl_classification(r: TradeOutcome) -> str:
    """A-G per the requested taxonomy. Uses only stored boolean/timestamp
    fields — entry_hit/tp1_hit/tp2_hit/tp3_hit/stop_hit and tp1_before_stop
    (already computed at close time in trade_outcomes.py), never inferred
    from current price."""
    if not r.entry_hit:
        return "F: entry never triggered"
    if r.status == "closed_stale":
        return "G: other (never entered / expired)"
    if r.tp3_hit and not r.stop_hit:
        return "C: TP3 before SL"
    if r.tp2_hit and not r.stop_hit:
        return "B: TP2 before SL"
    if r.tp1_hit and r.stop_hit:
        return "E: TP1 then reversal to SL"
    if r.tp1_hit and not r.stop_hit:
        return "A: TP1 before SL"
    if r.stop_hit and not r.tp1_hit:
        return "D: SL before TP1"
    return "G: other"


def _why_narrative(r: TradeOutcome) -> dict:
    """Deterministic, template-built narrative — never asks Claude. Splits
    "what the system believed" from "what happened" using only stored
    fields; every sub-answer is either a stored fact or an explicit
    NOT STORED, never inferred."""
    believed = {
        "score": r.score, "confidence": r.confidence, "grade": r.grade,
        "key_score_component": r.key_score_component,
        "ml_probability": r.ml_probability, "historic_probability": r.historic_probability,
        "entry_quality": r.entry_quality,
        "reasons_for": r.reasons_for, "reasons_against": r.reasons_against,
    }
    happened = {
        "status": r.status, "realized_return_pct": r.realized_return_pct,
        "max_runup_pct": r.max_runup_pct, "max_drawdown_pct": r.max_drawdown_pct,
        "tp_sl_path": _tp_sl_classification(r),
        "holding_minutes": r.holding_minutes,
    }
    was_late = None
    if r.entry_quality is not None:
        was_late = r.entry_quality in ("late", "exhausted")
    reasonable_stop = None
    if r.entry and r.stop_loss:
        risk_pct = abs(r.entry - r.stop_loss) / r.entry * 100
        reasonable_stop = f"{risk_pct:.2f}% risk from entry (no fixed 'reasonable' threshold defined — reported for your own judgment)"
    correct_signals = [k for k in ("trend", "structure", "volume", "funding") if getattr(r, f"{k}_score", 0) and getattr(r, f"{k}_score") > 0]
    return {
        "what_system_believed": believed,
        "what_actually_happened": happened,
        "signals_that_scored_positively": correct_signals,
        "was_entry_late_or_exhausted": was_late if was_late is not None else "NOT STORED (entry_quality field is null for this trade — predates the feature)",
        "stop_distance_from_entry": reasonable_stop,
        "target_realistic": (
            f"TP1 was {abs((r.tp1 - r.entry) / r.entry * 100):.2f}% away from entry" if r.tp1 and r.entry else "NULL — no TP1 stored"
        ),
        "regime_at_entry": r.market_regime,
        "note": "This narrative states stored facts and simple derived ratios only — it does not diagnose causation.",
    }


def trade_autopsies() -> list[dict]:
    """One full record per resolved trade with every requested field —
    NULL/NOT STORED where the column genuinely doesn't exist or wasn't
    populated for that trade (older rows predate confidence/grade/
    entry_indicators/entry_quality). macd_hist/cmf/mfi/bb_pct at entry are
    NOT STORED anywhere per-trade today — entry_indicators only captures
    rsi14/stoch_rsi/adx14/EMA-distances (see trade_outcomes.py:
    _capture_entry_indicators) — reported honestly as NOT STORED rather
    than reconstructed from current price data, which would violate the
    no-look-ahead rule."""
    rows = _resolved_rows()
    out = []
    for r in rows:
        ind = r.entry_indicators or {}
        out.append({
            "symbol": r.symbol, "trade_id": r.id, "direction": r.direction,
            "created_at": r.created_at, "entry_time": r.entry_time, "exit_time": r.exit_time,
            "entry": r.entry, "stop_loss": r.stop_loss, "tp1": r.tp1, "tp2": r.tp2, "tp3": r.tp3,
            "score": r.score, "confidence": r.confidence, "grade": r.grade,
            "ml_probability": r.ml_probability, "historic_probability": r.historic_probability,
            "market_regime": r.market_regime, "entry_quality": r.entry_quality,
            "trend_score": r.trend_score, "momentum_score": r.momentum_score,
            "volume_score": r.volume_score, "funding_score": r.funding_score,
            "structure_score": r.structure_score, "risk_penalty": r.risk_score,
            "rsi14": ind.get("rsi14"), "stoch_rsi": ind.get("stoch_rsi"), "adx14": ind.get("adx14"),
            "macd_hist": "NOT STORED (entry_indicators does not capture this)",
            "cmf": "NOT STORED (entry_indicators does not capture this)",
            "mfi": "NOT STORED (entry_indicators does not capture this)",
            "bb_pct": "NOT STORED (entry_indicators does not capture this)",
            "atr_distance_to_ema20": ind.get("atr_distance_to_ema20"),
            "distance_to_ema20_pct": ind.get("distance_to_ema20_pct"),
            "distance_to_ema50_pct": ind.get("distance_to_ema50_pct"),
            "distance_to_ema200_pct": ind.get("distance_to_ema200_pct"),
            "mfe_pct": r.max_runup_pct, "mae_pct": r.max_drawdown_pct,
            "return_pct": r.realized_return_pct, "holding_minutes": r.holding_minutes,
            "final_outcome": r.status,
            "exit_reason": (
                "stop" if r.stop_hit and not (r.tp2_hit or r.tp3_hit or (r.tp1_hit and r.tp2 is None and r.tp3 is None))
                else "target" if r.status == "closed_win"
                else "never_entered" if not r.entry_hit
                else "NOT STORED (no explicit exit_reason column — derived here from status/hit flags)"
            ),
            "tp_sl_path": _tp_sl_classification(r),
            "autopsy": _why_narrative(r),
        })
    return out


# ---------------------------------------------------------------------------
# 2. TP/SL path analysis
# ---------------------------------------------------------------------------

def tp_sl_path_analysis() -> dict:
    rows = _resolved_rows()
    n = len(rows)
    if n == 0:
        return {"sample_size": 0, "note": "No resolved trades yet."}

    classifications = defaultdict(int)
    for r in rows:
        classifications[_tp_sl_classification(r)] += 1

    entered = [r for r in rows if r.entry_hit]
    n_entered = len(entered)
    stopped_before_tp1 = sum(1 for r in entered if r.stop_hit and not r.tp1_hit)
    reached_tp1 = sum(1 for r in entered if r.tp1_hit)
    reached_tp2 = sum(1 for r in entered if r.tp2_hit)
    reached_tp3 = sum(1 for r in entered if r.tp3_hit)
    tp1_then_reversed = sum(1 for r in entered if r.tp1_hit and r.stop_hit)

    mfe = [r.max_runup_pct for r in entered if r.max_runup_pct is not None]
    mae = [r.max_drawdown_pct for r in entered if r.max_drawdown_pct is not None]

    return {
        "sample_size": n,
        "entered_sample_size": n_entered,
        "classification_counts": dict(classifications),
        "pct_stopped_before_tp1": round(stopped_before_tp1 / n_entered * 100, 1) if n_entered else None,
        "pct_reaching_tp1": round(reached_tp1 / n_entered * 100, 1) if n_entered else None,
        "pct_reaching_tp2": round(reached_tp2 / n_entered * 100, 1) if n_entered else None,
        "pct_reaching_tp3": round(reached_tp3 / n_entered * 100, 1) if n_entered else None,
        "pct_tp1_then_reversed_to_stop": round(tp1_then_reversed / n_entered * 100, 1) if n_entered else None,
        "average_mfe_pct": round(statistics.mean(mfe), 2) if mfe else None,
        "average_mae_pct": round(statistics.mean(mae), 2) if mae else None,
        "mfe_mae_ratio": (
            round(abs(statistics.mean(mfe) / statistics.mean(mae)), 2)
            if mfe and mae and statistics.mean(mae) != 0 else None
        ),
        "note": f"n={n} resolved trades — far below any threshold for a reliable rate estimate.",
    }


# ---------------------------------------------------------------------------
# 4b. Momentum interaction (cross-tabulation) — extends
#     trade_reports.momentum_score_bucket_performance() rather than
#     duplicating it; that function reports momentum alone, this adds the
#     structure/RSI/ATR cross-tab the spec explicitly asks for.
# ---------------------------------------------------------------------------

def momentum_interaction_analysis(min_sample: int = 3) -> dict:
    rows = _resolved_rows()
    high_momentum = [r for r in rows if r.momentum_score >= 12]
    low_momentum = [r for r in rows if r.momentum_score < 12]

    def _slice(rows_subset, label):
        n = len(rows_subset)
        if n < min_sample:
            return {"sample_size": n, "note": f"Insufficient sample size — need >= {min_sample}, have {n}."}
        traded = [r for r in rows_subset if r.status in _TRADED_STATUSES]
        wins = sum(1 for r in traded if r.status == "closed_win")
        returns = [r.realized_return_pct for r in traded if r.realized_return_pct is not None]
        weak_structure = sum(1 for r in rows_subset if r.structure_score < 8)
        return {
            "sample_size": n, "win_rate_pct": round(wins / len(traded) * 100, 1) if traded else None,
            "average_return_pct": round(statistics.mean(returns), 2) if returns else None,
            "pct_with_weak_structure_score": round(weak_structure / n * 100, 1),
        }

    return {
        "high_momentum_ge_12": _slice(high_momentum, "high"),
        "low_momentum_lt_12": _slice(low_momentum, "low"),
        "note": (
            "Cross-tabulates momentum_score against structure_score specifically — "
            "answers 'is high momentum alone the issue, or high momentum combined "
            "with weak structure.' See trade_reports.momentum_score_bucket_performance() "
            "for the plain momentum-only buckets this extends."
        ),
    }


# ---------------------------------------------------------------------------
# 5b. ML probability calibration — separate from trade_reports.
#     confidence_calibration() (confidence is a different, independently
#     computed number from ml_probability; see confidence.py).
# ---------------------------------------------------------------------------

_ML_PROB_BUCKETS = [(0.0, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 1.01)]


def ml_probability_calibration(min_sample: int = 5) -> dict:
    rows = [r for r in _resolved_rows() if r.ml_probability is not None]
    if len(rows) < min_sample:
        return {
            "sample_size": len(rows),
            "note": f"Need >= {min_sample} resolved trades with a stored ml_probability; have {len(rows)}. ML predictions were unavailable for most/all trades in this sample.",
        }
    buckets = []
    for lo, hi in _ML_PROB_BUCKETS:
        group = [r for r in rows if lo <= r.ml_probability < hi]
        entry = {"range": f"{lo:.1f}-{min(hi, 1.0):.1f}", "sample_size": len(group)}
        if len(group) < min_sample:
            entry["note"] = f"Insufficient sample size — need >= {min_sample}, have {len(group)}."
        else:
            traded = [r for r in group if r.status in _TRADED_STATUSES]
            wins = sum(1 for r in traded if r.status == "closed_win")
            entry["actual_win_rate_pct"] = round(wins / len(traded) * 100, 1) if traded else None
        buckets.append(entry)
    return {"total_eligible": len(rows), "buckets": buckets}


# ---------------------------------------------------------------------------
# 6. Regime performance — parallel to trade_reports.direction_breakdown(),
#    which does this for direction; nothing existing does it for regime
#    individually (monthly_breakdown only surfaces the single BEST regime).
# ---------------------------------------------------------------------------

def regime_performance(min_sample: int = 3) -> dict:
    rows = _resolved_rows()
    by_regime: dict[str, list[TradeOutcome]] = defaultdict(list)
    for r in rows:
        by_regime[r.market_regime or "unknown"].append(r)

    result = {}
    for regime, group in by_regime.items():
        traded = [r for r in group if r.status in _TRADED_STATUSES]
        if len(group) < min_sample:
            result[regime] = {"sample_size": len(group), "note": f"Insufficient sample size — need >= {min_sample}, have {len(group)}."}
            continue
        wins = sum(1 for r in traded if r.status == "closed_win")
        tp1 = sum(1 for r in group if r.tp1_hit)
        returns = [r.realized_return_pct for r in traded if r.realized_return_pct is not None]
        mfe = [r.max_runup_pct for r in group if r.max_runup_pct is not None]
        mae = [r.max_drawdown_pct for r in group if r.max_drawdown_pct is not None]
        result[regime] = {
            "sample_size": len(group),
            "win_rate_pct": round(wins / len(traded) * 100, 1) if traded else None,
            "tp1_rate_pct": round(tp1 / len(group) * 100, 1),
            "average_return_pct": round(statistics.mean(returns), 2) if returns else None,
            "average_mfe_pct": round(statistics.mean(mfe), 2) if mfe else None,
            "average_mae_pct": round(statistics.mean(mae), 2) if mae else None,
        }
    return result


# ---------------------------------------------------------------------------
# 9. Correlation / concentration analysis
# ---------------------------------------------------------------------------

def correlation_concentration_analysis(window_ms: int = 4 * 3_600_000) -> dict:
    """Groups trades whose entry_time falls within the same rolling window
    (default 4h) — flags them as POTENTIALLY correlated bets on the same
    market move, not independent predictions. True BTC-trend-at-entry for
    each historical trade is NOT STORED per-trade (MarketRegimeState is a
    single current-state row, overwritten every cycle) — market_regime
    (risk_on/risk_off/mixed), which IS stored per-trade, is used as the
    best available proxy and reported as such, not as literal BTC trend."""
    rows = [r for r in _resolved_rows() if r.entry_time]
    rows.sort(key=lambda r: r.entry_time)

    clusters = []
    used = set()
    for i, r in enumerate(rows):
        if r.id in used:
            continue
        cluster = [r]
        used.add(r.id)
        for other in rows[i + 1:]:
            if other.id in used:
                continue
            if other.entry_time - r.entry_time <= window_ms:
                cluster.append(other)
                used.add(other.id)
        if len(cluster) > 1:
            clusters.append(cluster)

    cluster_summaries = []
    for cluster in clusters:
        losses_in_cluster = sum(1 for r in cluster if r.status == "closed_loss")
        cluster_summaries.append({
            "symbols": [r.symbol for r in cluster],
            "entry_times": [r.entry_time for r in cluster],
            "directions": [r.direction for r in cluster],
            "market_regime_at_entry": [r.market_regime for r in cluster],
            "losses_in_cluster": losses_in_cluster,
            "cluster_size": len(cluster),
        })

    max_simultaneous = max((len(c) for c in clusters), default=1)
    total_in_clusters = sum(len(c) for c in clusters)

    return {
        "total_resolved_trades": len(rows),
        "window_hours": window_ms / 3_600_000,
        "clusters_found": len(clusters),
        "trades_inside_a_cluster": total_in_clusters,
        "trades_independent_of_any_cluster": len(rows) - total_in_clusters,
        "max_simultaneous_entries_within_window": max_simultaneous,
        "cluster_detail": cluster_summaries,
        "note": (
            "'market_regime_at_entry' is the stored risk_on/risk_off/mixed label, "
            "the best available proxy for market-wide conditions — true per-trade "
            "BTC trend at entry is NOT STORED historically (MarketRegimeState keeps "
            "only the current cycle's state, overwritten each cycle). "
            "This identifies POTENTIAL correlation (same-window entries), not proven "
            "causation — with n={} resolved trades, do not treat cluster loss rates "
            "as validated.".format(len(rows))
        ),
    }


# ---------------------------------------------------------------------------
# 10. Time-of-day / day-of-week
# ---------------------------------------------------------------------------

def time_of_day_analysis() -> dict:
    """UTC only — entry_time is epoch ms with no stored timezone, so UTC is
    the only honest interpretation. Purely descriptive; explicitly does not
    claim causality per the request."""
    rows = [r for r in _resolved_rows() if r.entry_time]
    if not rows:
        return {"sample_size": 0, "note": "No resolved trades with a stored entry_time yet."}

    by_hour: dict[int, list[TradeOutcome]] = defaultdict(list)
    by_dow: dict[str, list[TradeOutcome]] = defaultdict(list)
    for r in rows:
        dt = datetime.fromtimestamp(r.entry_time / 1000, tz=timezone.utc)
        by_hour[dt.hour].append(r)
        by_dow[dt.strftime("%A")].append(r)

    def _bucket_stats(group: list[TradeOutcome]) -> dict:
        traded = [r for r in group if r.status in _TRADED_STATUSES]
        wins = sum(1 for r in traded if r.status == "closed_win")
        returns = [r.realized_return_pct for r in traded if r.realized_return_pct is not None]
        return {
            "sample_size": len(group),
            "win_rate_pct": round(wins / len(traded) * 100, 1) if traded else None,
            "tp1_rate_pct": round(sum(1 for r in group if r.tp1_hit) / len(group) * 100, 1),
            "average_return_pct": round(statistics.mean(returns), 2) if returns else None,
        }

    return {
        "sample_size": len(rows),
        "by_hour_utc": {str(h): _bucket_stats(g) for h, g in sorted(by_hour.items())},
        "by_day_of_week": {d: _bucket_stats(g) for d, g in by_dow.items()},
        "note": (
            f"n={len(rows)} total, spread across up to 24 hour buckets and 7 day "
            "buckets — each individual bucket has an even smaller n. This can only "
            "ever describe possible clustering, never causality, at this volume."
        ),
    }


# ---------------------------------------------------------------------------
# 11. Holding-time analysis
# ---------------------------------------------------------------------------

_HOLDING_BUCKETS = [
    (0, 60, "<1 hour"), (60, 240, "1-4 hours"), (240, 720, "4-12 hours"),
    (720, 1440, "12-24 hours"), (1440, 4320, "1-3 days"), (4320, float("inf"), ">3 days"),
]


def holding_time_analysis() -> dict:
    rows = [r for r in _resolved_rows() if r.holding_minutes is not None]
    if not rows:
        return {"sample_size": 0, "note": "No resolved trades with a stored holding_minutes yet."}

    buckets = []
    for lo, hi, label in _HOLDING_BUCKETS:
        group = [r for r in rows if lo <= r.holding_minutes < hi]
        traded = [r for r in group if r.status in _TRADED_STATUSES]
        wins = sum(1 for r in traded if r.status == "closed_win")
        returns = [r.realized_return_pct for r in traded if r.realized_return_pct is not None]
        mfe = [r.max_runup_pct for r in group if r.max_runup_pct is not None]
        mae = [r.max_drawdown_pct for r in group if r.max_drawdown_pct is not None]
        buckets.append({
            "holding_range": label, "sample_size": len(group),
            "win_rate_pct": round(wins / len(traded) * 100, 1) if traded else None,
            "tp1_rate_pct": round(sum(1 for r in group if r.tp1_hit) / len(group) * 100, 1) if group else None,
            "average_return_pct": round(statistics.mean(returns), 2) if returns else None,
            "average_mfe_pct": round(statistics.mean(mfe), 2) if mfe else None,
            "average_mae_pct": round(statistics.mean(mae), 2) if mae else None,
        })
    return {"sample_size": len(rows), "buckets": buckets}


# ---------------------------------------------------------------------------
# 12/13. Stop and target analysis (R:R, distances, realism)
# ---------------------------------------------------------------------------

def stop_target_analysis() -> dict:
    rows = [r for r in _resolved_rows() if r.entry and r.stop_loss]
    if not rows:
        return {"sample_size": 0, "note": "No resolved trades with entry+stop stored."}

    per_trade = []
    risk_pcts, rr_ratios = [], []
    immediate_stops = 0  # stopped without ever getting close to TP1
    near_miss_tp1 = 0  # MFE reached >=80% of the TP1 distance before stopping

    for r in rows:
        risk_pct = abs(r.entry - r.stop_loss) / r.entry * 100
        reward_pct = abs(r.tp1 - r.entry) / r.entry * 100 if r.tp1 else None
        rr = round(reward_pct / risk_pct, 2) if reward_pct and risk_pct else None
        risk_pcts.append(risk_pct)
        if rr is not None:
            rr_ratios.append(rr)

        tp1_progress_pct = None
        if reward_pct and r.max_runup_pct is not None:
            tp1_progress_pct = round(min(100, max(0, r.max_runup_pct / reward_pct * 100)), 1)
            if r.status == "closed_loss" and not r.tp1_hit:
                if tp1_progress_pct < 15:
                    immediate_stops += 1
                elif tp1_progress_pct >= 80:
                    near_miss_tp1 += 1

        per_trade.append({
            "symbol": r.symbol, "trade_id": r.id,
            "risk_pct": round(risk_pct, 2), "reward_to_tp1_pct": round(reward_pct, 2) if reward_pct else None,
            "risk_reward_ratio": rr, "pct_of_tp1_distance_reached": tp1_progress_pct,
            "tp2_distance_pct": round(abs(r.tp2 - r.entry) / r.entry * 100, 2) if r.tp2 else None,
            "tp3_distance_pct": round(abs(r.tp3 - r.entry) / r.entry * 100, 2) if r.tp3 else None,
        })

    losses_with_data = [t for t in per_trade if t["pct_of_tp1_distance_reached"] is not None]

    return {
        "sample_size": len(rows),
        "per_trade": per_trade,
        "average_risk_pct": round(statistics.mean(risk_pcts), 2) if risk_pcts else None,
        "average_risk_reward_ratio": round(statistics.mean(rr_ratios), 2) if rr_ratios else None,
        "immediate_stops_count": immediate_stops,
        "immediate_stops_note": (
            f"{immediate_stops} of {len(losses_with_data)} losses with MFE data never reached "
            "15% of the TP1 distance before stopping — 'immediate,' not a gradual failure."
        ),
        "near_miss_tp1_count": near_miss_tp1,
        "near_miss_tp1_note": (
            f"{near_miss_tp1} of {len(losses_with_data)} losses with MFE data reached >=80% of the "
            "TP1 distance before reversing to the stop — close, not systematically too tight or wrong-direction."
        ),
        "note": (
            "Analysis only — this does not conclude stops are too tight or too wide; "
            "that would require comparing against a counterfactual with a different "
            "stop, which this function does not simulate."
        ),
    }


# ---------------------------------------------------------------------------
# 14. Feature interaction discovery
# ---------------------------------------------------------------------------

_INTERACTION_CHECKS = {
    "momentum_high_bb_extreme": lambda r, ind: r.momentum_score >= 12 and ind.get("stoch_rsi") is not None and (ind.get("stoch_rsi", 0) > 0.9 or ind.get("stoch_rsi", 1) < 0.1),
    "momentum_high_weak_structure": lambda r, ind: r.momentum_score >= 12 and r.structure_score < 8,
    "high_atr_low_structure": lambda r, ind: ind.get("atr_distance_to_ema20") is not None and abs(ind.get("atr_distance_to_ema20", 0)) > 2.5 and r.structure_score < 8,
    "trend_confirmed_no_structure": lambda r, ind: r.trend_score >= 15 and r.structure_score < 6,
    "high_confidence_no_history": lambda r, ind: (r.confidence or 0) >= 65 and r.historic_probability is None,
    "high_score_low_structure": lambda r, ind: r.score >= 60 and r.structure_score < 8,
    "high_rsi_extended": lambda r, ind: ind.get("rsi14") is not None and ind.get("rsi14", 0) > 70,
    "risk_on_regime_negative_risk_penalty": lambda r, ind: r.market_regime == "risk_on" and r.risk_score < -3,
    "negative_funding_score_taken_anyway": lambda r, ind: r.funding_score == 0,
    "zero_ml_zero_history": lambda r, ind: r.ml_probability is None and r.historic_probability is None,
}


def feature_interaction_discovery(min_sample: int = 3) -> dict:
    """Searches ALL predefined interaction checks against ALL resolved
    trades — not cherry-picked to explain known losses. Every check runs
    against the full set; only sample size decides whether a result is
    reportable. Add new checks to _INTERACTION_CHECKS to extend, don't
    special-case individual trades."""
    rows = _resolved_rows()
    results = {}
    for name, check in _INTERACTION_CHECKS.items():
        matched = [r for r in rows if check(r, r.entry_indicators or {})]
        n = len(matched)
        if n < min_sample:
            results[name] = {"sample_size": n, "verdict": "INSUFFICIENT DATA", "note": f"Need >= {min_sample}, have {n}."}
            continue
        traded = [r for r in matched if r.status in _TRADED_STATUSES]
        losses = sum(1 for r in traded if r.status == "closed_loss")
        wins = len(traded) - losses
        returns = [r.realized_return_pct for r in traded if r.realized_return_pct is not None]
        mfe = [r.max_runup_pct for r in matched if r.max_runup_pct is not None]
        mae = [r.max_drawdown_pct for r in matched if r.max_drawdown_pct is not None]
        loss_rate = round(losses / len(traded) * 100, 1) if traded else None
        verdict = "POSSIBLE" if n >= min_sample else "INSUFFICIENT DATA"
        # Never "CONFIRMED" below a real statistical floor — n<10 per pattern
        # cannot honestly claim confirmation regardless of loss rate.
        if n >= 10:
            verdict = "POSSIBLE"  # still not CONFIRMED — see module-level rule: no pattern is CONFIRMED from this dataset size
        results[name] = {
            "sample_size": n, "win_rate_pct": round(wins / len(traded) * 100, 1) if traded else None,
            "loss_rate_pct": loss_rate,
            "average_return_pct": round(statistics.mean(returns), 2) if returns else None,
            "average_mfe_pct": round(statistics.mean(mfe), 2) if mfe else None,
            "average_mae_pct": round(statistics.mean(mae), 2) if mae else None,
            "verdict": verdict,
        }
    return {
        "total_resolved_trades": len(rows),
        "patterns": results,
        "note": (
            "Every listed pattern was checked against the full resolved-trade set, "
            "not selected after the fact to explain known losses. No pattern is "
            "labeled CONFIRMED at this sample size — see the top-level findings "
            "report for the CONFIRMED/POSSIBLE/INSUFFICIENT DATA rule."
        ),
    }


# ---------------------------------------------------------------------------
# 15. Failure clustering
# ---------------------------------------------------------------------------

_FAILURE_TAGS = {
    "ENTRY_TOO_LATE": lambda r, ind: r.entry_quality in ("late", "exhausted"),
    "OVEREXTENSION": lambda r, ind: ind.get("atr_distance_to_ema20") is not None and abs(ind.get("atr_distance_to_ema20", 0)) > 2.5,
    "WEAK_STRUCTURE": lambda r, ind: r.structure_score < 8,
    "INSUFFICIENT_CONFIRMATION": lambda r, ind: r.trend_score < 15 or (r.confidence is not None and r.confidence < 60),
    "TARGET_TOO_FAR": lambda r, ind: r.tp1 and r.entry and abs(r.tp1 - r.entry) / r.entry > 0.08 and not r.tp1_hit,
    "STOP_TOO_TIGHT": lambda r, ind: r.max_runup_pct is not None and r.tp1 and r.entry and r.max_runup_pct > 0 and (r.max_runup_pct / (abs(r.tp1 - r.entry) / r.entry * 100)) > 0.8 and not r.tp1_hit,
    "MARKET_WIDE_SELLOFF": lambda r, ind: r.market_regime == "risk_off",
    "FALSE_BREAKOUT": lambda r, ind: r.structure_score >= 8 and r.max_runup_pct is not None and r.max_runup_pct < 1.0,
    "TREND_REVERSAL": lambda r, ind: r.tp1_hit and r.stop_hit,
    "LOW_LIQUIDITY": lambda r, ind: r.liquidity_score < -2,
}


def failure_clustering() -> dict:
    """Multi-tag classification of every LOSS against deterministic rules
    over already-stored fields. A trade can (and often does) get multiple
    tags — this is not a mutually-exclusive taxonomy."""
    losses = [r for r in _resolved_rows() if r.status == "closed_loss"]
    if not losses:
        return {"sample_size": 0, "note": "No resolved losses yet."}

    per_trade = []
    tag_counts: dict[str, int] = defaultdict(int)
    for r in losses:
        ind = r.entry_indicators or {}
        tags = [name for name, check in _FAILURE_TAGS.items() if check(r, ind)]
        if not tags:
            tags = ["UNKNOWN"]
        for t in tags:
            tag_counts[t] += 1
        per_trade.append({"symbol": r.symbol, "trade_id": r.id, "tags": tags})

    return {
        "total_losses": len(losses),
        "tag_counts": dict(sorted(tag_counts.items(), key=lambda kv: -kv[1])),
        "per_trade": per_trade,
        "note": f"n={len(losses)} losses, multi-tag — counts sum to more than {len(losses)} where a trade matched multiple failure modes.",
    }


# ---------------------------------------------------------------------------
# 16. "What would have saved this trade?" — deterministic counterfactual
#     FILTERS (would a stricter rule have excluded this trade), separate
#     from "should this become a rule."
# ---------------------------------------------------------------------------

_HYPOTHETICAL_FILTERS = {
    "require_fresh_bos_or_fvg": lambda r, ind: r.structure_score < 11,  # would have excluded if structure wasn't strong
    "reject_high_atr": lambda r, ind: ind.get("atr_distance_to_ema20") is not None and abs(ind.get("atr_distance_to_ema20", 0)) > 2.5,
    "reject_overbought": lambda r, ind: ind.get("rsi14") is not None and ind.get("rsi14", 0) > 75,
    "require_historical_evidence": lambda r, ind: r.historic_probability is None,
    "require_ml_support": lambda r, ind: r.ml_probability is None,
    "require_multi_timeframe_confirmation": lambda r, ind: r.trend_score < 20,
    "reject_entry_quality_late_or_worse": lambda r, ind: r.entry_quality in ("late", "exhausted", "invalid") if r.entry_quality else "NOT STORED",
}


def what_would_have_saved_this_trade() -> dict:
    """For every LOSS, checks whether each hypothetical filter WOULD have
    excluded it (a fact derivable from stored data), explicitly separated
    from whether that filter should become a real rule (a judgment call
    requiring far more data, made in the top-level findings report, not
    here)."""
    losses = [r for r in _resolved_rows() if r.status == "closed_loss"]
    per_trade = []
    filter_would_have_excluded_count: dict[str, int] = defaultdict(int)

    for r in losses:
        ind = r.entry_indicators or {}
        would_exclude = {}
        for name, check in _HYPOTHETICAL_FILTERS.items():
            result = check(r, ind)
            would_exclude[name] = result
            if result is True:
                filter_would_have_excluded_count[name] += 1
        per_trade.append({"symbol": r.symbol, "trade_id": r.id, "would_have_been_excluded_by": would_exclude})

    return {
        "total_losses": len(losses),
        "per_trade": per_trade,
        "filter_exclusion_counts": dict(filter_would_have_excluded_count),
        "note": (
            "'Would have excluded this specific loss' is a fact about stored data, "
            "not evidence the filter should become a real rule — a filter that "
            "excludes every loss usually also excludes wins we don't get to see in "
            "this dataset (survivorship). See the findings report's distinction "
            "between 'would have prevented this loss' and 'evidence for a general rule.'"
        ),
    }


# ---------------------------------------------------------------------------
# 17. Counterfactual entry-shift (APPROXIMATED, clearly labeled)
# ---------------------------------------------------------------------------

def counterfactual_entry_shift() -> dict:
    """COUNTERFACTUAL, approximated — NOT a real backtest. True path-replay
    would require re-simulating the trade against real OHLCV candles with
    a shifted entry; this project's stop/target close logic is
    scan-interval-driven (see trade_outcomes.py), not tick-level, so an
    exact replay isn't available without materially more engineering.
    Instead: uses the ALREADY-OBSERVED max_favorable_price/max_adverse_price
    (the real high/low actually reached) to ask "if entry had been X% more
    favorable, would that same observed adverse extreme still have reached
    the (proportionally shifted) stop?" This assumes the adverse extreme
    would occur at the same price regardless of entry — a simplification,
    not a real simulation, and is labeled as such in every returned row."""
    losses = [r for r in _resolved_rows() if r.status == "closed_loss" and r.entry and r.stop_loss and r.max_adverse_price is not None]
    shifts_pct = [0.01, 0.02, 0.03]
    results = []
    for r in losses:
        is_long = r.direction == "long"
        row_result = {"symbol": r.symbol, "trade_id": r.id, "actual_return_pct": r.realized_return_pct, "shifts": {}}
        for shift in shifts_pct:
            # Long: a "better" entry is LOWER (waiting for a pullback).
            hypothetical_entry = r.entry * (1 - shift) if is_long else r.entry * (1 + shift)
            still_hits_stop = (
                r.max_adverse_price <= r.stop_loss if is_long else r.max_adverse_price >= r.stop_loss
            )
            # Same absolute stop distance, shifted from the new entry.
            stop_distance = abs(r.entry - r.stop_loss)
            hypothetical_stop = hypothetical_entry - stop_distance if is_long else hypothetical_entry + stop_distance
            hypothetical_still_stopped = (
                r.max_adverse_price <= hypothetical_stop if is_long else r.max_adverse_price >= hypothetical_stop
            )
            row_result["shifts"][f"{int(shift*100)}pct"] = {
                "hypothetical_entry": round(hypothetical_entry, 6),
                "hypothetical_stop": round(hypothetical_stop, 6),
                "would_still_have_stopped_out": hypothetical_still_stopped,
                "label": "COUNTERFACTUAL — approximated from observed MFE/MAE, not a real path replay",
            }
        results.append(row_result)

    return {
        "sample_size": len(results),
        "per_trade": results,
        "note": (
            "COUNTERFACTUAL, approximated. Assumes the same adverse price extreme "
            "would still occur regardless of entry timing, which is a simplification, "
            "not a real simulation. Do not treat 'would_still_have_stopped_out: false' "
            "as proof a pullback entry would have worked — it only means, under this "
            "approximation, the observed adverse move wouldn't have reached the "
            "shifted stop level."
        ),
    }


# ---------------------------------------------------------------------------
# 18. Ranking backtest — LIMITED to published/resolved trades' own rank at
#     issuance (ScanSnapshot.rank), since only published symbols have a
#     real win/loss outcome. NOT a full-universe top-N simulation.
# ---------------------------------------------------------------------------

def ranking_backtest() -> dict:
    session = SessionLocal()
    try:
        rows = _resolved_rows()
        result_by_top_n = {n: {"wins": 0, "traded": 0, "total": 0, "returns": []} for n in (1, 3, 5, 10)}
        matched = 0
        for r in rows:
            if not r.created_at:
                continue
            snap = session.execute(
                select(ScanSnapshot)
                .where(ScanSnapshot.symbol == r.symbol, ScanSnapshot.timestamp <= r.created_at)
                .order_by(ScanSnapshot.timestamp.desc())
                .limit(1)
            ).scalar_one_or_none()
            if snap is None:
                continue
            matched += 1
            for n in (1, 3, 5, 10):
                if snap.rank < n:
                    result_by_top_n[n]["total"] += 1
                    if r.status in _TRADED_STATUSES:
                        result_by_top_n[n]["traded"] += 1
                        if r.status == "closed_win":
                            result_by_top_n[n]["wins"] += 1
                        if r.realized_return_pct is not None:
                            result_by_top_n[n]["returns"].append(r.realized_return_pct)
    finally:
        session.close()

    summary = {}
    for n, data in result_by_top_n.items():
        summary[f"top_{n}"] = {
            "sample_size": data["total"],
            "win_rate_pct": round(data["wins"] / data["traded"] * 100, 1) if data["traded"] else None,
            "average_return_pct": round(statistics.mean(data["returns"]), 2) if data["returns"] else None,
        }

    return {
        "resolved_trades_matched_to_a_rank": matched,
        "total_resolved_trades": len(rows),
        "by_top_n": summary,
        "note": (
            "LIMITED: only re-slices the trades that were ACTUALLY PUBLISHED, by "
            "their own rank at issuance (from ScanSnapshot). This is NOT a full "
            "top-N-of-the-whole-universe simulation — non-published, lower-ranked "
            "symbols never got a trade_plan, so there is no real win/loss outcome "
            "to replay for them. Answers 'among trades we actually took, did the "
            "highest-ranked ones do better,' not 'what if we'd only ever looked at "
            "rank 1.'"
        ),
    }


# ---------------------------------------------------------------------------
# 19. Daily market-regime report
# ---------------------------------------------------------------------------

def daily_market_regime_report(regime: dict | None, day_ms: int = 86_400_000) -> dict:
    import time

    from app.models.db_models import LiveOpportunity

    now_ms = int(time.time() * 1000)
    session = SessionLocal()
    try:
        latest_ts = session.execute(select(ScanSnapshot.timestamp).order_by(ScanSnapshot.timestamp.desc()).limit(1)).scalar_one_or_none()
        latest_scans = []
        if latest_ts is not None:
            latest_scans = session.execute(select(ScanSnapshot).where(ScanSnapshot.timestamp == latest_ts)).scalars().all()

        yesterday_ts = session.execute(
            select(ScanSnapshot.timestamp)
            .where(ScanSnapshot.timestamp <= now_ms - day_ms)
            .order_by(ScanSnapshot.timestamp.desc()).limit(1)
        ).scalar_one_or_none()
        yesterday_scans = []
        if yesterday_ts is not None:
            yesterday_scans = session.execute(select(ScanSnapshot).where(ScanSnapshot.timestamp == yesterday_ts)).scalars().all()

        top5 = session.execute(
            select(LiveOpportunity).where(LiveOpportunity.trade_plan.is_not(None)).order_by(LiveOpportunity.score_total.desc()).limit(5)
        ).scalars().all()
    finally:
        session.close()

    long_now = sum(1 for s in latest_scans if s.direction == "long")
    short_now = sum(1 for s in latest_scans if s.direction == "short")
    no_trade_now = sum(1 for s in latest_scans if s.direction == "no_trade")
    long_yday = sum(1 for s in yesterday_scans if s.direction == "long")
    short_yday = sum(1 for s in yesterday_scans if s.direction == "short")

    rejected = [
        {"symbol": s.symbol, "rank": s.rank, "score": s.score_total, "reason": s.rejection_reason}
        for s in latest_scans if s.rejection_reason
    ]

    return {
        "as_of": latest_ts,
        "market_regime": regime,
        "long_candidates": long_now, "short_candidates": short_now, "no_trade_candidates": no_trade_now,
        "top5": [{"symbol": o.symbol, "score": o.score_total} for o in top5],
        "rejected_setups": rejected,
        "open_trades": trade_reports.open_trade_count(),
        "recent_outcomes_24h": trade_reports.performance_digest(now_ms - day_ms, now_ms, "Last 24h"),
        "current_performance_30d": trade_reports.performance_digest(now_ms - 30 * day_ms, now_ms, "Last 30d"),
        "what_changed_since_yesterday": {
            "long_candidates_delta": (long_now - long_yday) if yesterday_scans else "NOT STORED (no scan data from ~24h ago yet)",
            "short_candidates_delta": (short_now - short_yday) if yesterday_scans else "NOT STORED (no scan data from ~24h ago yet)",
        },
    }
