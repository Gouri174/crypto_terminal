"""Aggregate reports built on top of app/models/db_models.py:TradeOutcome.

Everything here reads resolved rows (status starting "closed_") within a
time window and computes plain statistics — no LLM involved, nothing
inferred. This is the "was the AI actually profitable" answer the rest of
the system couldn't give before TradeOutcome existed.

All reports score performance by trades that RESOLVED within the window
(exit_time), not trades opened within it — a trade opened yesterday but
still running isn't a result yet.
"""

import statistics
from collections import defaultdict

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

_RESOLVED_STATUSES = ("closed_win", "closed_loss", "closed_stale")
_MIN_GROUP_SAMPLE = 3


def _resolved_in_window(start_ms: int, end_ms: int) -> list[TradeOutcome]:
    session = SessionLocal()
    try:
        return (
            session.execute(
                select(TradeOutcome).where(
                    TradeOutcome.status.in_(_RESOLVED_STATUSES),
                    TradeOutcome.exit_time >= start_ms,
                    TradeOutcome.exit_time < end_ms,
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()


def _predicted_probability(row: TradeOutcome) -> float:
    """Best available probability estimate at the time the trade was
    issued, used only to measure surprise after the fact — never fed back
    into scoring."""
    if row.ml_probability is not None:
        return row.ml_probability
    if row.historic_probability is not None:
        return row.historic_probability
    return row.score / 100


def performance_digest(start_ms: int, end_ms: int, label: str) -> dict:
    """Shared by daily/weekly/monthly — the window size is the only
    difference. Wins/losses exclude closed_stale (never entered — not a
    trading result, just an expired signal)."""
    rows = _resolved_in_window(start_ms, end_ms)
    traded = [r for r in rows if r.status in ("closed_win", "closed_loss")]
    stale = len(rows) - len(traded)

    if not traded:
        return {
            "label": label,
            "signals_resolved": len(rows),
            "never_entered": stale,
            "wins": 0,
            "losses": 0,
            "note": "No resolved trades in this window yet.",
        }

    returns = [r.realized_return_pct for r in traded]
    wins = [r for r in traded if r.status == "closed_win"]
    losses = [r for r in traded if r.status == "closed_loss"]
    gains = [r.realized_return_pct for r in wins]
    loss_amounts = [abs(r.realized_return_pct) for r in losses]

    profit_factor = (sum(gains) / sum(loss_amounts)) if loss_amounts else None
    sharpe = (
        statistics.mean(returns) / statistics.pstdev(returns)
        if len(returns) > 1 and statistics.pstdev(returns) > 0
        else None
    )
    max_drawdown = _equity_curve_max_drawdown(traded)

    best = max(traded, key=lambda r: r.realized_return_pct)
    worst = min(traded, key=lambda r: r.realized_return_pct)
    highest_confidence = max(traded, key=lambda r: r.score)
    biggest_surprise = max(
        traded,
        key=lambda r: abs((1.0 if r.status == "closed_win" else 0.0) - _predicted_probability(r)),
    )

    return {
        "label": label,
        "signals_resolved": len(traded),
        "never_entered": stale,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(traded) * 100, 1),
        "tp1_hit": sum(1 for r in traded if r.tp1_hit),
        "tp2_hit": sum(1 for r in traded if r.tp2_hit),
        "tp3_hit": sum(1 for r in traded if r.tp3_hit),
        "average_return_pct": round(statistics.mean(returns), 2),
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        # Simplified: an equal-weighted series of per-trade % returns, not a
        # sized/compounded equity curve, and not annualized — a real
        # position-sizing model would change this materially.
        "sharpe_simplified": round(sharpe, 2) if sharpe is not None else None,
        "max_drawdown_pct": round(max_drawdown, 2) if max_drawdown is not None else None,
        "best_trade": {"symbol": best.symbol, "return_pct": best.realized_return_pct},
        "worst_trade": {"symbol": worst.symbol, "return_pct": worst.realized_return_pct},
        "highest_confidence": {"symbol": highest_confidence.symbol, "score": highest_confidence.score},
        "biggest_surprise": {
            "symbol": biggest_surprise.symbol,
            "predicted_probability": round(_predicted_probability(biggest_surprise), 2),
            "outcome": biggest_surprise.status,
        },
    }


def _equity_curve_max_drawdown(traded: list[TradeOutcome]) -> float | None:
    ordered = sorted((r for r in traded if r.exit_time), key=lambda r: r.exit_time)
    if not ordered:
        return None
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in ordered:
        cumulative += r.realized_return_pct
        peak = max(peak, cumulative)
        max_dd = min(max_dd, cumulative - peak)
    return max_dd


def monthly_breakdown(start_ms: int, end_ms: int) -> dict:
    """Best/worst coin and strategy, and which timeframe/regime the system
    has actually been most accurate in — only meaningful once enough
    resolved trades exist per group (_MIN_GROUP_SAMPLE), otherwise a single
    lucky/unlucky trade would dominate the label."""
    rows = [r for r in _resolved_in_window(start_ms, end_ms) if r.status in ("closed_win", "closed_loss")]
    if not rows:
        return {"note": "No resolved trades in this window yet."}

    by_symbol = _group_avg_return(rows, lambda r: r.symbol)
    by_strategy = _group_avg_return(rows, lambda r: f"{r.timeframe} {r.direction}")
    by_timeframe_winrate = _group_win_rate(rows, lambda r: r.timeframe)
    by_regime_winrate = _group_win_rate(rows, lambda r: r.market_regime or "unknown")

    return {
        "best_coin": _best(by_symbol),
        "worst_coin": _worst(by_symbol),
        "best_strategy": _best(by_strategy),
        "worst_strategy": _worst(by_strategy),
        "highest_accuracy_timeframe": _best(by_timeframe_winrate),
        "best_market_regime": _best(by_regime_winrate),
        "by_direction": direction_breakdown(start_ms, end_ms),
    }


def direction_breakdown(start_ms: int, end_ms: int) -> dict:
    """"Are shorts performing better than longs?" — monthly_breakdown groups
    by timeframe+direction combined (e.g. "swing long"); this groups by
    direction ALONE, which is the more direct question. Gated behind
    _MIN_GROUP_SAMPLE per side."""
    rows = [r for r in _resolved_in_window(start_ms, end_ms) if r.status in ("closed_win", "closed_loss")]
    by_direction = _group_win_rate(rows, lambda r: r.direction)
    returns_by_direction = _group_avg_return(rows, lambda r: r.direction)
    result = {}
    for direction in ("long", "short"):
        win = by_direction.get(direction)
        ret = returns_by_direction.get(direction)
        if win is None or ret is None:
            result[direction] = {"note": f"Need >= {_MIN_GROUP_SAMPLE} resolved {direction} trades."}
        else:
            result[direction] = {
                "sample_size": win["sample_size"],
                "win_rate_pct": win["win_rate_pct"],
                "avg_return_pct": ret["avg_return_pct"],
            }
    return result


def _group_avg_return(rows: list[TradeOutcome], key_fn) -> dict[str, dict]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        buckets[key_fn(r)].append(r.realized_return_pct)
    return {
        k: {"avg_return_pct": round(statistics.mean(v), 2), "sample_size": len(v)}
        for k, v in buckets.items()
        if len(v) >= _MIN_GROUP_SAMPLE
    }


def _group_win_rate(rows: list[TradeOutcome], key_fn) -> dict[str, dict]:
    buckets: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        buckets[key_fn(r)].append(r.status == "closed_win")
    return {
        k: {"win_rate_pct": round(sum(v) / len(v) * 100, 1), "sample_size": len(v)}
        for k, v in buckets.items()
        if len(v) >= _MIN_GROUP_SAMPLE
    }


def _best(groups: dict[str, dict]) -> dict | None:
    if not groups:
        return None
    metric = "avg_return_pct" if "avg_return_pct" in next(iter(groups.values())) else "win_rate_pct"
    name = max(groups, key=lambda k: groups[k][metric])
    return {"name": name, **groups[name]}


def _worst(groups: dict[str, dict]) -> dict | None:
    if not groups:
        return None
    metric = "avg_return_pct" if "avg_return_pct" in next(iter(groups.values())) else "win_rate_pct"
    name = min(groups, key=lambda k: groups[k][metric])
    return {"name": name, **groups[name]}


_COMPONENT_LABELS = {
    "trend_score": "Trend", "momentum_score": "Momentum", "volume_score": "Volume",
    "funding_score": "Funding", "structure_score": "Structure", "history_score": "Historical Similarity",
    "regime_score": "Market Regime", "ml_score": "ML Model", "sentiment_score": "Sentiment (Fear/Greed)",
    "liquidity_score": "Cross-Exchange Liquidity", "risk_score": "Risk Penalty",
}


def feature_importance(min_sample: int = 20, limit: int | None = None) -> dict:
    """Which score components actually differed between winning and losing
    trades — mean value among wins minus mean value among losses, sorted by
    absolute impact. A large positive gap means that component's high
    values tend to precede wins; a large negative gap means the opposite of
    what the scoring formula assumes (worth investigating, not just
    reporting). This is NOT a statistical significance test — with few
    resolved trades it's noise, which is why it refuses to run below
    min_sample.

    limit: if given, only the most recently CREATED `limit` resolved trades
    are used — lets "what's mattered lately" be asked as data accumulates,
    instead of always averaging over the entire history including whatever
    scoring-formula version was active long ago (see score_formula_version
    on each row for the exact version, if a future version-aware split is
    worth building). None (default) uses every resolved trade."""
    session = SessionLocal()
    try:
        stmt = (
            select(TradeOutcome)
            .where(TradeOutcome.status.in_(["closed_win", "closed_loss"]))
            .order_by(TradeOutcome.created_at.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        rows = session.execute(stmt).scalars().all()
    finally:
        session.close()

    if len(rows) < min_sample:
        return {
            "sample_size": len(rows),
            "note": f"Need at least {min_sample} resolved trades for this to mean anything; have {len(rows)}.",
        }

    wins = [r for r in rows if r.status == "closed_win"]
    losses = [r for r in rows if r.status == "closed_loss"]

    components = []
    win_minus_loss_mean = {}
    for field, label in _COMPONENT_LABELS.items():
        win_mean = statistics.mean(getattr(r, field) for r in wins) if wins else 0.0
        loss_mean = statistics.mean(getattr(r, field) for r in losses) if losses else 0.0
        diff = round(win_mean - loss_mean, 2)
        win_minus_loss_mean[field] = diff
        components.append({"component": field, "label": label, "win_minus_loss_mean": diff})

    components.sort(key=lambda c: abs(c["win_minus_loss_mean"]), reverse=True)

    return {
        "sample_size": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "components": components,
        "win_minus_loss_mean": win_minus_loss_mean,  # kept for backward compatibility
    }


# Previous name — kept as an alias so nothing that already imports
# score_correlations breaks.
score_correlations = feature_importance


_CONFIDENCE_BUCKETS = [(90, 101), (80, 90), (70, 80), (60, 70), (50, 60), (0, 50)]
_GRADE_ORDER = ["A+", "A", "B+", "B", "C", "Avoid"]


def confidence_calibration(min_sample: int = 5) -> dict:
    """Buckets resolved trades by the confidence stored AT ISSUE TIME and
    compares against actual win rate — "if 90-confidence trades only won
    60% of the time, the confidence scale needs recalibration," not a
    number to trust just because it looks precise. Only trades with a
    stored confidence are included — TradeOutcome rows created before this
    field existed are honestly excluded, not backfilled with a guess.
    Per-bucket sample-size gate for the same reason as feature_importance:
    a single lucky/unlucky trade shouldn't produce a misleading 100%/0%
    bucket."""
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(TradeOutcome).where(
                    TradeOutcome.status.in_(["closed_win", "closed_loss"]),
                    TradeOutcome.confidence.is_not(None),
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    buckets = []
    for lo, hi in _CONFIDENCE_BUCKETS:
        in_bucket = [r for r in rows if lo <= r.confidence < hi]
        entry = {"range": f"{lo}-{min(hi, 100)}", "sample_size": len(in_bucket)}
        if len(in_bucket) < min_sample:
            entry["note"] = f"Need >= {min_sample} resolved trades in this range; have {len(in_bucket)}."
        else:
            wins = sum(1 for r in in_bucket if r.status == "closed_win")
            entry["actual_win_rate_pct"] = round(wins / len(in_bucket) * 100, 1)
        buckets.append(entry)

    return {"total_eligible": len(rows), "buckets": buckets}


def grade_calibration(min_sample: int = 5) -> dict:
    """Same idea as confidence_calibration, bucketed by letter grade
    instead — "does A+ actually outperform B?" Only trades with a stored
    grade are included."""
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(TradeOutcome).where(
                    TradeOutcome.status.in_(["closed_win", "closed_loss"]),
                    TradeOutcome.grade.is_not(None),
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    by_grade: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by_grade[r.grade].append(r.status == "closed_win")

    grades = []
    for grade in _GRADE_ORDER:
        vals = by_grade.get(grade, [])
        entry = {"grade": grade, "sample_size": len(vals)}
        if len(vals) < min_sample:
            entry["note"] = f"Need >= {min_sample} resolved trades; have {len(vals)}."
        else:
            entry["actual_win_rate_pct"] = round(sum(vals) / len(vals) * 100, 1)
        grades.append(entry)

    return {"total_eligible": len(rows), "grades": grades}


def signals_issued_summary(start_ms: int, end_ms: int, label: str) -> dict:
    """Different slice from performance_digest: scores signals by when they
    were ISSUED (created_at), not when they resolved — answers "how are
    today's picks doing so far," including ones still open, rather than
    "what resolved today regardless of when it was picked." This is the
    shape of a daily/weekly "prediction report": signals, completed, still
    open, TP/stop counts, and — only once enough of THIS batch has actually
    resolved — return/win-rate/profit-factor and notable trades."""
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(TradeOutcome).where(
                    TradeOutcome.created_at >= start_ms,
                    TradeOutcome.created_at < end_ms,
                    TradeOutcome.direction.in_(["long", "short"]),
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    still_open = [r for r in rows if r.status in ("pending", "open")]
    traded_completed = [r for r in rows if r.status in ("closed_win", "closed_loss")]

    result = {
        "label": label,
        "signals": len(rows),
        "completed": len(rows) - len(still_open),
        "still_open": len(still_open),
        "tp1_hit": sum(1 for r in rows if r.tp1_hit),
        "tp2_hit": sum(1 for r in rows if r.tp2_hit),
        "tp3_hit": sum(1 for r in rows if r.tp3_hit),
        "stopped": sum(1 for r in rows if r.status == "closed_loss"),
    }

    if not traded_completed:
        result["note"] = "None of this window's signals have resolved to a win/loss yet."
        return result

    returns = [r.realized_return_pct for r in traded_completed]
    wins = [r for r in traded_completed if r.status == "closed_win"]
    gains = [r.realized_return_pct for r in wins]
    loss_amounts = [abs(r.realized_return_pct) for r in traded_completed if r.status == "closed_loss"]
    with_confidence = [r for r in rows if r.confidence is not None]
    worst = min(traded_completed, key=lambda r: r.realized_return_pct)
    biggest_surprise = max(
        traded_completed,
        key=lambda r: abs((1.0 if r.status == "closed_win" else 0.0) - _predicted_probability(r)),
    )

    result["average_return_pct"] = round(statistics.mean(returns), 2)
    result["win_rate_pct"] = round(len(wins) / len(traded_completed) * 100, 1)
    result["profit_factor"] = round(sum(gains) / sum(loss_amounts), 2) if loss_amounts else None
    result["worst_trade"] = {"symbol": worst.symbol, "return_pct": worst.realized_return_pct}
    result["biggest_surprise"] = {"symbol": biggest_surprise.symbol, "outcome": biggest_surprise.status}
    if with_confidence:
        highest = max(with_confidence, key=lambda r: r.confidence)
        result["highest_confidence_trade"] = {"symbol": highest.symbol, "confidence": highest.confidence}

    return result


_MOMENTUM_BUCKETS = [(0, 3), (3, 6), (6, 9), (9, 12), (12, 16)]


def momentum_vs_runup(min_sample: int = 5) -> dict:
    """Tests a specific hypothesis, not a general diagnostic: does a maxed-
    out momentum_score at entry correlate with LESS favorable movement
    before exit (late/exhausted entries), or more (clean confirmation)?
    Pure analysis over columns TradeOutcome already stores (momentum_score,
    max_runup_pct) — no new capture, no schema change. Gated per-bucket
    behind min_sample; with few resolved trades this is noise, not a
    finding, which is why it says so rather than drawing a curve from 3
    points."""
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(TradeOutcome).where(
                    TradeOutcome.status.in_(["closed_win", "closed_loss"]),
                    TradeOutcome.max_runup_pct.is_not(None),
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    buckets = []
    for lo, hi in _MOMENTUM_BUCKETS:
        in_bucket = [r for r in rows if lo <= r.momentum_score < hi]
        entry = {"momentum_range": f"{lo}-{hi}", "sample_size": len(in_bucket)}
        if len(in_bucket) < min_sample:
            entry["note"] = f"Need >= {min_sample} resolved trades; have {len(in_bucket)}."
        else:
            entry["avg_max_runup_pct"] = round(statistics.mean(r.max_runup_pct for r in in_bucket), 3)
            entry["avg_max_drawdown_pct"] = round(
                statistics.mean(r.max_drawdown_pct for r in in_bucket if r.max_drawdown_pct is not None), 3
            )
            entry["win_rate_pct"] = round(
                sum(1 for r in in_bucket if r.status == "closed_win") / len(in_bucket) * 100, 1
            )
        buckets.append(entry)

    return {
        "total_eligible": len(rows),
        "buckets": buckets,
        "note": (
            "Tests whether maxed momentum at entry predicts WORSE forward "
            "movement (late/exhausted entries) or better (clean "
            "confirmation). Not a conclusion until each bucket clears "
            "min_sample — see the per-bucket 'note' field."
        ),
    }


def evidence_coverage(min_sample: int = 5) -> dict:
    """Of the evidence sources that can genuinely be unavailable for a
    given symbol (ML prediction needs a trained model + enough of that
    symbol's own history to standardize against; historical similarity
    needs >= 20 stored analogues; sentiment needs a live Fear & Greed
    fetch), how often did each actually participate, and does coverage
    correlate with outcome? Trend/momentum/volume/structure/funding/regime
    are NOT included here — they're always computed once features are
    fetched, so "available" isn't a meaningful distinction for them the
    way it is for ML/history/sentiment."""
    session = SessionLocal()
    try:
        rows = (
            session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(["closed_win", "closed_loss"])))
            .scalars()
            .all()
        )
    finally:
        session.close()

    if len(rows) < min_sample:
        return {
            "sample_size": len(rows),
            "note": f"Need >= {min_sample} resolved trades for this to mean anything; have {len(rows)}.",
        }

    def coverage(r: TradeOutcome) -> int:
        return sum([r.ml_probability is not None, r.historic_probability is not None, r.fear_greed is not None])

    by_coverage: dict[int, list[bool]] = defaultdict(list)
    for r in rows:
        by_coverage[coverage(r)].append(r.status == "closed_win")

    levels = []
    for n in range(4):  # 0, 1, 2, or all 3 of ML/history/sentiment available
        vals = by_coverage.get(n, [])
        entry = {"sources_available": n, "of_possible": 3, "sample_size": len(vals)}
        if len(vals) < min_sample:
            entry["note"] = f"Need >= {min_sample}; have {len(vals)}."
        else:
            entry["win_rate_pct"] = round(sum(vals) / len(vals) * 100, 1)
        levels.append(entry)

    ml_available = sum(1 for r in rows if r.ml_probability is not None)
    history_available = sum(1 for r in rows if r.historic_probability is not None)
    sentiment_available = sum(1 for r in rows if r.fear_greed is not None)

    return {
        "sample_size": len(rows),
        "source_availability_pct": {
            "ml": round(ml_available / len(rows) * 100, 1),
            "history": round(history_available / len(rows) * 100, 1),
            "sentiment": round(sentiment_available / len(rows) * 100, 1),
        },
        "win_rate_by_coverage_level": levels,
    }


def momentum_vs_time_to_tp1(min_sample: int = 5) -> dict:
    """Distinct question from momentum_vs_runup: does a maxed momentum
    score actually LOSE more, or does it just reach TP1 FASTER — closing
    out before this existed, tp1_hit alone couldn't tell those apart.
    Only includes trades where tp1_hit_at and entry_time are both known
    (i.e. TP1 was actually reached, and the field existed to record when)
    — trades from before this column existed are honestly excluded."""
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(TradeOutcome).where(
                    TradeOutcome.tp1_hit_at.is_not(None),
                    TradeOutcome.entry_time.is_not(None),
                )
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    buckets = []
    for lo, hi in _MOMENTUM_BUCKETS:
        in_bucket = [r for r in rows if lo <= r.momentum_score < hi]
        entry = {"momentum_range": f"{lo}-{hi}", "sample_size": len(in_bucket)}
        if len(in_bucket) < min_sample:
            entry["note"] = f"Need >= {min_sample} trades that reached TP1; have {len(in_bucket)}."
        else:
            minutes = [(r.tp1_hit_at - r.entry_time) / 60_000 for r in in_bucket]
            entry["avg_minutes_to_tp1"] = round(statistics.mean(minutes), 1)
        buckets.append(entry)

    return {
        "total_eligible": len(rows),
        "buckets": buckets,
        "note": (
            "Distinct from momentum_vs_runup: tests whether maxed momentum "
            "reaches TP1 faster, not whether it wins more. A component "
            "can be 'good' on one axis and neutral on the other — this is "
            "why they're separate reports, not combined into one number."
        ),
    }


def open_trade_count() -> dict:
    """Live count for the performance dashboard's "Open Trades" tile —
    reads current TradeOutcome status, not a windowed query."""
    session = SessionLocal()
    try:
        statuses = (
            session.execute(select(TradeOutcome.status).where(TradeOutcome.status.in_(["pending", "open"])))
            .scalars()
            .all()
        )
    finally:
        session.close()
    return {
        "pending": statuses.count("pending"),
        "open": statuses.count("open"),
        "total_open": len(statuses),
    }
