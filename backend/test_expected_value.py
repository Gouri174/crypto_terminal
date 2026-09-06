"""Manual verification script for Karma V2.1 Phase 1 — Expected Value
engine (app/engine/expected_value.py) and its wiring into
trade_outcomes.py:open_trade_outcome().

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_expected_value.py`. Runs against the real dev DB using
clearly-fake symbols (ZZZEVA*) and cleans up after itself, including on
failure.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import expected_value as ev
from app.engine import trade_outcomes
from app.models.db_models import TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZEVAAUSDT"]
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
# 1. historical_tp_probabilities() backoff behavior — pure computation
#    against the real DB (whatever conditioning currently has enough
#    history is exercised naturally; this checks the MECHANISM, not a
#    fixed expected number, since the DB keeps growing).
# ---------------------------------------------------------------------------
def test_backoff_mechanism():
    # A conditioning combination that (almost certainly) has zero matching
    # rows forces a backoff all the way to "unconditioned".
    result = ev.historical_tp_probabilities(direction="long", entry_quality="exhausted", market_regime="risk_off")
    check(
        "impossible conditioning (entry_quality=exhausted can never have a TradeOutcome row) backs off to a coarser slice",
        result["tp1_probability"]["conditioning_used"] != "direction+entry_quality+regime",
        result["tp1_probability"],
    )
    check("tp1_probability always reports its own sample size", "n" in result["tp1_probability"])
    check("stop_before_tp1_probability always reports a 95% CI tuple", isinstance(result["stop_before_tp1_probability"]["ci_95"], tuple))


# ---------------------------------------------------------------------------
# 2. compute_expected_value() arithmetic — hand-computable inputs
# ---------------------------------------------------------------------------
def test_expected_value_arithmetic():
    # Force a specific, hand-checkable probability set by monkeypatching
    # historical_tp_probabilities via direct math verification instead:
    # risk=5%, reward_to_tp1=10% -> R multiple to TP1 = 2.0R.
    # Whatever real P(TP1)/P(stop) the live DB currently has, expected_r
    # must equal p_tp1*2.0 - p_stop*1.0 exactly.
    rr = {"risk_to_sl_pct": 5.0, "reward_to_tp1_pct": 10.0}
    result = ev.compute_expected_value(rr, direction="long")
    probs = ev.historical_tp_probabilities(direction="long")
    p_tp1 = probs["tp1_probability"]["probability_pct"]
    p_stop = probs["stop_before_tp1_probability"]["probability_pct"]
    if p_tp1 is not None and p_stop is not None:
        expected = round((p_tp1 / 100 * 2.0) - (p_stop / 100 * 1.0), 3)
        check("expected_r arithmetic matches p_tp1*2.0 - p_stop*1.0 exactly", result["expected_r"] == expected, (result["expected_r"], expected))
    check("expected_reward_pct passes through reward_to_tp1_pct unchanged", result["expected_reward_pct"] == 10.0)
    check("expected_risk_pct passes through risk_to_sl_pct unchanged", result["expected_risk_pct"] == 5.0)
    check("sample_size and conditioning_used are both reported", result["sample_size"] is not None and result["conditioning_used"] is not None)

    # Missing risk/reward data -> expected_r must be None, never guessed.
    result_missing = ev.compute_expected_value({}, direction="long")
    check("expected_r is None (not fabricated) when risk_reward has no risk_to_sl_pct", result_missing["expected_r"] is None)


# ---------------------------------------------------------------------------
# 3. End-to-end: open_trade_outcome() attaches expected_value additively
# ---------------------------------------------------------------------------
class FakePlan:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_expected_value_attached_on_open():
    symbol = FAKE_SYMBOLS[0]
    plan = FakePlan(
        recommendation="long", entry_low=100.0, entry_high=101.0, stop_loss=95.0,
        take_profit_1=110.0, take_profit_2=120.0, take_profit_3=None, time_horizon="swing",
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
        row = session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(
            TradeOutcome.id.desc()
        ).first()
    finally:
        session.close()

    check("expected_value is populated (not None) on a newly-opened trade", row.expected_value is not None)
    check("expected_value carries the probability keys", {
        "expected_r", "tp1_probability_pct", "tp2_given_tp1_probability_pct",
        "tp3_given_tp2_probability_pct", "stop_before_tp1_probability_pct", "sample_size",
    }.issubset(row.expected_value.keys()), row.expected_value.keys())
    check("score/confidence/grade are unchanged by adding expected_value (additive, not a replacement)", row.score == 65.0 and row.confidence == 65 and row.grade == "B")


try:
    test_backoff_mechanism()
    test_expected_value_arithmetic()
    test_expected_value_attached_on_open()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
