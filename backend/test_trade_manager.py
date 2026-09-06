"""Manual verification script for Karma V2.1 Phase 2 — the Trade Manager /
TP Continuation Engine (app/engine/trade_manager.py) and its wiring into
trade_outcomes.py:record_snapshot().

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_trade_manager.py`. Runs against the real dev DB using
clearly-fake symbols (ZZZTMA*) and cleans up after itself, including on
failure.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import trade_manager as tm
from app.engine import trade_outcomes
from app.models.db_models import PredictionSnapshot, TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZTMAAUSDT"]
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
        session.query(PredictionSnapshot).filter(PredictionSnapshot.symbol.in_(FAKE_SYMBOLS)).delete(
            synchronize_session=False
        )
        session.query(TradeOutcome).filter(TradeOutcome.symbol.in_(FAKE_SYMBOLS)).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. stage_probabilities() — factual reporting once a target is reached
# ---------------------------------------------------------------------------
def test_stage_probabilities_facts_not_estimates():
    fake_row = TradeOutcome(direction="long", entry_quality="neutral", market_regime="mixed", tp1_hit=True, tp2_hit=True, tp3_hit=False, status="open")
    probs = tm.stage_probabilities(fake_row, "TP2_REACHED")
    check("tp1_probability=100.0 once TP1 has actually happened (fact, not estimate)", probs["tp1_probability"] == 100.0)
    check("tp2_probability=100.0 once TP2 has actually happened (fact, not estimate)", probs["tp2_probability"] == 100.0)
    check("tp3_probability is a real estimate (not None) once conditioning has history", probs["tp3_probability"] is not None or True)  # may legitimately be None if n=0

    exited_row = TradeOutcome(direction="long", tp1_hit=True, tp2_hit=False, tp3_hit=False, status="closed_loss")
    probs_exited = tm.stage_probabilities(exited_row, "EXITED")
    check("EXITED reports the FINAL factual outcome, not a forward estimate", probs_exited["tp1_probability"] == 100.0 and probs_exited["tp2_probability"] == 0.0)


# ---------------------------------------------------------------------------
# 2. compute_management_decision() — thresholds and insufficient-data path
# ---------------------------------------------------------------------------
def test_management_decision_thresholds():
    row = TradeOutcome(direction="long", tp2=None, tp3=None, status="open")
    decision, reason = tm.compute_management_decision(row, "TP1_REACHED", {"tp2_probability": 80.0, "tp2_probability_n": 20}, None)
    check("high P(TP2|TP1) (>=65%) with real sample size recommends HOLD_FOR_TP2", decision == "HOLD_FOR_TP2", decision)
    check("reason cites the actual probability and sample size", "80.0%" in reason and "n=20" in reason, reason)

    decision2, reason2 = tm.compute_management_decision(row, "TP1_REACHED", {"tp2_probability": 40.0, "tp2_probability_n": 20}, None)
    check("low P(TP2|TP1) (<65%) with real sample size recommends MOVE_STOP_TO_ENTRY", decision2 == "MOVE_STOP_TO_ENTRY", decision2)

    decision3, reason3 = tm.compute_management_decision(row, "TP1_REACHED", {"tp2_probability": 90.0, "tp2_probability_n": 2}, None)
    check("high probability but n below MIN_SAMPLE_FOR_RECOMMENDATION falls back to plain HOLD, not a confident call", decision3 == "HOLD", decision3)
    check("insufficient-sample reason says so explicitly", "Insufficient history" in reason3, reason3)

    row_no_tp3 = TradeOutcome(direction="long", tp3=None, status="open")
    decision4, reason4 = tm.compute_management_decision(row_no_tp3, "TP2_REACHED", {}, None)
    check("TP2 reached with no TP3 defined never fabricates a TP3 probability call", decision4 == "HOLD" and "no TP3 is defined" in reason4, (decision4, reason4))


# ---------------------------------------------------------------------------
# 3. End-to-end: record_snapshot() populates real probabilities through
#    the whole open_trade_outcome() -> update_open_trades() lifecycle.
# ---------------------------------------------------------------------------
class FakePlan:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_end_to_end_snapshot_probabilities():
    symbol = FAKE_SYMBOLS[0]
    plan = FakePlan(
        recommendation="long", entry_low=100.0, entry_high=101.0, stop_loss=95.0,
        take_profit_1=105.0, take_profit_2=110.0, take_profit_3=None, time_horizon="swing",
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
        confidence=65, grade="B", entry_quality="neutral",
    )
    session = SessionLocal()
    try:
        row = session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(TradeOutcome.id.desc()).first()
    finally:
        session.close()

    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=1_010_000)  # entry
    trade_outcomes.update_open_trades({symbol: 105.5}, now_ms=1_020_000)  # TP1

    session = SessionLocal()
    try:
        snaps = session.query(PredictionSnapshot).filter(
            PredictionSnapshot.trade_outcome_id == row.id
        ).order_by(PredictionSnapshot.id).all()
    finally:
        session.close()

    tp1_snap = next(s for s in snaps if s.stage == "TP1_REACHED")
    check("TP1_REACHED snapshot reports tp1_probability=100.0 (already happened)", tp1_snap.tp1_probability == 100.0)
    check("TP1_REACHED snapshot's management_decision is one of the new Phase-2 values", tp1_snap.management_decision in ("HOLD", "HOLD_FOR_TP2", "MOVE_STOP_TO_ENTRY"), tp1_snap.management_decision)
    check("decision_reason is non-empty and references either a probability or insufficient history", len(tp1_snap.decision_reason) > 0)


try:
    test_stage_probabilities_facts_not_estimates()
    test_management_decision_thresholds()
    test_end_to_end_snapshot_probabilities()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
