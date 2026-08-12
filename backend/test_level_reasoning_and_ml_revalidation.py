"""Manual verification script for two independent pieces of work:

1. Per-trade level-reasoning capture (task: "stop letting Claude be the
   only source of truth for risk levels going forward") — smart_money.py's
   newly-exposed structure price levels, entry_flags.py's ATR-normalized
   risk/reward, and trade_outcomes.py's _capture_level_reasoning /
   open_trade_outcome wiring.
2. ml_model.py's new evaluate_calibration() — Brier score, log loss, and
   bucketed hit-rate reporting added on top of the (already-correct,
   confirmed by reading the code) chronological train/test split.

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_level_reasoning_and_ml_revalidation.py`. DB-touching checks
use clearly-fake symbols (ZZZLR*) and clean up after themselves.
"""

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import entry_flags, ml_model, smart_money, trade_outcomes
from app.models.db_models import TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZLRAUSDT"]
FAILURES = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} {detail}")
        FAILURES.append(name)


def cleanup():
    session = SessionLocal()
    try:
        session.query(TradeOutcome).filter(TradeOutcome.symbol.in_(FAKE_SYMBOLS)).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. smart_money.compute_structure(): nearest_swing_high/low + FVG bounds
#    are the exact values the existing bos/choch/fvg booleans were already
#    computed from, not a new formula.
# ---------------------------------------------------------------------------
def test_structure_levels_exposed():
    # Handcrafted candles: a clean swing low at index 2 (10), then a strong
    # up-impulse candle (index 4) leaving a bullish FVG between candle[2].high
    # and candle[4].low, then price breaks the prior swing high to confirm
    # a swing high (index 6) was tracked as nearest_swing_high.
    data = {
        "open":  [50, 48, 43, 55, 70, 68, 66, 65, 64],
        "high":  [52, 50, 46, 58, 72, 69, 90, 66, 65],
        "low":   [48, 47, 44, 54, 65, 66, 64, 63, 62],
        "close": [49, 45, 45, 57, 71, 67, 89, 64, 63],
    }
    df = pd.DataFrame(data)
    structure = smart_money.compute_structure(df, lookback=2)

    check(
        "nearest_swing_low tracks the confirmed fractal low (44 at idx 2)",
        structure["nearest_swing_low"].iloc[3] == 44,
        structure["nearest_swing_low"].iloc[3],
    )
    fvg_row = structure[structure["fvg_up"]]
    if len(fvg_row):
        i = fvg_row.index[0]
        check(
            f"fvg_up_bottom/top match high[i-2]/low[i] at idx {i}",
            structure["fvg_up_bottom"].iloc[i] == df["high"].iloc[i - 2]
            and structure["fvg_up_top"].iloc[i] == df["low"].iloc[i],
            (structure["fvg_up_bottom"].iloc[i], structure["fvg_up_top"].iloc[i]),
        )
    else:
        check("fvg_up detected in synthetic data", False, "no fvg_up row found — fixture needs adjustment")

    check(
        "non-FVG candles have null fvg_up_bottom/top",
        pd.isna(structure["fvg_up_bottom"].iloc[0]) and pd.isna(structure["fvg_up_top"].iloc[0]),
    )


# ---------------------------------------------------------------------------
# 2. entry_flags.compute_risk_reward(): ATR-normalized distances.
# ---------------------------------------------------------------------------
def test_atr_normalized_risk_reward():
    rr = entry_flags.compute_risk_reward(entry=100.0, stop_loss=95.0, tp1=110.0, tp2=120.0, tp3=None, atr14=5.0)
    check("entry_to_sl_atr = |100-95|/5 = 1.0", rr["entry_to_sl_atr"] == 1.0, rr["entry_to_sl_atr"])
    check("entry_to_tp1_atr = |110-100|/5 = 2.0", rr["entry_to_tp1_atr"] == 2.0, rr["entry_to_tp1_atr"])
    check("entry_to_tp2_atr = |120-100|/5 = 4.0", rr["entry_to_tp2_atr"] == 4.0, rr["entry_to_tp2_atr"])
    check("entry_to_tp3_atr is None when tp3 is None", rr["entry_to_tp3_atr"] is None)

    rr_no_atr = entry_flags.compute_risk_reward(entry=100.0, stop_loss=95.0, tp1=110.0, tp2=None, tp3=None)
    check(
        "ATR fields default to None when atr14 not supplied (never guessed)",
        rr_no_atr["entry_to_sl_atr"] is None and rr_no_atr["entry_to_tp1_atr"] is None,
    )
    check(
        "pre-existing pct/RR fields unchanged by the new atr14 param",
        rr["risk_to_sl_pct"] == 5.0 and rr["rr_tp1"] == 2.0,
        (rr["risk_to_sl_pct"], rr["rr_tp1"]),
    )


# ---------------------------------------------------------------------------
# 3. trade_outcomes._capture_level_reasoning + open_trade_outcome wiring —
#    end to end, against the real dev DB.
# ---------------------------------------------------------------------------
class FakePlan:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_level_reasoning_captured_end_to_end():
    symbol = FAKE_SYMBOLS[0]
    plan = FakePlan(
        recommendation="long", entry_low=100.0, entry_high=101.0, stop_loss=95.0,
        take_profit_1=110.0, take_profit_2=120.0, take_profit_3=None, time_horizon="swing",
        summary="t", reasons_for=["x"], reasons_against=["y"],
        entry_reasoning="Entering on reclaim of prior range.",
        sl_reasoning="Below the last swing low.",
        tp1_reasoning="At the FVG midpoint.",
        tp2_reasoning="Prior resistance turned support target.",
        tp3_reasoning=None,
    )
    features = {
        "indicators_4h": {"atr14": 5.0},
        "structure_4h": {
            "nearest_swing_high": 130.0, "nearest_swing_low": 90.0,
            "fvg_up": True, "fvg_up_bottom": 98.0, "fvg_up_top": 102.0,
            "fvg_down": False, "fvg_down_top": None, "fvg_down_bottom": None,
        },
    }
    breakdown = {
        "trend": 20.0, "momentum": 10.0, "volume": 5.0, "funding": 8.0, "structure": 12.0,
        "history": 5.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
        "risk": -2.0, "total": 65.0,
    }
    trade_outcomes.open_trade_outcome(
        symbol, plan, breakdown, features, None, None, {"label": "risk_on"}, now_ms=9_000_000,
        confidence=70, grade="B+",
    )
    session = SessionLocal()
    try:
        row = session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(
            TradeOutcome.id.desc()
        ).first()
    finally:
        session.close()

    lr = row.level_reasoning
    check("level_reasoning stored on the row (not None)", lr is not None)
    check("entry_reasoning captured verbatim", lr["entry_reasoning"] == "Entering on reclaim of prior range.", lr)
    check("tp3_reasoning is None when take_profit_3 is None", lr["tp3_reasoning"] is None)
    check("atr_at_entry captured", lr["atr_at_entry"] == 5.0, lr["atr_at_entry"])
    check(
        "structure_level_used = nearest_swing_high for a LONG (resistance measured against)",
        lr["structure_level_used"] == 130.0, lr["structure_level_used"],
    )
    check("nearest_support/resistance both present regardless of direction", lr["nearest_support"] == 90.0 and lr["nearest_resistance"] == 130.0)
    check("fvg_used populated from the active up-FVG", lr["fvg_used"] == {"direction": "up", "bottom": 98.0, "top": 102.0}, lr["fvg_used"])
    check("order_block_note explicitly reports the gap rather than fabricating a value", "Not detected" in lr["order_block_note"])

    ei = row.entry_indicators
    # entry_mid = (100.0 + 101.0) / 2 = 100.5, so |100.5-95|/5.0 = 1.1
    check("entry_indicators.risk_reward carries the new ATR fields too", ei["risk_reward"]["entry_to_sl_atr"] == 1.1, ei["risk_reward"])


# ---------------------------------------------------------------------------
# 4. ml_model.evaluate_calibration() — Brier score sanity + bucket gating.
# ---------------------------------------------------------------------------
class _FakeModel:
    """predict_proba returning fixed values, no real XGBoost needed here —
    this test is about evaluate_calibration()'s own math, not model fit."""
    def __init__(self, probs):
        self._probs = np.array(probs)

    def predict_proba(self, X):
        return np.column_stack([1 - self._probs, self._probs])


def test_calibration_reporting():
    # A perfectly calibrated toy: 10 rows at predicted 0.9, 9 of them win.
    probs = [0.9] * 10
    y = np.array([1] * 9 + [0])
    result = ml_model.evaluate_calibration(_FakeModel(probs), np.zeros((10, 1)), y, min_bucket_n=5)
    check("brier_score present and low for a near-perfectly-calibrated toy set", result["brier_score"] < 0.15, result["brier_score"])
    bucket_90 = next(b for b in result["buckets"] if b["predicted_range"] == "0.8-1.0")
    check("0.8-1.0 bucket has n=10 and actual_hit_rate ~0.9", bucket_90["n"] == 10 and bucket_90["actual_hit_rate"] == 0.9, bucket_90)

    bucket_40 = next(b for b in result["buckets"] if b["predicted_range"] == "0.4-0.6")
    check("empty bucket reports insufficient rather than a fabricated 0", "note" in bucket_40 and "actual_hit_rate" not in bucket_40, bucket_40)

    check("evaluate_calibration returns None for single-class y (AUC/Brier undefined)", ml_model.evaluate_calibration(_FakeModel([0.5]), np.zeros((1, 1)), np.array([1])) is None)


try:
    test_structure_levels_exposed()
    test_atr_normalized_risk_reward()
    test_level_reasoning_captured_end_to_end()
    test_calibration_reporting()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
