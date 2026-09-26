"""Trade Verdict V2 — Karma V3.3-B (analytics / debugging only).

ONE primary verdict per resolved trade, from the fixed taxonomy below. This
is a *classification of what the stored fields show*, not a proof of cause:
the priority order decides which label a multi-cause loss receives, and some
labels describe traits that are true of most trades (see BASE_RATE_NOTE), so
the leaderboard always reports the base rate next to each trait.

Builds on trade_truth.classify_truth (good_entry_bad_exit / near_miss) and
failure_patterns.lifecycle_pattern rather than recomputing path logic.

Never used to gate, score or size trades.
"""

import statistics
from collections import Counter, defaultdict

from sqlalchemy import select

from app.analytics import failure_patterns, trade_truth
from app.db import SessionLocal
from app.models.db_models import TradeOutcome

_TRADED = ("closed_win", "closed_loss")
VERDICTS = [
    "Perfect Trade", "Good Entry Bad Exit", "Good Entry Early Stop", "Bad Entry", "Trend Failure",
    "Structure Failure", "Momentum Exhaustion", "Liquidity / Volatility Failure", "Infrastructure Failure",
    "Scanner Gap", "TP Management Failure", "Unknown",
]

# Thresholds (disclosed; none tuned against outcomes)
SLIPPAGE_INFRA_PCT = -5.0        # stop filled >=5% beyond the level -> price gapped through it
STRUCTURE_WEAK_BELOW = 9         # matches red_flags.weak_structure
TREND_WEAK_BELOW = 18            # trend_score below this (max 25)
ATR_EXTENSION_MAX = 2.5          # |ATR distance from EMA20|
SLIPPAGE_VOL_PCT = -2.0          # with a top-tercile ATR% => volatility failure

BASE_RATE_NOTE = (
    "Priority order matters: a loss gets the FIRST matching label. Structure/trend/momentum labels describe "
    "traits present in many winners too (compare the base-rate columns), so they are descriptive, not causal."
)


def _entry_ind(row) -> dict:
    return row.entry_indicators or {}


def atr_pct(row) -> float | None:
    """Entry ATR as % of price, from the stored risk figures (risk% / stop distance in ATR)."""
    rr = _entry_ind(row).get("risk_reward") or {}
    e, rp = rr.get("entry_to_sl_atr"), rr.get("risk_to_sl_pct")
    if e and rp:
        return rp / e
    a = (row.level_reasoning or {}).get("atr_at_entry")
    return a / row.entry * 100 if a and row.entry else None


def _btc_counter(row) -> bool | None:
    b = _entry_ind(row).get("btc_trend")
    if b not in ("bull", "bear"):
        return None
    return (b == "bull") != (row.direction == "long")


def _momentum_exhausted(row) -> bool:
    i = _entry_ind(row)
    return ((i.get("rsi14") or 0) >= 70 or (i.get("mfi") or 0) > 80 or (i.get("stoch_rsi") or 0) > 0.9
            or abs(i.get("atr_distance_to_ema20") or 0) > ATR_EXTENSION_MAX)


def primary_verdict(row: TradeOutcome, outages: list[dict] | None = None, high_atr_pct: float | None = None) -> dict:
    """Returns {'verdict', 'rule', 'traits'}. `high_atr_pct` = the top-tercile cutoff of entry ATR% over
    resolved trades (pass it in when classifying many rows; None disables the volatility clause)."""
    outages = outages or []
    truth = trade_truth.classify_truth(row, outages)["verdict"]
    life = failure_patterns.lifecycle_pattern(row)
    in_gap = trade_truth._in_outage(row.exit_time, outages)
    traits = {
        "weak_structure": (row.structure_score is not None and row.structure_score < STRUCTURE_WEAK_BELOW),
        "weak_trend": (row.trend_score is not None and row.trend_score < TREND_WEAK_BELOW),
        "counter_btc_trend": _btc_counter(row),
        "momentum_exhausted": _momentum_exhausted(row),
        "thin_liquidity": (row.liquidity_score is not None and row.liquidity_score < 0),
        "exit_in_monitoring_gap": bool(in_gap),
        "lifecycle": life,
    }

    def out(v, rule):
        return {"verdict": v, "rule": rule, "traits": traits}

    if row.status == "closed_win":
        if (row.max_drawdown_pct or 0) >= trade_truth.PERFECT_TRADE_MAX_DRAWDOWN_PCT:
            return out("Perfect Trade", f"win with MAE >= {trade_truth.PERFECT_TRADE_MAX_DRAWDOWN_PCT}%")
        if truth == "good_entry_bad_exit":
            return out("Good Entry Bad Exit", "Trade-Truth: good_entry_bad_exit")
        return out("Unknown", "win with deep drawdown; no further label supported by stored fields")

    # ---- losses, in priority order
    if row.stop_slippage_pct is not None and row.stop_slippage_pct <= SLIPPAGE_INFRA_PCT:
        return out("Infrastructure Failure", f"stop slippage <= {SLIPPAGE_INFRA_PCT}% (price gapped through the stop)")
    if in_gap:
        return out("Scanner Gap", "exit occurred inside a monitoring gap")
    if row.tp1_hit:
        return out("TP Management Failure", "TP1 had been reached before the loss")
    if truth == "near_miss_early_stop":
        return out("Good Entry Early Stop", "MFE reached >=80% of the TP1 distance before the stop")
    thin = traits["thin_liquidity"]
    vol = (high_atr_pct is not None and (atr_pct(row) or 0) >= high_atr_pct and (row.stop_slippage_pct or 0) <= SLIPPAGE_VOL_PCT)
    if thin or vol:
        return out("Liquidity / Volatility Failure", "thin book, or top-tercile ATR% with >=2% stop slippage")
    if traits["momentum_exhausted"]:
        return out("Momentum Exhaustion", "RSI>=70 / MFI>80 / StochRSI>0.9 / >2.5 ATR extended at entry")
    if traits["weak_structure"]:
        return out("Structure Failure", f"structure_score < {STRUCTURE_WEAK_BELOW}")
    if traits["weak_trend"] or traits["counter_btc_trend"]:
        return out("Trend Failure", f"trend_score < {TREND_WEAK_BELOW} or entry against the BTC trend")
    if life == "immediate_reversal":
        return out("Bad Entry", "immediate reversal not explained by a more specific label")
    return out("Unknown", "no stored field supports a more specific label")


def _rows() -> list[TradeOutcome]:
    session = SessionLocal()
    try:
        return session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(_TRADED))).scalars().all()
    finally:
        session.close()


def _context(rows):
    from app.engine import performance_center as pc

    outages = pc.scanner_health(10).get("outages", [])
    atrs = sorted(a for a in (atr_pct(r) for r in rows) if a)
    high = atrs[int(len(atrs) * 2 / 3)] if len(atrs) >= 6 else None  # top-tercile cutoff
    return outages, high


def verdict_for_trade(trade_outcome_id: int) -> dict | None:
    session = SessionLocal()
    try:
        row = session.execute(select(TradeOutcome).where(TradeOutcome.id == trade_outcome_id)).scalar_one_or_none()
    finally:
        session.close()
    if row is None or row.status not in _TRADED:
        return None
    outages, high = _context(_rows())
    v = primary_verdict(row, outages, high)
    return {"trade_outcome_id": row.id, "symbol": row.symbol, "status": row.status, "realized_return_pct": row.realized_return_pct, **v}


def _trait_rate(rows, pred):
    n = len(rows)
    return round(sum(1 for r in rows if pred(r)) / n * 100, 1) if n else None


def verdict_leaderboard() -> dict:
    rows = _rows()
    if not rows:
        return {"n": 0, "verdicts": [], "note": "No resolved trades yet."}
    outages, high = _context(rows)
    by = defaultdict(list)
    for r in rows:
        by[primary_verdict(r, outages, high)["verdict"]].append(r)
    total_loss = -sum(r.realized_return_pct for r in rows if r.status == "closed_loss" and r.realized_return_pct is not None) or None
    board = []
    for v in VERDICTS:
        sub = by.get(v, [])
        rets = [r.realized_return_pct for r in sub if r.realized_return_pct is not None]
        wins = sum(1 for r in sub if r.status == "closed_win")
        board.append({
            "verdict": v, "n": len(sub),
            "win_rate_pct": round(wins / len(sub) * 100, 1) if sub else None,
            "avg_return_pct": round(sum(rets) / len(rets), 3) if rets else None,
            "median_return_pct": round(statistics.median(rets), 3) if rets else None,
            "total_pnl_contribution_pp": round(sum(rets), 1) if rets else 0.0,
            "top_symbols": [{"symbol": s, "n": c} for s, c in Counter(r.symbol for r in sub).most_common(5)],
        })
    losses = [r for r in rows if r.status == "closed_loss"]
    wins_ = [r for r in rows if r.status == "closed_win"]
    trait_tests = {
        "weak_structure": lambda r: r.structure_score is not None and r.structure_score < STRUCTURE_WEAK_BELOW,
        "weak_trend_or_counter_btc": lambda r: (r.trend_score is not None and r.trend_score < TREND_WEAK_BELOW) or _btc_counter(r) is True,
        "momentum_exhausted": _momentum_exhausted,
    }
    base_rates = [{
        "trait": k, "share_of_all_trades_pct": _trait_rate(rows, f), "share_of_losses_pct": _trait_rate(losses, f), "share_of_wins_pct": _trait_rate(wins_, f),
    } for k, f in trait_tests.items()]
    infra = sum(b["total_pnl_contribution_pp"] for b in board if b["verdict"] in ("Infrastructure Failure", "Scanner Gap"))
    return {
        "n": len(rows),
        "verdicts": board,
        "base_rates": base_rates,
        "infrastructure_share_of_loss_magnitude_pct": round(-infra / total_loss * 100, 1) if total_loss else None,
        "note": BASE_RATE_NOTE,
    }
