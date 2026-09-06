"""Karma V2.1 — measurement-only score recalibration analysis. READ ONLY:
does not modify scoring.py, weights, or any DB row. Produces
feature_importance.json and score_recalibration_report.md.

This replaces the V2.1-C commit's direct scoring.py edits (reverted) per
explicit instruction: measurement and implementation must be two separate,
separately-approved steps. Nothing computed here is used to change
trading behavior until a human reads this report and explicitly says so.
"""

import json
import math
import statistics
import sys

sys.path.insert(0, ".")

from app.db import SessionLocal
from app.models.db_models import TradeOutcome
from scipy.stats import fisher_exact
from sqlalchemy import select

session = SessionLocal()
all_trades = session.execute(select(TradeOutcome)).scalars().all()
session.close()

entered = [r for r in all_trades if r.status in ("closed_win", "closed_loss")]
wins = [r for r in entered if r.status == "closed_win"]
N = len(entered)
OVERALL_WIN_RATE = len(wins) / N if N else None
print(f"n={N} wins={len(wins)} overall_win_rate={OVERALL_WIN_RATE}")


def wilson_ci(successes, n, z=1.96):
    if n == 0:
        return (None, None)
    phat = successes / n
    denom = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    half = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    return (round(max(0, (center - half) / denom) * 100, 1), round(min(1, (center + half) / denom) * 100, 1))


def entropy(p):
    if p <= 0 or p >= 1:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def information_gain(present_rows, absent_rows, all_rows):
    n = len(all_rows)
    if n == 0:
        return None
    h_total = entropy(sum(1 for r in all_rows if r.status == "closed_win") / n)
    h_present = entropy(sum(1 for r in present_rows if r.status == "closed_win") / len(present_rows)) if present_rows else 0.0
    h_absent = entropy(sum(1 for r in absent_rows if r.status == "closed_win") / len(absent_rows)) if absent_rows else 0.0
    weighted = (len(present_rows) / n) * h_present + (len(absent_rows) / n) * h_absent
    return round(h_total - weighted, 4)


def odds_ratio_and_p(win_present, loss_present, win_absent, loss_absent):
    table = [[win_present, loss_present], [win_absent, loss_absent]]
    try:
        odds, p = fisher_exact(table)
        return round(odds, 3) if math.isfinite(odds) else None, round(p, 4)
    except Exception:
        return None, None


def pct(n, d):
    return round(n / d * 100, 1) if d else None


def avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def analyze_feature(name: str, predicate) -> dict:
    """predicate(row) -> True/False/None (None = not applicable/no data)."""
    flags = [predicate(r) for r in entered]
    if all(f is None for f in flags):
        return {"feature": name, "available": False, "note": "Not stored per-trade in this codebase — not computed, not fabricated."}

    present = [r for r, f in zip(entered, flags) if f is True]
    absent = [r for r, f in zip(entered, flags) if f is False]
    if len(present) < 3 or len(absent) < 3:
        return {
            "feature": name, "available": True,
            "n_present": len(present), "n_absent": len(absent),
            "note": "Fewer than 3 trades on one side — insufficient for reliable statistics.",
        }

    win_present = sum(1 for r in present if r.status == "closed_win")
    win_absent = sum(1 for r in absent if r.status == "closed_win")
    win_rate_present = pct(win_present, len(present))
    win_rate_absent = pct(win_absent, len(absent))
    ci_present = wilson_ci(win_present, len(present))
    odds, p_value = odds_ratio_and_p(win_present, len(present) - win_present, win_absent, len(absent) - win_absent)
    ig = information_gain(present, absent, entered)

    return {
        "feature": name, "available": True,
        "n_present": len(present), "n_absent": len(absent),
        "win_rate_present_pct": win_rate_present, "win_rate_present_ci_95": ci_present,
        "win_rate_absent_pct": win_rate_absent,
        "avg_return_present_pct": avg([r.realized_return_pct for r in present]),
        "avg_return_absent_pct": avg([r.realized_return_pct for r in absent]),
        "tp1_rate_present_pct": pct(sum(1 for r in present if r.tp1_hit), len(present)),
        "tp2_rate_present_pct": pct(sum(1 for r in present if r.tp2_hit), len(present)),
        "tp3_rate_present_pct": pct(sum(1 for r in present if r.tp3_hit), len(present)),
        "stop_rate_present_pct": pct(sum(1 for r in present if r.stop_hit), len(present)),
        "odds_ratio": odds, "p_value_fisher_exact": p_value,
        "lift_vs_overall_pct_points": round(win_rate_present - OVERALL_WIN_RATE * 100, 1) if OVERALL_WIN_RATE is not None else None,
        "information_gain_bits": ig,
    }


def ei(r):
    return r.entry_indicators or {}


def lr(r):
    return r.level_reasoning or {}


FEATURES = {
    "trend_high (trend_score>=22)": lambda r: (r.trend_score >= 22) if r.trend_score is not None else None,
    "structure_high (structure_score>=9)": lambda r: (r.structure_score >= 9) if r.structure_score is not None else None,
    "momentum_high (momentum_score>=14)": lambda r: (r.momentum_score >= 14) if r.momentum_score is not None else None,
    "volume_high (volume_score>=8)": lambda r: (r.volume_score >= 8) if r.volume_score is not None else None,
    "funding_high (funding_score>=8)": lambda r: (r.funding_score >= 8) if r.funding_score is not None else None,
    "history_present": lambda r: (r.history_score > 0) if r.history_score is not None else None,
    "regime_mixed": lambda r: (r.market_regime == "mixed") if r.market_regime else None,
    "entry_quality_excellent": lambda r: (r.entry_quality == "excellent") if r.entry_quality else None,
    "cmf_positive": lambda r: ((ei(r).get("cmf") or 0) > 0) if ei(r).get("cmf") is not None else None,
    "obv": lambda r: None,  # not stored per-trade anywhere in this codebase
    "rsi_healthy_50_70": lambda r: (50 <= ei(r)["rsi14"] < 70) if ei(r).get("rsi14") is not None else None,
    "adx_trending_20_50": lambda r: (20 <= ei(r)["adx14"] < 50) if ei(r).get("adx14") is not None else None,
    "fvg_present": lambda r: bool(lr(r).get("fvg_used")) if lr(r) else None,
    "bos": lambda r: None,  # not stored per-trade anywhere in this codebase
    "choch": lambda r: None,  # not stored per-trade anywhere in this codebase
}

results = [analyze_feature(name, fn) for name, fn in FEATURES.items()]

with open("feature_importance.json", "w") as f:
    json.dump({
        "n_resolved_trades": N,
        "overall_win_rate_pct": round(OVERALL_WIN_RATE * 100, 1) if OVERALL_WIN_RATE else None,
        "methodology": (
            "Fisher's exact test odds ratio + p-value (appropriate for small-sample 2x2 tables), "
            "information gain in bits (entropy reduction on win/loss from knowing the feature), "
            "and a 95% Wilson CI on the present-side win rate. NOT a trained model of any kind."
        ),
        "features": results,
    }, f, indent=2, default=str)

print("wrote feature_importance.json")
for r in results:
    print(r.get("feature"), "->", {k: v for k, v in r.items() if k != "feature"})
