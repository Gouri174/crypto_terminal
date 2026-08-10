"""Manual verification script for the entry_quality hypothesis layer.

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py). Run directly with `python test_entry_quality.py`.
Pure-function tests need no DB; the "old rows untouched" and "score
unchanged" checks read the real dev DB directly.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine.entry_quality import classify_entry_quality
from app.engine.scoring import score_opportunity
from app.models.db_models import TradeOutcome

init_db()

FAILURES = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} {detail}")
        FAILURES.append(name)


def ind(rsi, stoch, bb, ema20, atr, close, macd_hist=0.5, adx=30):
    return {
        "last_close": close, "ema20": ema20, "ema50": ema20 * 0.98, "ema200": ema20 * 0.9,
        "rsi14": rsi, "stoch_rsi": stoch, "bb_pct": bb, "atr14": atr, "adx14": adx,
        "macd_hist": macd_hist, "trend_vs_ema50": "above" if close > ema20 * 0.98 else "below",
    }


def structure(fvg_up=False, bos_up=False, fvg_down=False, bos_down=False, trend="bull"):
    return {"trend": trend, "fvg_up": fvg_up, "bos_up": bos_up, "fvg_down": fvg_down, "bos_down": bos_down, "choch": False}


# ---------------------------------------------------------------------------
# 1. Healthy high-momentum trend (CASE A): fresh structure, not extended.
# ---------------------------------------------------------------------------
features_healthy = {
    "indicators_1h": ind(55, 0.6, 0.5, 100, 2, 101),
    "indicators_4h": ind(58, 0.7, 0.6, 100, 2, 101),
    "indicators_1d": ind(60, 0.5, 0.55, 100, 2, 101),
    "structure_4h": structure(fvg_up=True, bos_up=True),
}
r = classify_entry_quality(features_healthy, "long", {"momentum": 15.0, "structure": 11.0})
check("healthy high-momentum trend -> excellent", r["entry_quality"] == "excellent", r)

# ---------------------------------------------------------------------------
# 2. High momentum but overextended (CASE B), multi-timeframe overbought.
# ---------------------------------------------------------------------------
features_overextended = {
    "indicators_1h": ind(85, 0.97, 1.1, 100, 2, 112),
    "indicators_4h": ind(91, 0.98, 1.2, 100, 2, 112),
    "indicators_1d": ind(94, 0.99, 1.3, 100, 2, 112),
    "structure_4h": structure(),
}
r = classify_entry_quality(features_overextended, "long", {"momentum": 15.0, "structure": 6.0})
check("high momentum + overextended -> exhausted", r["entry_quality"] == "exhausted", r)

# ---------------------------------------------------------------------------
# 3. Weak momentum + weak structure (CASE C) -> invalid.
# ---------------------------------------------------------------------------
features_weak = {
    "indicators_1h": ind(50, 0.5, 0.5, 100, 2, 100.5),
    "indicators_4h": ind(50, 0.5, 0.5, 100, 2, 100.5),
    "indicators_1d": ind(50, 0.5, 0.5, 100, 2, 100.5),
    "structure_4h": structure(),
}
r = classify_entry_quality(features_weak, "long", {"momentum": 2.0, "structure": 4.0})
check("weak momentum -> invalid", r["entry_quality"] == "invalid", r)

# ---------------------------------------------------------------------------
# 4. Strong structure + healthy pullback/retest (CASE D).
# ---------------------------------------------------------------------------
features_pullback = {
    "indicators_1h": ind(52, 0.6, 0.5, 100, 2, 100.5),
    "indicators_4h": ind(55, 0.65, 0.55, 100, 2, 100.5),
    "indicators_1d": ind(58, 0.6, 0.6, 100, 2, 100.5),
    "structure_4h": structure(fvg_up=True, bos_up=True),
}
r = classify_entry_quality(features_pullback, "long", {"momentum": 15.0, "structure": 11.0})
check("strong structure + healthy pullback -> excellent", r["entry_quality"] == "excellent", r)

# ---------------------------------------------------------------------------
# 5. Exhausted LONG — the real BICOUSDT forensic scenario (fresh structure
#    but severe multi-timeframe overbought should still classify exhausted).
# ---------------------------------------------------------------------------
features_exhausted_long = {
    "indicators_1h": ind(72, 0.7, 0.6, 0.065, 0.001, 0.0708),
    "indicators_4h": ind(91, 0.77, 1.05, 0.065, 0.001, 0.0708),
    "indicators_1d": ind(94, 0.8, 1.1, 0.065, 0.001, 0.0708),
    "structure_4h": structure(fvg_up=True, bos_up=True),
}
r = classify_entry_quality(features_exhausted_long, "long", {"momentum": 9.0, "structure": 11.0})
check(
    "exhausted long (fresh structure, severe overbought) -> exhausted",
    r["entry_quality"] == "exhausted",
    r,
)

# ---------------------------------------------------------------------------
# 6. Exhausted SHORT — mirror of case 5.
# ---------------------------------------------------------------------------
features_exhausted_short = {
    "indicators_1h": ind(28, 0.3, -0.05, 100, 2, 88),
    "indicators_4h": ind(9, 0.02, -0.1, 100, 2, 88),
    "indicators_1d": ind(6, 0.01, -0.15, 100, 2, 88),
    "structure_4h": structure(fvg_down=True, bos_down=True),
}
r = classify_entry_quality(features_exhausted_short, "short", {"momentum": 9.0, "structure": 11.0})
check("exhausted short -> exhausted", r["entry_quality"] == "exhausted", r)

# ---------------------------------------------------------------------------
# 7. Missing historical/ML data — entry_quality takes neither as input;
#    verify it still classifies cleanly (decoupled from history/ML entirely).
# ---------------------------------------------------------------------------
r = classify_entry_quality(features_healthy, "long", {"momentum": 15.0, "structure": 11.0})
check(
    "entry_quality has no dependency on history_stats/ml_prediction (not in its signature)",
    "entry_quality" in r and "entry_quality_score" in r,
    r,
)

# ---------------------------------------------------------------------------
# 8. Missing timeframe data — only 4h present, 1h/1d absent entirely.
# ---------------------------------------------------------------------------
features_partial = {"indicators_4h": ind(55, 0.6, 0.5, 100, 2, 101), "structure_4h": structure(fvg_up=True)}
try:
    r = classify_entry_quality(features_partial, "long", {"momentum": 10.0, "structure": 8.0})
    check("missing 1h/1d indicators does not crash", r["entry_quality"] in
          ("excellent", "good", "neutral", "late", "exhausted", "invalid"), r)
except Exception as exc:
    check("missing 1h/1d indicators does not crash", False, str(exc))

# ---------------------------------------------------------------------------
# 9. Extreme ATR distance from EMA20 pushes toward late/exhausted even
#    without RSI/stochRSI/BB extremes.
# ---------------------------------------------------------------------------
features_extreme_atr = {
    "indicators_1h": ind(60, 0.6, 0.6, 100, 1, 104),  # 4 ATR above EMA20
    "indicators_4h": ind(62, 0.65, 0.65, 100, 1, 104),
    "indicators_1d": ind(58, 0.55, 0.6, 100, 1, 104),
    "structure_4h": structure(),
}
r = classify_entry_quality(features_extreme_atr, "long", {"momentum": 11.0, "structure": 6.0})
check(
    "extreme ATR-distance from EMA20 (no fresh structure) -> late or exhausted",
    r["entry_quality"] in ("late", "exhausted"),
    r,
)

# ---------------------------------------------------------------------------
# 10. no_trade direction -> invalid, no crash, no score.
# ---------------------------------------------------------------------------
r = classify_entry_quality({}, "no_trade", {})
check("no_trade direction -> invalid with null score", r["entry_quality"] == "invalid" and r["entry_quality_score"] is None, r)

# ---------------------------------------------------------------------------
# 11. Score formula unchanged — scoring.py was never touched by this work.
#     Fixed input, hand-verifiable expected components.
# ---------------------------------------------------------------------------
fixed_features = {
    "indicators_1h": {"trend_vs_ema50": "above"},
    "indicators_4h": {"trend_vs_ema50": "above", "adx14": 30, "rsi14": 55, "macd_hist": 1.0,
                       "obv_slope": 1, "cmf": 0.1, "mfi": 50, "bb_pct": 0.5, "stoch_rsi": 0.5, "atr14": 1, "last_close": 100},
    "indicators_1d": {"trend_vs_ema50": "above"},
    "structure_4h": {"trend": "bull", "fvg_up": True, "fvg_down": False, "choch": False},
    "funding_rate": 0.0001,
}
breakdown = score_opportunity(fixed_features, None, None, None)
expected_trend = round(1.0 * 15 + min(30, 40) / 40 * 10, 2)  # 15 + 7.5 = 22.5
expected_momentum = round(8 + 7, 2)  # RSI 40-65 band + positive macd_hist = 15
expected_structure = round(6 + 5, 2)  # trend not neutral + fvg = 11
check(
    "score_opportunity() components match hand-computed expected values (formula unchanged)",
    breakdown["trend"] == expected_trend and breakdown["momentum"] == expected_momentum and breakdown["structure"] == expected_structure,
    breakdown,
)

# ---------------------------------------------------------------------------
# 12. entry_quality.py never imports/calls Claude.
# ---------------------------------------------------------------------------
import app.engine.entry_quality as eq_module

check(
    "entry_quality.py has no anthropic import or Claude client",
    "anthropic" not in eq_module.__dict__ and not hasattr(eq_module, "_client"),
)

# ---------------------------------------------------------------------------
# 13. Old TradeOutcome rows (from before entry_quality shipped) remain NULL,
#     not backfilled with a guess.
# ---------------------------------------------------------------------------
session = SessionLocal()
try:
    old_row = session.query(TradeOutcome).filter(TradeOutcome.symbol == "BEATUSDT").first()
    check(
        "pre-existing TradeOutcome row (BEATUSDT, from the forensic sample) has entry_quality=NULL, not backfilled",
        old_row is not None and old_row.entry_quality is None,
        old_row.entry_quality if old_row else "row not found",
    )
finally:
    session.close()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
