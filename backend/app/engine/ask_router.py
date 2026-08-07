"""Deterministic question router for the AI research assistant (/api/ask).

The old /api/ask just regex-extracted a symbol, dumped that symbol's raw
indicator features into a prompt, and asked Claude to answer freely — it
never touched TradeOutcome, PredictionSnapshot, or any of the calibration/
diagnostic reports this app already computes. That meant Claude was
guessing from the same live features a trade card already shows, not
reasoning over the system's actual track record.

This module fixes that ordering: classify the question by keyword match
(no NLU/ML — deterministic, inspectable, no extra API cost) into one of a
fixed set of categories, then pull REAL numbers from the existing report
functions (trade_reports.py, ml_retrain.py, background_scanner.py,
trade_outcomes.py) for that category BEFORE any Claude call happens.
Claude's only job (in routes/ask.py) is to explain/summarize this already-
computed data — never to invent a number that isn't in it.

Multiple categories can match one question (e.g. "why did SUIUSDT lose and
how's my system doing overall" is both coin-specific and system-accuracy);
gather_context() collects every matching category's data rather than
forcing a single guess.
"""

import re
import time
from dataclasses import dataclass, field

from sqlalchemy import select

from app.db import SessionLocal
from app.engine import trade_reports
from app.engine.background_scanner import load_current_regime
from app.engine.ml_retrain import retrain_recommendation
from app.models.db_models import LiveOpportunity, PredictionSnapshot, TradeOutcome

_DAY_MS = 86_400_000
_KNOWN_QUOTE = "USDT"
_SYMBOL_RE = re.compile(r"\b([A-Z]{2,15})\b")
_SYMBOL_CACHE_TTL_S = 300

_CATEGORY_KEYWORDS = {
    "best_trades_today": ["best trade", "top trade", "best signal", "best pick", "what's good", "opportunities"],
    "current_trades": ["current trade", "open trade", "open position", "live trade", "what's open", "how many open"],
    "system_accuracy": ["win rate", "how accurate", "how is the system", "profitable", "profit factor", "performing", "performance", "track record", "how good"],
    "calibration": ["calibrat", "confidence actually", "does confidence", "grade actually", "trust the grade", "trust the confidence"],
    "feature_importance": ["feature importance", "which factor", "what matters", "what predicts", "correlat", "most important"],
    "momentum_patterns": ["momentum", "run-up", "runup", "time to tp", "reach tp", "false breakout", "entry timing", "evidence coverage"],
    "long_vs_short": ["long vs short", "longs vs shorts", "long or short", "shorts perform", "longs perform", "direction"],
    "regime_performance": ["market regime", "which regime", "bull market", "bear market", "regime performance"],
    "retrain": ["retrain", "retraining", "should i train", "model version", "new model"],
}

# "today"/"week"/"month"/"90 day" phrasing controls report window size —
# defaults to 30 days if the question doesn't say.
_WINDOW_KEYWORDS = [
    ("today", 1), ("yesterday", 1), ("this week", 7), ("past week", 7),
    ("this month", 30), ("past month", 30), ("90 day", 90), ("90-day", 90),
    ("quarter", 90),
]


@dataclass
class RouterResult:
    categories: list[str]
    symbols: list[str]
    window_days: int
    data: dict = field(default_factory=dict)


_known_symbols_cache: tuple[float, set[str]] = (0.0, set())


def _known_symbols() -> set[str]:
    """Whitelist of symbols this system actually has data for, from
    TradeOutcome + LiveOpportunity. A blocklist of "not a ticker" English
    words doesn't scale (PERFORMING, SYSTEM, TODAY all look like valid
    2-15 char uppercase tokens) — matching against symbols we've genuinely
    seen is the only way to avoid false positives without hand-maintaining
    an ever-growing stopword list. Cached briefly since this is called on
    every question and the symbol universe changes at most once per scan
    cycle."""
    global _known_symbols_cache
    cached_at, cached = _known_symbols_cache
    if time.time() - cached_at < _SYMBOL_CACHE_TTL_S:
        return cached

    session = SessionLocal()
    try:
        outcome_symbols = session.execute(select(TradeOutcome.symbol).distinct()).scalars().all()
        live_symbols = session.execute(select(LiveOpportunity.symbol).distinct()).scalars().all()
    finally:
        session.close()

    symbols = {s.upper() for s in outcome_symbols} | {s.upper() for s in live_symbols}
    _known_symbols_cache = (time.time(), symbols)
    return symbols


def _extract_symbols(question: str) -> list[str]:
    upper = question.upper()
    known = _known_symbols()
    candidates = {m.group(1) for m in _SYMBOL_RE.finditer(upper)}

    matched = set()
    for c in candidates:
        if c in known:
            matched.add(c)
        elif f"{c}{_KNOWN_QUOTE}" in known:
            matched.add(f"{c}{_KNOWN_QUOTE}")
    return list(matched)[:5]


def _extract_window_days(question: str) -> int:
    lowered = question.lower()
    for phrase, days in _WINDOW_KEYWORDS:
        if phrase in lowered:
            return days
    return 30


def classify(question: str) -> list[str]:
    """Returns every category whose keywords appear in the question. Empty
    list means no known category matched — gather_context() falls back to a
    small general snapshot rather than guessing a category."""
    lowered = question.lower()
    return [cat for cat, keywords in _CATEGORY_KEYWORDS.items() if any(kw in lowered for kw in keywords)]


def _coin_history(symbol: str) -> dict:
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(TradeOutcome)
                .where(TradeOutcome.symbol == symbol)
                .order_by(TradeOutcome.created_at.desc())
                .limit(10)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    if not rows:
        return {"symbol": symbol, "note": "No trade history for this symbol yet."}

    resolved = [r for r in rows if r.status in ("closed_win", "closed_loss")]
    return {
        "symbol": symbol,
        "total_signals": len(rows),
        "resolved": len(resolved),
        "wins": sum(1 for r in resolved if r.status == "closed_win"),
        "losses": sum(1 for r in resolved if r.status == "closed_loss"),
        "recent_trades": [
            {
                "created_at": r.created_at,
                "direction": r.direction,
                "status": r.status,
                "confidence": r.confidence,
                "grade": r.grade,
                "realized_return_pct": r.realized_return_pct,
                "reasoning": r.reasoning,
                "key_score_component": r.key_score_component,
            }
            for r in rows
        ],
    }


def _coin_snapshots(symbol: str) -> list[dict]:
    """Latest validation snapshots for a symbol's currently-open trade, if
    any — the lifecycle timeline (distance to TP/stop over time), not an
    AI-generated narrative."""
    session = SessionLocal()
    try:
        open_row = session.execute(
            select(TradeOutcome)
            .where(TradeOutcome.symbol == symbol, TradeOutcome.status.in_(["pending", "open"]))
            .order_by(TradeOutcome.created_at.desc())
        ).scalars().first()
        if open_row is None:
            return []
        snaps = (
            session.execute(
                select(PredictionSnapshot)
                .where(PredictionSnapshot.trade_outcome_id == open_row.id)
                .order_by(PredictionSnapshot.timestamp.desc())
                .limit(10)
            )
            .scalars()
            .all()
        )
        return [
            {
                "timestamp": s.timestamp,
                "current_pnl_pct": s.current_pnl_pct,
                "distance_to_tp1_pct": s.distance_to_tp1_pct,
                "distance_to_stop_pct": s.distance_to_stop_pct,
                "status": s.status,
                "reason": s.reason,
            }
            for s in snaps
        ]
    finally:
        session.close()


def _live_opportunities(limit: int = 6) -> list[dict]:
    session = SessionLocal()
    try:
        rows = (
            session.execute(
                select(LiveOpportunity)
                .where(LiveOpportunity.trade_plan.is_not(None))
                .order_by(LiveOpportunity.score_total.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()
    return [
        {
            "symbol": r.symbol,
            "score": r.score_total,
            "last_price": r.last_price,
            "change_24h_pct": r.change_24h_pct,
            "lifecycle_status": r.lifecycle_status,
            "grade": (r.trade_plan or {}).get("grade"),
            "confidence": (r.trade_plan or {}).get("confidence"),
        }
        for r in rows
    ]


def _open_trades() -> list[dict]:
    session = SessionLocal()
    try:
        rows = (
            session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(["pending", "open"])))
            .scalars()
            .all()
        )
    finally:
        session.close()
    return [
        {
            "symbol": r.symbol,
            "direction": r.direction,
            "status": r.status,
            "confidence": r.confidence,
            "grade": r.grade,
            "entry": r.entry,
            "stop_loss": r.stop_loss,
            "tp1": r.tp1,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def gather_context(question: str) -> RouterResult:
    categories = classify(question)
    symbols = _extract_symbols(question)
    window_days = _extract_window_days(question)
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - window_days * _DAY_MS

    data: dict = {}

    if not categories and not symbols:
        # Nothing matched — give Claude a small honest general snapshot
        # instead of either guessing a category or calling with no data.
        categories = ["system_accuracy", "current_trades"]

    if "best_trades_today" in categories or "current_trades" in categories:
        data["live_opportunities"] = _live_opportunities()
    if "current_trades" in categories:
        data["open_trades"] = _open_trades()
        data["open_trade_count"] = trade_reports.open_trade_count()
    if "system_accuracy" in categories:
        data["performance_digest"] = trade_reports.performance_digest(start_ms, now_ms, f"last {window_days}d")
        data["monthly_breakdown"] = trade_reports.monthly_breakdown(start_ms, now_ms)
    if "calibration" in categories:
        data["confidence_calibration"] = trade_reports.confidence_calibration()
        data["grade_calibration"] = trade_reports.grade_calibration()
    if "feature_importance" in categories:
        data["feature_importance"] = trade_reports.feature_importance()
    if "momentum_patterns" in categories:
        data["momentum_vs_runup"] = trade_reports.momentum_vs_runup()
        data["momentum_vs_time_to_tp1"] = trade_reports.momentum_vs_time_to_tp1()
        data["evidence_coverage"] = trade_reports.evidence_coverage()
    if "long_vs_short" in categories:
        data["direction_breakdown"] = trade_reports.direction_breakdown(start_ms, now_ms)
    if "regime_performance" in categories:
        data["current_regime"] = load_current_regime()
        data["monthly_breakdown"] = data.get("monthly_breakdown") or trade_reports.monthly_breakdown(start_ms, now_ms)
    if "retrain" in categories:
        data["retrain_recommendation"] = retrain_recommendation()

    for symbol in symbols:
        data.setdefault("coin_history", {})[symbol] = _coin_history(symbol)
        snaps = _coin_snapshots(symbol)
        if snaps:
            data.setdefault("coin_snapshots", {})[symbol] = snaps

    # Always include current regime as background context, cheap and
    # frequently relevant regardless of category.
    data.setdefault("current_regime", load_current_regime())

    return RouterResult(categories=categories, symbols=symbols, window_days=window_days, data=data)
