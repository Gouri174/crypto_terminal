"""Manual verification script for the multi-target Phase 1 data model.

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_multi_target_phase1.py`. Runs against the real dev DB using
clearly-fake symbols (ZZZMT*) and cleans up after itself, including on
failure.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import forensic_diagnostics as fd
from app.engine import trade_outcomes
from app.models.db_models import PredictionSnapshot, TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZMTAUSDT", "ZZZMTBUSDT"]
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


class FakePlan:
    def __init__(self, **kw):
        self.__dict__.update(kw)


BREAKDOWN = {
    "trend": 20.0, "momentum": 10.0, "volume": 5.0, "funding": 8.0, "structure": 12.0,
    "history": 5.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
    "risk": -2.0, "total": 65.0,
}


def get_row(symbol):
    session = SessionLocal()
    try:
        return session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(
            TradeOutcome.id.desc()
        ).first()
    finally:
        session.close()


def get_snapshots(trade_id):
    session = SessionLocal()
    try:
        return session.query(PredictionSnapshot).filter(
            PredictionSnapshot.trade_outcome_id == trade_id
        ).order_by(PredictionSnapshot.id).all()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. Full lifecycle: PRE_ENTRY -> OPEN -> TP1_REACHED -> TP2_REACHED -> EXITED,
#    with correct management_decision at every stage, no probability
#    fabricated (all NULL in Phase 1).
# ---------------------------------------------------------------------------
def test_full_stage_lifecycle():
    symbol = FAKE_SYMBOLS[0]
    plan = FakePlan(
        recommendation="long", entry_low=100.0, entry_high=101.0, stop_loss=97.0,
        take_profit_1=105.0, take_profit_2=110.0, take_profit_3=115.0, time_horizon="swing",
        summary="t", reasons_for=["x"], reasons_against=["y"],
    )
    trade_outcomes.open_trade_outcome(
        symbol, plan, BREAKDOWN, {}, None, None, {"label": "risk_on"}, now_ms=4_000_000,
        confidence=70, grade="B+",
    )
    row = get_row(symbol)

    # PRE_ENTRY
    trade_outcomes.update_open_trades({symbol: 90.0}, now_ms=4_010_000)  # outside zone, still pending
    snaps = get_snapshots(row.id)
    check("stage=PRE_ENTRY while pending", snaps[-1].stage == "PRE_ENTRY", snaps[-1].stage)
    check("management_decision=HOLD at PRE_ENTRY", snaps[-1].management_decision == "HOLD", snaps[-1].management_decision)
    check("tp1_probability NULL in Phase 1 (never fabricated)", snaps[-1].tp1_probability is None)

    # OPEN
    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=4_020_000)
    snaps = get_snapshots(row.id)
    check("stage=OPEN after entry triggers", snaps[-1].stage == "OPEN", snaps[-1].stage)
    check("decision_reason mentions Phase 2 not built", "Phase 2 not built" in snaps[-1].decision_reason, snaps[-1].decision_reason)

    # TP1_REACHED
    trade_outcomes.update_open_trades({symbol: 105.5}, now_ms=4_030_000)
    snaps = get_snapshots(row.id)
    check("stage=TP1_REACHED", snaps[-1].stage == "TP1_REACHED", snaps[-1].stage)
    check("mfe_pct reflects real favorable move", snaps[-1].mfe_pct is not None and snaps[-1].mfe_pct > 4.0, snaps[-1].mfe_pct)
    check("distance_to_tp3_pct populated", snaps[-1].distance_to_tp3_pct is not None, snaps[-1].distance_to_tp3_pct)

    # TP2_REACHED
    trade_outcomes.update_open_trades({symbol: 110.5}, now_ms=4_040_000)
    snaps = get_snapshots(row.id)
    check("stage=TP2_REACHED", snaps[-1].stage == "TP2_REACHED", snaps[-1].stage)

    # EXITED via TP3 (outermost target)
    trade_outcomes.update_open_trades({symbol: 115.5}, now_ms=4_050_000)
    snaps = get_snapshots(row.id)
    check("stage=EXITED after final target hit", snaps[-1].stage == "EXITED", snaps[-1].stage)
    check("management_decision=TAKE_PROFIT on win", snaps[-1].management_decision == "TAKE_PROFIT", snaps[-1].management_decision)

    row_final = get_row(symbol)
    check("status=closed_win", row_final.status == "closed_win", row_final.status)
    check("tp1_hit/tp2_hit/tp3_hit all True (existing fields, not duplicated)",
          row_final.tp1_hit and row_final.tp2_hit and row_final.tp3_hit)


# ---------------------------------------------------------------------------
# 2. STOPPED path.
# ---------------------------------------------------------------------------
def test_stopped_stage():
    symbol = FAKE_SYMBOLS[1]
    plan = FakePlan(
        recommendation="long", entry_low=100.0, entry_high=101.0, stop_loss=97.0,
        take_profit_1=105.0, take_profit_2=None, take_profit_3=None, time_horizon="swing",
        summary="t", reasons_for=["x"], reasons_against=["y"],
    )
    trade_outcomes.open_trade_outcome(
        symbol, plan, BREAKDOWN, {}, None, None, {"label": "risk_on"}, now_ms=5_000_000,
        confidence=60, grade="B",
    )
    row = get_row(symbol)
    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=5_010_000)
    trade_outcomes.update_open_trades({symbol: 95.0}, now_ms=5_020_000)  # stop hit

    snaps = get_snapshots(row.id)
    check("stage=EXITED on stop", snaps[-1].stage == "EXITED", snaps[-1].stage)
    check("management_decision=STOPPED", snaps[-1].management_decision == "STOPPED", snaps[-1].management_decision)
    check("mae_pct reflects real adverse move", snaps[-1].mae_pct is not None and snaps[-1].mae_pct < -4.0, snaps[-1].mae_pct)


# ---------------------------------------------------------------------------
# 3. Append-only: old snapshots never mutated once written.
# ---------------------------------------------------------------------------
def test_snapshots_append_only():
    row = get_row(FAKE_SYMBOLS[0])
    snaps = get_snapshots(row.id)
    check("5 distinct stages recorded, one per real event (append-only)", len(snaps) == 5, len(snaps))
    stages_seen = [s.stage for s in snaps]
    check("stages progressed in real order", stages_seen == ["PRE_ENTRY", "OPEN", "TP1_REACHED", "TP2_REACHED", "EXITED"], stages_seen)


# ---------------------------------------------------------------------------
# 4. Conditional probability report runs cleanly and gates small samples.
# ---------------------------------------------------------------------------
def test_conditional_probability_report_runs():
    result = fd.target_conditional_probabilities(min_sample=3)
    check("target_conditional_probabilities returns expected keys",
          set(["p_tp1", "p_tp2_given_tp1_reached", "p_tp3_given_tp2_reached"]).issubset(result.keys()), result.keys())
    check("p_tp1 has a sample size field", "n" in result["p_tp1"], result["p_tp1"])


try:
    test_full_stage_lifecycle()
    test_stopped_stage()
    test_snapshots_append_only()
    test_conditional_probability_report_runs()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
