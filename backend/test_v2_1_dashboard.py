"""Manual verification script for Karma V2.1 Phase 7 dashboard additions
(app/engine/performance_center.py:ev_leaderboard/red_flag_leaderboard and
their routes in app/routes/performance.py).

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_v2_1_dashboard.py`. Runs against the real dev DB using
clearly-fake symbols (ZZZDASH*) and cleans up after itself.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import performance_center as pc
from app.engine import trade_outcomes
from app.models.db_models import PredictionSnapshot, TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZDASHAUSDT", "ZZZDASHBUSDT"]
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


def open_and_resolve(symbol, rsi, direction, confidence, final_price, status_target):
    plan = FakePlan(
        recommendation=direction, entry_low=100.0, entry_high=101.0,
        stop_loss=95.0 if direction == "long" else 105.0,
        take_profit_1=110.0 if direction == "long" else 90.0,
        take_profit_2=None, take_profit_3=None, time_horizon="swing",
        summary="t", reasons_for=["x"], reasons_against=["y"],
        entry_reasoning=None, sl_reasoning=None, tp1_reasoning=None, tp2_reasoning=None, tp3_reasoning=None,
    )
    breakdown = {
        "trend": 20.0, "momentum": 10.0, "volume": 5.0, "funding": 8.0, "structure": 6.0,
        "history": 0.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
        "risk": -2.0, "total": 54.0,
    }
    features = {"indicators_4h": {"rsi14": rsi}}
    trade_outcomes.open_trade_outcome(
        symbol, plan, breakdown, features, None, None, {"label": "mixed"}, now_ms=1_000_000,
        confidence=confidence, grade="B", entry_quality="neutral",
    )
    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=1_010_000)  # entry
    trade_outcomes.update_open_trades({symbol: final_price}, now_ms=1_020_000)  # resolve


def test_ev_and_red_flag_leaderboards():
    # A chop-zone (RSI 35) long that wins -- triggers rsi_chop_zone + weak
    # structure + no history (structure=6 < 9) = 3 red flags.
    open_and_resolve(FAKE_SYMBOLS[0], rsi=35, direction="long", confidence=63, final_price=110.5, status_target="closed_win")
    # A healthy-RSI (60) short that loses -- 0 red flags on RSI/structure (structure=6 still <9 so 2 flags: weak_structure + no_history).
    open_and_resolve(FAKE_SYMBOLS[1], rsi=60, direction="long", confidence=63, final_price=94.5, status_target="closed_loss")

    ev = pc.ev_leaderboard(min_sample=1)
    check("ev_leaderboard picks up both newly-opened trades", ev["n"] == 2, ev)
    check("ranked_by_expected_r is sorted descending by expected_r", ev["ranked_by_expected_r"][0]["expected_r"] >= ev["ranked_by_expected_r"][-1]["expected_r"], ev["ranked_by_expected_r"])
    check("each entry reports its realized_r alongside expected_r", all("realized_r" in e for e in ev["ranked_by_expected_r"]))

    rf = pc.red_flag_leaderboard()
    check("red_flag_leaderboard picks up both newly-opened trades", rf["n"] == 2, rf)
    check("bucket for red_flag_score=3 exists (the chop-zone trade)", 3 in rf["by_red_flag_score"], rf["by_red_flag_score"])


try:
    test_ev_and_red_flag_leaderboards()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
