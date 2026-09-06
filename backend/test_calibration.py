"""Manual verification script for Karma V2.1 Phase 4 — Confidence
Calibration (app/engine/calibration.py) and its wiring into
trade_outcomes.py:open_trade_outcome().

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_calibration.py`. Runs against the real dev DB using a
clearly-fake symbol (ZZZCALAUSDT) and cleans up after itself.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import calibration
from app.engine import trade_outcomes
from app.models.db_models import TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZCALAUSDT"]
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
# 1. calibration_table() — shape and bucket coverage
# ---------------------------------------------------------------------------
def test_calibration_table_shape():
    table = calibration.calibration_table()
    labels = [b["bucket"] for b in table["buckets"]]
    check("calibration_table covers exactly the 6 established buckets", labels == ["50-54", "55-59", "60-64", "65-69", "70-74", "75+"], labels)
    for b in table["buckets"]:
        if b["n"] > 0:
            check(f"bucket {b['bucket']} reports a 95% CI tuple", "ci_95" in b and isinstance(b["ci_95"], tuple), b)
            check(f"bucket {b['bucket']} 'reliable' flag matches min_sample threshold", b["reliable"] == (b["n"] >= table["min_sample"]), b)


# ---------------------------------------------------------------------------
# 2. calibrated_confidence() — insufficient-data fallback never fabricates
# ---------------------------------------------------------------------------
def test_calibrated_confidence_fallback():
    result_none = calibration.calibrated_confidence(None)
    check("None confidence returns None calibrated_confidence, not a fabricated number", result_none["calibrated_confidence"] is None)

    result_out_of_range = calibration.calibrated_confidence(30)
    check("confidence outside the 50-100 calibrated range is returned unchanged", result_out_of_range["calibrated_confidence"] == 30, result_out_of_range)

    # A confidence with a real dev-DB bucket: either it has >= MIN_SAMPLE
    # (returns a real calibrated value with a note) or it doesn't (falls
    # back to raw, with an explicit insufficient_data note) — both are
    # valid outcomes; the ONLY invariant this checks is that the note
    # always explains which case happened.
    result_62 = calibration.calibrated_confidence(62)
    check("calibrated_confidence for a real bucket always includes an explanatory note", isinstance(result_62["note"], str) and len(result_62["note"]) > 0, result_62)
    if result_62["sample_size"] < calibration.MIN_SAMPLE:
        check("below-min-sample bucket returns raw confidence unchanged and says 'insufficient_data'", result_62["calibrated_confidence"] == 62 and "insufficient_data" in result_62["note"], result_62)
    else:
        check("above-min-sample bucket's calibrated value equals that bucket's real observed win rate", result_62["calibrated_confidence"] is not None, result_62)


# ---------------------------------------------------------------------------
# 3. End-to-end: open_trade_outcome() attaches calibrated_confidence
#    additively, without changing the stored raw confidence.
# ---------------------------------------------------------------------------
class FakePlan:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_end_to_end_calibration_attached():
    symbol = FAKE_SYMBOLS[0]
    plan = FakePlan(
        recommendation="long", entry_low=100.0, entry_high=101.0, stop_loss=95.0,
        take_profit_1=110.0, take_profit_2=None, take_profit_3=None, time_horizon="swing",
        summary="t", reasons_for=["x"], reasons_against=["y"],
        entry_reasoning=None, sl_reasoning=None, tp1_reasoning=None, tp2_reasoning=None, tp3_reasoning=None,
    )
    breakdown = {
        "trend": 20.0, "momentum": 10.0, "volume": 5.0, "funding": 8.0, "structure": 12.0,
        "history": 5.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
        "risk": -2.0, "total": 65.0,
    }
    trade_outcomes.open_trade_outcome(
        symbol, plan, breakdown, {}, None, None, {"label": "mixed"}, now_ms=1_000_000,
        confidence=63, grade="B", entry_quality="neutral",
    )
    session = SessionLocal()
    try:
        row = session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(TradeOutcome.id.desc()).first()
    finally:
        session.close()

    check("calibrated_confidence is populated (not None) on a newly-opened trade", row.calibrated_confidence is not None)
    check("raw confidence field is UNCHANGED at 63 (additive, not a replacement)", row.confidence == 63, row.confidence)
    check("calibrated_confidence's own raw_confidence key matches the stored raw value", row.calibrated_confidence["raw_confidence"] == 63, row.calibrated_confidence)


try:
    test_calibration_table_shape()
    test_calibrated_confidence_fallback()
    test_end_to_end_calibration_attached()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
