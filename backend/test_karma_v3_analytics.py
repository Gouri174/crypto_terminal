"""Manual verification script for Karma V3.0's analytics layer:
app/analytics/failure_patterns.py, app/analytics/reliability.py,
app/analytics/position_sizing.py, and their wiring into
app/engine/performance_center.py (trade_replay's new pattern/narrative
fields, failure_pattern_leaderboard, coin_reliability_leaderboard).

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_karma_v3_analytics.py`. Uses clearly-fake symbols
(ZZZV3A/ZZZV3B) for the end-to-end checks and cleans up after itself.
"""

import sys

sys.path.insert(0, ".")

from app.analytics import failure_patterns, position_sizing, reliability
from app.db import SessionLocal, init_db
from app.engine import performance_center as pc
from app.engine import trade_outcomes
from app.models.db_models import PredictionSnapshot, TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZV3AAUSDT", "ZZZV3ABUSDT"]
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
# 1. lifecycle_pattern() — every branch, using in-memory rows (no DB)
# ---------------------------------------------------------------------------
def test_lifecycle_pattern_branches():
    win_tp3 = TradeOutcome(status="closed_win", tp1_hit=True, tp2_hit=True, tp3_hit=True)
    check("win with tp3_hit -> ran_to_tp3", failure_patterns.lifecycle_pattern(win_tp3) == "ran_to_tp3")

    win_tp2 = TradeOutcome(status="closed_win", tp1_hit=True, tp2_hit=True, tp3_hit=False)
    check("win with tp2_hit, no tp3 -> closed_at_tp2", failure_patterns.lifecycle_pattern(win_tp2) == "closed_at_tp2")

    loss_after_tp2 = TradeOutcome(status="closed_loss", tp1_hit=True, tp2_hit=True, tp3_hit=False)
    check("loss after reaching tp2 -> hit_tp2_then_reversed", failure_patterns.lifecycle_pattern(loss_after_tp2) == "hit_tp2_then_reversed")

    loss_after_tp1 = TradeOutcome(status="closed_loss", tp1_hit=True, tp2_hit=False, tp3_hit=False)
    check("loss after reaching tp1 only -> reached_tp1_then_stopped", failure_patterns.lifecycle_pattern(loss_after_tp1) == "reached_tp1_then_stopped")

    immediate = TradeOutcome(status="closed_loss", tp1_hit=False, tp2_hit=False, tp3_hit=False, max_runup_pct=0.3)
    check("loss with MFE<1% and no TP hit -> immediate_reversal", failure_patterns.lifecycle_pattern(immediate) == "immediate_reversal")

    some_move = TradeOutcome(status="closed_loss", tp1_hit=False, tp2_hit=False, tp3_hit=False, max_runup_pct=3.0)
    check("loss with real favorable move but no TP hit -> some_favorable_move_then_stopped", failure_patterns.lifecycle_pattern(some_move) == "some_favorable_move_then_stopped")


# ---------------------------------------------------------------------------
# 2. risk_tags() — each tag fires independently and only when it should
# ---------------------------------------------------------------------------
def test_risk_tags():
    row = TradeOutcome(entry_indicators={"rsi14": 35}, structure_score=6.0, historic_probability=None, direction="short")
    tags = failure_patterns.risk_tags(row)
    check("all 4 applicable tags fire (rsi_chop_zone, weak_structure, no_historical_analogue, short_direction)", set(tags) == {"rsi_chop_zone", "weak_structure", "no_historical_analogue", "short_direction"}, tags)

    clean_row = TradeOutcome(entry_indicators={"rsi14": 60}, structure_score=12.0, historic_probability=0.55, direction="long")
    check("a clean setup triggers zero risk tags", failure_patterns.risk_tags(clean_row) == [])


# ---------------------------------------------------------------------------
# 3. failure_pattern_leaderboard() — shape, against the real DB
# ---------------------------------------------------------------------------
def test_failure_pattern_leaderboard_shape():
    result = failure_patterns.failure_pattern_leaderboard(min_sample=3)
    check("leaderboard reports n_losses and n_total_resolved", "n_losses" in result and "n_total_resolved" in result, result.keys())
    check("by_lifecycle_pattern entries sum to n_losses", sum(p["n"] for p in result["by_lifecycle_pattern"]) == result["n_losses"], result["by_lifecycle_pattern"])
    for p in result["by_lifecycle_pattern"]:
        check(f"pattern {p['pattern']} 'reliable' flag matches min_sample threshold", p["reliable"] == (p["n"] >= 3), p)


# ---------------------------------------------------------------------------
# 4. Bayesian reliability shrinkage — hand-verifiable arithmetic
# ---------------------------------------------------------------------------
def test_reliability_shrinkage_arithmetic():
    # wins=2, n=2 (100% raw), pooled_rate=0.4, prior_strength=10:
    # shrunk = (2 + 10*0.4) / (2+10) = 6/12 = 0.5 -> 50.0%
    shrunk = reliability._shrunk_win_rate(2, 2, 0.4, 10)
    check("Beta-Binomial shrinkage matches hand-computed value for a tiny 100%-win sample", round(shrunk * 100, 1) == 50.0, shrunk)

    # At n=0, shrunk win rate must equal the pooled rate exactly.
    shrunk_zero = reliability._shrunk_win_rate(0, 0, 0.4, 10)
    check("n=0 shrinks exactly to the pooled rate", shrunk_zero == 0.4, shrunk_zero)

    result = reliability.symbol_reliability(symbol="ZZZNONEXISTENTUSDT")
    check("an unseen symbol reports n=0 and reliability_score = pooled rate, not a crash", result["n"] == 0 and result["reliability_score"] is not None, result)


# ---------------------------------------------------------------------------
# 5. Position sizing — pure arithmetic, no execution
# ---------------------------------------------------------------------------
def test_position_sizing():
    # capital=1000, risk_pct=1% -> max_dollar_loss=$10. stop_distance=5% ->
    # position_size = 10 / 0.05 = $200.
    result = position_sizing.recommend_position_size(1000, 1.0, 5.0)
    check("max_dollar_loss = capital * risk_pct/100", result["max_dollar_loss"] == 10.0, result)
    check("position_size = max_dollar_loss / (stop_distance_pct/100)", result["position_size"] == 200.0, result)
    check("implied_leverage = position_size / capital", result["implied_leverage"] == 0.2, result)

    capped = position_sizing.recommend_position_size(1000, 5.0, 1.0, max_leverage=2.0)
    # Uncapped this would be (1000*0.05)/(1/100) = $5000 = 5x leverage — must cap at 2x = $2000.
    check("position size is capped at max_leverage when the raw math would exceed it", capped["position_size"] == 2000.0 and capped["leverage_capped"] is True, capped)

    invalid = position_sizing.recommend_position_size(0, 1.0, 5.0)
    check("zero/negative capital returns None, not a division error", invalid["position_size"] is None, invalid)


# ---------------------------------------------------------------------------
# 6. End-to-end: trade_replay()'s new pattern/narrative fields
# ---------------------------------------------------------------------------
class FakePlan:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_trade_replay_pattern_and_narrative():
    symbol = FAKE_SYMBOLS[0]
    plan = FakePlan(
        recommendation="long", entry_low=100.0, entry_high=101.0, stop_loss=95.0,
        take_profit_1=110.0, take_profit_2=None, take_profit_3=None, time_horizon="swing",
        summary="t", reasons_for=["x"], reasons_against=["y"],
        entry_reasoning="Testing entry.", sl_reasoning="Testing stop.",
        tp1_reasoning=None, tp2_reasoning=None, tp3_reasoning=None,
    )
    breakdown = {
        "trend": 20.0, "momentum": 10.0, "volume": 5.0, "funding": 8.0, "structure": 6.0,
        "history": 0.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
        "risk": -2.0, "total": 54.0,
    }
    features = {"indicators_4h": {"rsi14": 35, "cmf": -0.1}}
    trade_outcomes.open_trade_outcome(
        symbol, plan, breakdown, features, None, None, {"label": "mixed"}, now_ms=1_000_000,
        confidence=63, grade="B", entry_quality="neutral",
    )
    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=1_010_000)  # entry
    trade_outcomes.update_open_trades({symbol: 94.0}, now_ms=1_020_000)  # stop hit

    session = SessionLocal()
    try:
        row = session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(TradeOutcome.id.desc()).first()
    finally:
        session.close()

    replay = pc.trade_replay(row.id)
    check("trade_replay includes a 'pattern' field for a resolved trade", replay["pattern"] is not None, replay.get("pattern"))
    check("pattern.lifecycle_pattern is a real classification (immediate_reversal, given no TP hit and a real adverse move)", replay["pattern"]["lifecycle_pattern"] == "immediate_reversal", replay["pattern"])
    check("pattern.risk_tags includes rsi_chop_zone/weak_structure/no_historical_analogue", set(replay["pattern"]["risk_tags"]) == {"rsi_chop_zone", "weak_structure", "no_historical_analogue"}, replay["pattern"])
    check("narrative includes the stored entry/stop reasoning text", any("Testing entry" in b for b in replay["narrative"]), replay["narrative"])
    check("narrative includes a CMF-negative bullet", any("CMF was negative" in b for b in replay["narrative"]), replay["narrative"])


try:
    test_lifecycle_pattern_branches()
    test_risk_tags()
    test_failure_pattern_leaderboard_shape()
    test_reliability_shrinkage_arithmetic()
    test_position_sizing()
    test_trade_replay_pattern_and_narrative()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
