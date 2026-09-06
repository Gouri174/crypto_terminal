"""Trading Engine V2 — Performance Center: read-only analytics only.

Everything here READS TradeOutcome/PredictionSnapshot/ScanSnapshot/
MarketRegimeState and computes statistics. Nothing here writes to those
tables, changes scoring.py's weights, confidence.py's formula, entry/SL/TP
generation, ml_model.py, entry_quality.py's thresholds, or lifecycle.py.
Same contract as forensic_diagnostics.py and trade_reports.py, which this
module complements rather than duplicates:
  - target_conditional_probabilities() (forensic_diagnostics.py) already
    reports aggregate P(TP2|TP1)/P(TP3|TP2) from real TradeOutcome data —
    tp_continuation_analytics() below is per-trade and adds return-to-
    entry/return-to-stop path analysis, which that function doesn't cover.
  - confidence_calibration()/grade_calibration() (trade_reports.py) already
    bucket by confidence/grade — confidence_lab() below adds Brier score
    and Expected Calibration Error on top, using the SAME bucket
    convention this project already settled on elsewhere (50-54...75+).

Nothing here is cached or persisted to a new table. Every function
recomputes from stored rows on each call, matching how every other
diagnostics function in this codebase already works (forensic_diagnostics.py,
trade_reports.py) — this app has no cron/scheduler infra (see
ml_retrain.py's own module docstring for why that's a deliberate choice,
not an oversight), and at current data volumes (hundreds, not millions, of
rows) recomputing on request costs nothing worth caching for.

"Store these as reusable analytics" (TP continuation) is satisfied by
these being ordinary importable functions other code can call — not by
writing results to a new DB table. Adding a table to hold values that are
already cheap to recompute from existing tables would be exactly the kind
of premature abstraction this project's own conventions avoid.
"""

import statistics
from collections import defaultdict

from sqlalchemy import select

from app.db import SessionLocal
from app.engine.background_scanner import load_current_regime
from app.models.db_models import PredictionSnapshot, ScanSnapshot, TradeOutcome

_TRADED_STATUSES = ("closed_win", "closed_loss")
_OPEN_STATUSES = ("pending", "open")
_MIN_GROUP_SAMPLE = 3


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _all_trades() -> list[TradeOutcome]:
    session = SessionLocal()
    try:
        return session.execute(select(TradeOutcome)).scalars().all()
    finally:
        session.close()


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


def _all_snapshots() -> list[PredictionSnapshot]:
    session = SessionLocal()
    try:
        return session.execute(select(PredictionSnapshot)).scalars().all()
    finally:
        session.close()


def _snapshots_for(trade_outcome_id: int) -> list[PredictionSnapshot]:
    session = SessionLocal()
    try:
        return (
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


def _pct(n: float, d: float) -> float | None:
    return round(n / d * 100, 1) if d else None


def _avg(vals) -> float | None:
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def _profit_factor(rows: list[TradeOutcome]) -> float | None:
    rets = [r.realized_return_pct for r in rows if r.realized_return_pct is not None]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    return round(gains / abs(loss), 3) if loss else None


# ---------------------------------------------------------------------------
# 1. Scanner Health Dashboard
# ---------------------------------------------------------------------------

def scanner_health(gap_threshold_minutes: int = 10) -> dict:
    """Heartbeat = the timestamp of every PredictionSnapshot ever recorded
    (one per open/pending TradeOutcome per scan cycle — see
    trade_outcomes.py:update_open_trades()). A gap between two consecutive
    distinct timestamps longer than gap_threshold_minutes means the scanner
    was not running (or had nothing open to check) for that entire span —
    this can't distinguish "process was down" from "there were zero open
    trades that cycle," but either way no monitoring happened, which is the
    thing that matters for stop-execution risk.

    Uptime % is computed only over the OBSERVED span (first to last
    heartbeat) — it says nothing about time before the first trade or
    after the last, which this table has no record of either way."""
    snapshots = _all_snapshots()
    timestamps = sorted(set(s.timestamp for s in snapshots))
    if len(timestamps) < 2:
        return {"note": "Fewer than 2 distinct snapshot timestamps — not enough heartbeat history yet.", "heartbeat_count": len(timestamps)}

    threshold_ms = gap_threshold_minutes * 60_000
    total_span_ms = timestamps[-1] - timestamps[0]

    outages = []
    for a, b in zip(timestamps, timestamps[1:]):
        gap = b - a
        if gap > threshold_ms:
            outages.append({"start": a, "end": b, "duration_minutes": round(gap / 60_000, 1)})

    outage_ms = sum((o["end"] - o["start"]) for o in outages)
    uptime_pct = round((total_span_ms - outage_ms) / total_span_ms * 100, 2) if total_span_ms else None

    all_trades = _all_trades()
    for o in outages:
        affected = [
            t.symbol
            for t in all_trades
            if t.status == "open"
            and t.entry_time is not None
            and t.entry_time <= o["start"]
            and (t.exit_time is None or t.exit_time >= o["start"])
        ]
        # A trade opened DURING the gap (entry_time inside [start, end]) was
        # also unmonitored for whatever remained of the gap after it opened.
        affected += [
            t.symbol
            for t in all_trades
            if t.entry_time is not None
            and o["start"] < t.entry_time < o["end"]
            and t.symbol not in affected
        ]
        o["affected_open_trades"] = sorted(set(affected))

    return {
        "gap_threshold_minutes": gap_threshold_minutes,
        "observed_span_start": timestamps[0],
        "observed_span_end": timestamps[-1],
        "heartbeat_count": len(timestamps),
        "uptime_pct": uptime_pct,
        "total_outages": len(outages),
        "longest_outage_minutes": max((o["duration_minutes"] for o in outages), default=None),
        "average_outage_minutes": _avg([o["duration_minutes"] for o in outages]),
        "outages": outages,
    }


# ---------------------------------------------------------------------------
# 2. Stop Execution Audit
# ---------------------------------------------------------------------------

def _volatility_bucket(row: TradeOutcome) -> str:
    """Prefers the ATR-normalized SL distance captured at issuance
    (entry_indicators.risk_reward.entry_to_sl_atr — only present on trades
    issued after the level-reasoning capture pass) since it's a genuine
    volatility measure; falls back to raw risk_to_sl_pct (available on
    every trade via compute_risk_reward) when the ATR figure isn't stored,
    which is a real but less precise proxy — narrower/wider stops roughly
    track how volatile the instrument was priced as being at entry."""
    rr = (row.entry_indicators or {}).get("risk_reward") or {}
    atr_dist = rr.get("entry_to_sl_atr")
    if atr_dist is not None:
        if atr_dist < 1.0:
            return "<1.0 ATR"
        if atr_dist < 2.0:
            return "1.0-2.0 ATR"
        if atr_dist < 3.0:
            return "2.0-3.0 ATR"
        return ">=3.0 ATR"
    pct_dist = rr.get("risk_to_sl_pct")
    if pct_dist is None:
        return "unknown"
    if pct_dist < 2.0:
        return "<2% (pct proxy)"
    if pct_dist < 5.0:
        return "2-5% (pct proxy)"
    if pct_dist < 10.0:
        return "5-10% (pct proxy)"
    return ">=10% (pct proxy)"


def stop_execution_audit(outage_gap_threshold_minutes: int = 10) -> dict:
    """Slippage = stop_slippage_pct, only ever set at close for a
    stop-triggered exit on trades issued after the V1.1 capture pass — NULL
    (never estimated) on older rows, honestly excluded from every
    distribution below rather than treated as zero."""
    rows = [r for r in _traded_rows() if r.stop_hit and r.stop_slippage_pct is not None]
    no_data_rows = [r for r in _all_trades() if r.stop_hit and r.stop_slippage_pct is None]

    def _distribution(subset: list[TradeOutcome]) -> dict:
        slips = [r.stop_slippage_pct for r in subset]
        if not slips:
            return {"n": 0}
        return {
            "n": len(slips),
            "mean": _avg(slips),
            "median": round(statistics.median(slips), 3),
            "worst": round(min(slips), 3),
            "best": round(max(slips), 3),
        }

    by_direction = {d: _distribution([r for r in rows if r.direction == d]) for d in ("long", "short")}

    by_symbol = defaultdict(list)
    for r in rows:
        by_symbol[r.symbol].append(r)
    symbol_distribution = {
        symbol: _distribution(subset) for symbol, subset in by_symbol.items() if len(subset) >= 1
    }

    by_bucket = defaultdict(list)
    for r in rows:
        by_bucket[_volatility_bucket(r)].append(r)
    bucket_distribution = {bucket: _distribution(subset) for bucket, subset in by_bucket.items()}

    health = scanner_health(gap_threshold_minutes=outage_gap_threshold_minutes)
    outages = health.get("outages", [])

    def _in_outage(exit_time: int | None) -> bool:
        if exit_time is None:
            return False
        return any(o["start"] <= exit_time <= o["end"] for o in outages)

    during_outage = [r for r in rows if _in_outage(r.exit_time)]
    normal = [r for r in rows if not _in_outage(r.exit_time)]

    return {
        "overall": _distribution(rows),
        "no_slippage_data_available": {
            "n": len(no_data_rows),
            "note": "stop-hit trades that predate the V1.1 exit_price/stop_slippage_pct capture — honestly excluded above, not backfilled.",
            "symbols": sorted(set(r.symbol for r in no_data_rows)),
        },
        "by_direction": by_direction,
        "by_symbol": symbol_distribution,
        "by_volatility_bucket": bucket_distribution,
        "during_outage_vs_normal": {
            "during_outage": _distribution(during_outage),
            "normal_uptime": _distribution(normal),
            "note": f"'during_outage' uses the same >{outage_gap_threshold_minutes}min gap definition as scanner_health().",
        },
    }


# ---------------------------------------------------------------------------
# 3. TP Continuation Dashboard
# ---------------------------------------------------------------------------

def _post_tp1_path(row: TradeOutcome, snapshots: list[PredictionSnapshot]) -> dict | None:
    """Walks REAL price snapshots after tp1_hit_at — not final status alone.

    Two sign/field pitfalls found and avoided here (discovered building the
    read-only forensic report this is based on):
      - PredictionSnapshot.current_pnl_pct is hardcoded to 0.0 by
        record_snapshot() once status != "open" (i.e. the closing
        snapshot) — comparing it directly would read every trade's final
        row as "back at entry" regardless of real exit price. Compares
        current_price to row.entry directly instead, and only over
        snapshots still tagged status == "open".
      - distance_to_stop_pct = (stop_loss - price)/price*100*sign is
        NEGATIVE during healthy operation (opposite convention from the
        distance_to_tp*_pct fields) — compares current_price to
        row.stop_loss directly instead of trusting that field's sign.
    """
    if not row.tp1_hit_at:
        return None
    after = [s for s in snapshots if s.timestamp >= row.tp1_hit_at]
    if not after:
        return {"returned_to_entry": None, "returned_to_stop": None, "continuation_after_tp1": None, "pullback_after_tp1": None}

    is_long = row.direction == "long"
    sign = 1 if is_long else -1

    open_prices = [s.current_price for s in after if s.current_price is not None and s.status == "open"]
    if not open_prices:
        returned_to_entry = None
    elif is_long:
        returned_to_entry = any(p <= row.entry for p in open_prices)
    else:
        returned_to_entry = any(p >= row.entry for p in open_prices)

    all_prices = [s.current_price for s in after if s.current_price is not None]
    if is_long:
        returned_to_stop = any(p <= row.stop_loss for p in all_prices) if all_prices else None
    else:
        returned_to_stop = any(p >= row.stop_loss for p in all_prices) if all_prices else None

    excursions = [round((p - row.entry) / row.entry * 100 * sign, 3) for p in all_prices]
    continuation_after_tp1 = max(excursions) if excursions else None  # best case beyond entry, after TP1
    pullback_after_tp1 = min(excursions) if excursions else None  # worst case beyond entry, after TP1

    return {
        "returned_to_entry": returned_to_entry,
        "returned_to_stop": returned_to_stop,
        "continuation_after_tp1": continuation_after_tp1,
        "pullback_after_tp1": pullback_after_tp1,
    }


def tp_continuation_analytics() -> dict:
    """Per-trade continuation detail plus aggregate probabilities. See
    forensic_diagnostics.py:target_conditional_probabilities() for the
    aggregate P(TP2|TP1)/P(TP3|TP2) figures this deliberately does not
    duplicate — this function's unique value is the per-trade
    return-to-entry/return-to-stop/continuation/pullback path analysis."""
    rows = _traded_rows()
    tp1_rows = [r for r in rows if r.tp1_hit]

    per_trade = []
    entry_true = entry_determined = 0
    stop_true = stop_determined = 0
    continuations, pullbacks = [], []

    for r in tp1_rows:
        snaps = _snapshots_for(r.id)
        path = _post_tp1_path(r, snaps)
        if path is None:
            continue
        if path["returned_to_entry"] is not None:
            entry_determined += 1
            entry_true += int(path["returned_to_entry"])
        if path["returned_to_stop"] is not None:
            stop_determined += 1
            stop_true += int(path["returned_to_stop"])
        if path["continuation_after_tp1"] is not None:
            continuations.append(path["continuation_after_tp1"])
        if path["pullback_after_tp1"] is not None:
            pullbacks.append(path["pullback_after_tp1"])
        per_trade.append({
            "trade_outcome_id": r.id, "symbol": r.symbol, "status": r.status,
            "tp2_hit": r.tp2_hit, "tp3_hit": r.tp3_hit, **path,
        })

    tp1_and_tp2 = [r for r in tp1_rows if r.tp2_hit]
    tp2_rows = [r for r in rows if r.tp2_hit]
    tp2_and_tp3 = [r for r in tp2_rows if r.tp3_hit]

    return {
        "n_reached_tp1": len(tp1_rows),
        "tp2_probability_given_tp1": _pct(len(tp1_and_tp2), len(tp1_rows)),
        "tp3_probability_given_tp2": _pct(len(tp2_and_tp3), len(tp2_rows)),
        "return_to_entry_probability": {
            "pct": _pct(entry_true, entry_determined),
            "n_determinable": entry_determined,
            "n_undeterminable": len(tp1_rows) - entry_determined,
            "note": "Undeterminable trades only ever had a single (closing) snapshot after TP1 — no intermediate open-status price to check.",
        },
        "return_to_stop_probability": {"pct": _pct(stop_true, stop_determined), "n_determinable": stop_determined},
        "average_continuation_after_tp1_pct": _avg(continuations),
        "average_pullback_after_tp1_pct": _avg(pullbacks),
        "per_trade": per_trade,
    }


# ---------------------------------------------------------------------------
# 4. Confidence Lab
# ---------------------------------------------------------------------------

_CONFIDENCE_BUCKETS = [(50, 55), (55, 60), (60, 65), (65, 70), (70, 75), (75, 101)]
_CONFIDENCE_LABELS = ["50-54", "55-59", "60-64", "65-69", "70-74", "75+"]


def confidence_lab(min_bucket_n: int = 5) -> dict:
    """Brier score and Expected Calibration Error (ECE) on top of the
    existing confidence-bucket win rates (trade_reports.py:
    confidence_calibration() already reports win rate per bucket; this
    treats each trade's confidence/100 as its "predicted probability of
    winning" and scores that against the real win/loss outcome).

    ECE here is the standard bucketed definition: weighted average, across
    buckets, of |predicted_avg_confidence - actual_win_rate|, weighted by
    each bucket's share of trades. Buckets under min_bucket_n are excluded
    from the ECE weighting (too few trades for the bucket's own win rate to
    mean anything) but still reported with their raw counts."""
    rows = [r for r in _traded_rows() if r.confidence is not None]
    return _confidence_lab_from_rows(rows, min_bucket_n=min_bucket_n)


def _confidence_lab_from_rows(rows: list[TradeOutcome], min_bucket_n: int = 5) -> dict:
    """Pure computation, split out from confidence_lab() so it can be unit
    tested against a hand-built row list instead of whatever happens to be
    in the live DB at test time."""
    if not rows:
        return {"note": "No resolved trades with a stored confidence value yet."}

    probs = [r.confidence / 100 for r in rows]
    outcomes = [1 if r.status == "closed_win" else 0 for r in rows]
    brier = round(sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(rows), 4)

    buckets = []
    ece_numerator = 0.0
    ece_weight_total = 0
    for (lo, hi), label in zip(_CONFIDENCE_BUCKETS, _CONFIDENCE_LABELS):
        b = [r for r in rows if lo <= r.confidence < hi]
        n = len(b)
        if n == 0:
            buckets.append({"bucket": label, "n": 0})
            continue
        wins = sum(1 for r in b if r.status == "closed_win")
        actual_win_rate = wins / n * 100
        avg_predicted = sum(r.confidence for r in b) / n
        entry = {
            "bucket": label, "n": n, "avg_predicted_confidence": round(avg_predicted, 1),
            "actual_win_rate_pct": round(actual_win_rate, 1),
            "calibration_gap": round(avg_predicted - actual_win_rate, 1),
        }
        if n < min_bucket_n:
            entry["note"] = f"n < {min_bucket_n} — excluded from ECE weighting below."
        else:
            ece_numerator += abs(avg_predicted - actual_win_rate) * n
            ece_weight_total += n
        buckets.append(entry)

    ece = round(ece_numerator / ece_weight_total, 2) if ece_weight_total else None

    return {
        "n_trades": len(rows),
        "brier_score": brier,
        "expected_calibration_error": ece,
        "expected_calibration_error_note": (
            f"Computed only over buckets with n >= {min_bucket_n} ({ece_weight_total} of {len(rows)} trades); "
            "smaller buckets are reported but not weighted into this number."
        ),
        "buckets": buckets,
    }


# ---------------------------------------------------------------------------
# 5. Coin Intelligence
# ---------------------------------------------------------------------------

def coin_leaderboard(min_sample: int = 3) -> dict:
    rows = _traded_rows()
    by_symbol = defaultdict(list)
    for r in rows:
        by_symbol[r.symbol].append(r)

    leaderboard = []
    for symbol, symbol_rows in by_symbol.items():
        if len(symbol_rows) < min_sample:
            continue
        wins = [r for r in symbol_rows if r.status == "closed_win"]
        rets = [r.realized_return_pct for r in symbol_rows]
        leaderboard.append({
            "symbol": symbol,
            "n": len(symbol_rows),
            "profit_factor": _profit_factor(symbol_rows),
            "win_rate_pct": _pct(len(wins), len(symbol_rows)),
            "avg_return_pct": _avg(rets),
            "avg_confidence": _avg([r.confidence for r in symbol_rows]),
            "avg_mfe_pct": _avg([r.max_runup_pct for r in symbol_rows]),
            "avg_mae_pct": _avg([r.max_drawdown_pct for r in symbol_rows]),
        })

    leaderboard.sort(key=lambda c: c["profit_factor"] if c["profit_factor"] is not None else -1, reverse=True)
    excluded = len(by_symbol) - len(leaderboard)
    return {
        "min_sample": min_sample,
        "symbols_ranked": leaderboard,
        "symbols_excluded_below_min_sample": excluded,
    }


# ---------------------------------------------------------------------------
# 6. Trade Replay API
# ---------------------------------------------------------------------------

def _replay_pattern(row: TradeOutcome) -> dict:
    from app.analytics.failure_patterns import lifecycle_pattern, pattern_similarity, risk_tags

    ei = row.entry_indicators or {}
    similarity = pattern_similarity(ei, row.structure_score, row.historic_probability, row.direction)
    return {
        "lifecycle_pattern": lifecycle_pattern(row),
        "risk_tags": risk_tags(row),
        "similarity_to_shared_tags": similarity,
    }


def _replay_narrative(row: TradeOutcome) -> list[str]:
    """Plain-English bullets built from already-stored diagnostic_flags/
    entry_indicators — never a new judgment, just a readable restatement
    of facts this row already carries. Empty list (not fabricated text)
    when nothing notable is stored."""
    bullets = []
    ei = row.entry_indicators or {}
    flags = row.diagnostic_flags or []

    if row.structure_score is not None and row.structure_score >= 9:
        bullets.append("Structure confirmed (fresh trend break and/or fair value gap present at entry).")
    elif "HIGH_SCORE_WEAK_STRUCTURE" in flags or "HIGH_MOMENTUM_WEAK_STRUCTURE" in flags:
        bullets.append("Structure was weak relative to the rest of the setup.")

    cmf = ei.get("cmf")
    if cmf is not None:
        bullets.append(f"CMF was {'positive' if cmf > 0 else 'negative'} ({cmf}) at entry.")

    if "OVERBOUGHT" in flags:
        bullets.append("RSI/stochRSI flagged overbought or oversold at entry (see entry_quality reasons for direction).")

    if "NO_HISTORY" in flags:
        bullets.append("No stored historical analogue existed for this symbol at entry.")

    if row.level_reasoning:
        for key, label in (
            ("entry_reasoning", "Entry"), ("sl_reasoning", "Stop"),
            ("tp1_reasoning", "TP1"), ("tp2_reasoning", "TP2"), ("tp3_reasoning", "TP3"),
        ):
            text = row.level_reasoning.get(key)
            if text:
                bullets.append(f"{label} reasoning: {text}")

    return bullets


def trade_replay(trade_outcome_id: int) -> dict | None:
    session = SessionLocal()
    try:
        row = session.get(TradeOutcome, trade_outcome_id)
    finally:
        session.close()
    if row is None:
        return None

    snapshots = _snapshots_for(trade_outcome_id)

    if row.exit_time is None:
        exit_reason = None
    elif row.status == "closed_win":
        exit_reason = "target reached"
    elif row.status == "closed_loss":
        exit_reason = "stop hit" if row.stop_hit else "closed at a loss (max holding window)"
    elif row.status == "closed_stale":
        exit_reason = "never entered within the max holding window"
    elif row.status == "invalidated":
        exit_reason = "superseded by a new plan before resolving"
    else:
        exit_reason = row.status

    return {
        "trade_outcome_id": row.id,
        "symbol": row.symbol,
        "direction": row.direction,
        "status": row.status,
        "created_at": row.created_at,
        "entry_time": row.entry_time,
        "exit_time": row.exit_time,
        "plan": {
            "entry_low": row.entry_low, "entry_high": row.entry_high, "entry": row.entry,
            "stop_loss": row.stop_loss, "tp1": row.tp1, "tp2": row.tp2, "tp3": row.tp3,
            "confidence": row.confidence, "grade": row.grade, "entry_quality": row.entry_quality,
            "entry_quality_reasons": row.entry_quality_reasons,
        },
        "entry_indicators": row.entry_indicators,
        "level_reasoning": row.level_reasoning,
        "claude_reasoning": {
            "summary": row.reasoning,
            "reasons_for": row.reasons_for,
            "reasons_against": row.reasons_against,
        },
        "tp_sl_events": {
            "tp1_hit": row.tp1_hit, "tp1_hit_at": row.tp1_hit_at,
            "tp2_hit": row.tp2_hit, "tp2_hit_at": row.tp2_hit_at,
            "tp3_hit": row.tp3_hit, "tp3_hit_at": row.tp3_hit_at,
            "stop_hit": row.stop_hit, "stop_slippage_pct": row.stop_slippage_pct,
        },
        "exit_price": row.exit_price,
        "exit_reason": exit_reason,
        "realized_return_pct": row.realized_return_pct,
        "max_runup_pct": row.max_runup_pct,
        "max_drawdown_pct": row.max_drawdown_pct,
        # Karma V3.0 — reuses app/analytics/failure_patterns.py rather than
        # reimplementing classification here; lazy import avoids a
        # circular dependency (that module also reads scanner_health()
        # from this one). Only meaningful once the trade has resolved.
        "pattern": _replay_pattern(row) if row.status in ("closed_win", "closed_loss") else None,
        "narrative": _replay_narrative(row),
        "prediction_timeline": [
            {
                "timestamp": s.timestamp, "stage": s.stage, "current_price": s.current_price,
                "current_pnl_pct": s.current_pnl_pct, "distance_to_tp1_pct": s.distance_to_tp1_pct,
                "distance_to_tp2_pct": s.distance_to_tp2_pct, "distance_to_tp3_pct": s.distance_to_tp3_pct,
                "distance_to_stop_pct": s.distance_to_stop_pct, "mfe_pct": s.mfe_pct, "mae_pct": s.mae_pct,
                "management_decision": s.management_decision, "decision_reason": s.decision_reason,
                "reason": s.reason,
            }
            for s in snapshots
        ],
    }


# ---------------------------------------------------------------------------
# 7. Trade Manager Analytics (open trades only — ANALYTICS ONLY, never
#    executes anything; see management_decision's own Phase-1 "always
#    HOLD while open" contract in trade_outcomes.py, which this does not
#    override or bypass)
# ---------------------------------------------------------------------------

def _distance_pct(level: float | None, price: float, sign: int) -> float | None:
    if level is None:
        return None
    return round((level - price) / price * 100 * sign, 3)


def _recommend(row: TradeOutcome, latest: PredictionSnapshot | None) -> tuple[str, str]:
    """Deterministic, template-built heuristic over already-computed
    fields — same "never fabricated, never Claude, never fed back into
    execution" contract as _rejection_reason() in background_scanner.py
    and management_decision in trade_outcomes.py. This is a SEPARATE,
    analytics-only suggestion surfaced for a human to read; it does not
    write to TradeOutcome, does not change lifecycle_status, and nothing
    in the scanner consumes it."""
    if latest is None:
        return "Hold", "No snapshot data yet to base a recommendation on."
    if row.tp2_hit:
        return "Hold for TP3" if row.tp3 is not None else "Exit Full", (
            "TP2 already reached; TP3 is defined as a further target." if row.tp3 is not None
            else "TP2 already reached and no TP3 is defined for this plan."
        )
    if row.tp1_hit:
        return "Move Stop to Breakeven", "TP1 reached — locking in the entry price as the new floor is a common risk-reduction step (suggestion only, not applied)."
    mae = latest.mae_pct
    if mae is not None and mae < -3.0:
        return "Hold", f"Open and adverse (MAE {mae}%), but stop not yet hit — no target reached to justify tightening or exiting early."
    return "Hold", "Open, no target reached yet, no adverse-excursion concern flagged."


# ---------------------------------------------------------------------------
# Karma V2.1 Phase 7 additions — reuses V2.1-A's expected_value.py and
# V2.1-C's red_flags.py rather than recomputing anything; these two are
# genuinely new leaderboards, not duplicates of anything already in
# trade_reports.py/forensic_diagnostics.py (which already cover feature
# importance, entry-quality performance, and confidence calibration — see
# app/routes/performance.py for how those get reused via routes instead of
# being reimplemented here).
# ---------------------------------------------------------------------------

def ev_leaderboard(min_sample: int = 1) -> dict:
    """Ranks resolved trades by their stored expected_value.expected_r
    (V2.1-A, computed once at issuance) against what actually happened —
    the same "does score agree with EV" question Section 4 of the V2.1
    forensic report answered by hand, kept live here as new trades
    resolve. Only trades issued after V2.1-A shipped have this field."""
    rows = [r for r in _traded_rows() if r.expected_value and r.expected_value.get("expected_r") is not None]
    if len(rows) < min_sample:
        return {"n": len(rows), "note": f"Fewer than {min_sample} trades have a stored expected_value yet.", "trades": []}

    def _realized_r(r: TradeOutcome) -> float | None:
        rr = (r.entry_indicators or {}).get("risk_reward") or {}
        risk_pct = rr.get("risk_to_sl_pct")
        if not risk_pct or r.realized_return_pct is None:
            return None
        return round(r.realized_return_pct / risk_pct, 3)

    entries = []
    for r in rows:
        entries.append({
            "symbol": r.symbol, "score": r.score, "expected_r": r.expected_value["expected_r"],
            "realized_r": _realized_r(r), "status": r.status,
            "conditioning_used": r.expected_value.get("conditioning_used"),
            "sample_size": r.expected_value.get("sample_size"),
        })
    entries.sort(key=lambda e: -e["expected_r"])

    scores = [e["score"] for e in entries]
    evs = [e["expected_r"] for e in entries]
    corr = None
    if len(entries) >= 3:
        try:
            import statistics
            corr = round(statistics.correlation(scores, evs), 3)
        except Exception:
            corr = None

    return {
        "n": len(entries), "corr_score_vs_expected_r": corr,
        "avg_expected_r": _avg(evs), "avg_realized_r": _avg([e["realized_r"] for e in entries]),
        "ranked_by_expected_r": entries,
    }


def red_flag_leaderboard() -> dict:
    """Win rate and avg return by red_flag_score (V2.1-C, 0-3 flags
    triggered at issuance) — only trades issued after V2.1-C shipped have
    this field. Purely observational, same as red_flags.py itself."""
    rows = [r for r in _traded_rows() if r.red_flags is not None]
    if not rows:
        return {"n": 0, "note": "No trades have a stored red_flags value yet."}

    buckets = {}
    for score in range(0, 4):
        sub = [r for r in rows if r.red_flags.get("red_flag_score") == score]
        if not sub:
            continue
        w = [r for r in sub if r.status == "closed_win"]
        buckets[score] = {
            "n": len(sub), "win_rate_pct": _pct(len(w), len(sub)),
            "avg_return_pct": _avg([r.realized_return_pct for r in sub]),
        }
    return {"n": len(rows), "by_red_flag_score": buckets}


def failure_pattern_leaderboard(min_sample: int = 3) -> dict:
    """Thin pass-through to app/analytics/failure_patterns.py — kept here
    too (not just as a standalone module) so the Performance Center
    dashboard has one place listing every leaderboard it exposes."""
    from app.analytics.failure_patterns import failure_pattern_leaderboard as _impl

    return _impl(min_sample=min_sample)


def coin_reliability_leaderboard(prior_strength: int | None = None) -> dict:
    """Thin pass-through to app/analytics/reliability.py — Bayesian-
    shrunk win rate per symbol, distinct from coin_leaderboard() above
    (which reports raw, unshrunk stats and requires min_sample to even
    appear; this instead reports EVERY symbol, shrinking thin samples
    toward the pooled rate rather than hiding them)."""
    from app.analytics.reliability import PRIOR_STRENGTH, symbol_reliability

    return symbol_reliability(prior_strength=prior_strength if prior_strength is not None else PRIOR_STRENGTH)


def open_trade_management_analytics() -> dict:
    session = SessionLocal()
    try:
        open_rows = session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(_OPEN_STATUSES))).scalars().all()
    finally:
        session.close()

    current_regime = load_current_regime()
    current_regime_label = (current_regime or {}).get("label")

    trades = []
    for row in open_rows:
        snaps = _snapshots_for(row.id)
        latest = snaps[-1] if snaps else None
        first = snaps[0] if snaps else None
        is_long = row.direction == "long"
        sign = 1 if is_long else -1
        price = latest.current_price if latest else None

        distances = None
        if price is not None:
            distances = {
                "to_tp1_pct": _distance_pct(row.tp1, price, sign),
                "to_tp2_pct": _distance_pct(row.tp2, price, sign),
                "to_tp3_pct": _distance_pct(row.tp3, price, sign),
                "to_stop_pct": _distance_pct(row.stop_loss, price, sign),
            }

        # Confidence itself does not change after issuance in this app
        # (no re-explanation of open trades exists yet — see
        # PredictionSnapshot.confidence's own docstring: "carried over ...
        # confidence/grade don't change after a plan is issued"). Reported
        # honestly as flat rather than inventing a "trend" from a constant.
        confidence_trend = {
            "at_entry": row.confidence, "latest_snapshot": latest.confidence if latest else None,
            "note": "Confidence is fixed at issuance and carried forward unchanged in every snapshot (no re-explanation of open trades exists yet) — this is not expected to differ.",
        }

        structure_change = None
        if first and latest and first.structure_score is not None and latest.structure_score is not None:
            structure_change = round(latest.structure_score - first.structure_score, 2)
        momentum_change = None
        if first and latest and first.momentum_score is not None and latest.momentum_score is not None:
            momentum_change = round(latest.momentum_score - first.momentum_score, 2)

        regime_at_entry = row.market_regime
        regime_change = (
            None if regime_at_entry is None or current_regime_label is None
            else (regime_at_entry != current_regime_label)
        )

        recommendation, reason = _recommend(row, latest)
        # V3.1 — reuses trade_manager.py's conditional_triggers() rather
        # than duplicating "if price reaches level X" logic here.
        from app.engine.trade_manager import conditional_triggers
        from app.engine.trade_outcomes import _compute_stage

        triggers = conditional_triggers(row, _compute_stage(row))

        trades.append({
            "trade_outcome_id": row.id, "symbol": row.symbol, "direction": row.direction, "status": row.status,
            "current_price": price,
            "distances": distances,
            "confidence_trend": confidence_trend,
            # "trend change" per the spec — momentum_score is this app's
            # existing per-snapshot trend/momentum proxy (structure_score
            # covers structure separately); there is no separate raw
            # "trend score" carried on PredictionSnapshot to diff against.
            "trend_change_momentum_score_delta": momentum_change,
            "structure_change_score_delta": structure_change,
            "regime_at_entry": regime_at_entry,
            "current_regime": current_regime_label,
            "regime_changed": regime_change,
            "mfe_pct": latest.mfe_pct if latest else None,
            "mae_pct": latest.mae_pct if latest else None,
            "recommendation": recommendation,
            "recommendation_reason": reason,
            "conditional_triggers": triggers,
        })

    return {"n_open_trades": len(trades), "trades": trades, "note": "Analytics only — nothing here executes, modifies, or closes any trade."}
