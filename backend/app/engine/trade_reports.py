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
    }


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
