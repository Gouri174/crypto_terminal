"""Manual verification script for Karma V3.1 synthesis features:
Trade Quality Score, reliability-adjusted confidence display, Karma
Explain, Decision Audit, Strategy Attribution, and Trade Manager's new
conditional_triggers(). All read-only synthesis over already-existing
modules — no scoring/decision/regime/ML changes (30-day freeze honored).

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_karma_v3_1_synthesis.py`. Uses a clearly-fake symbol
(ZZZV31AUSDT) for the end-to-end checks and cleans up after itself.
"""

import sys

sys.path.insert(0, ".")

from app.analytics import decision_audit, karma_explain, strategy_attribution, trade_quality
from app.db import SessionLocal, init_db
from app.engine import calibration, trade_manager, trade_outcomes
from app.models.db_models import PredictionSnapshot, TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZV31AUSDT"]
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
# 1. Trade Quality Score — formula arithmetic, hand-computable
# ---------------------------------------------------------------------------
def test_trade_quality_formula():
    # entry_quality=excellent(100) EV=+3.0R(100) reliability=80 calibration=70
    # structure=15/15(100) red_flag_score=0(100):
    # 0.30*100 + 0.20*100 + 0.15*80 + 0.15*70 + 0.10*100 + 0.10*100
    # = 30 + 20 + 12 + 10.5 + 10 + 10 = 92.5
    result = trade_quality.compute_trade_quality(
        entry_quality="excellent", expected_r=3.0, reliability_score=80.0,
        calibrated_confidence=70.0, structure_score=15.0, red_flag_score=0,
    )
    check("trade_quality matches hand-computed 92.5 for a maxed-out setup", result["trade_quality"] == 92.5, result)
    check("grade A+ at 92.5 (>=85 band)", result["grade"] == "A+", result["grade"])

    # Missing inputs default to neutral 50, not a crash or a zero.
    result_missing = trade_quality.compute_trade_quality(
        entry_quality=None, expected_r=None, reliability_score=None,
        calibrated_confidence=None, structure_score=None, red_flag_score=None,
    )
    check("all-missing inputs produce exactly 50.0 (every component defaults to neutral)", result_missing["trade_quality"] == 50.0, result_missing)

    # Worst-case setup.
    worst = trade_quality.compute_trade_quality(
        entry_quality="exhausted", expected_r=-1.0, reliability_score=0.0,
        calibrated_confidence=0.0, structure_score=0.0, red_flag_score=3,
    )
    check("a worst-case setup scores 0.0", worst["trade_quality"] == 0.0, worst)
    check("grade D at 0.0", worst["grade"] == "D", worst["grade"])


# ---------------------------------------------------------------------------
# 2. Reliability-adjusted confidence display — uncertainty derived from CI
# ---------------------------------------------------------------------------
def test_confidence_display():
    result = calibration.confidence_display(200)  # out of calibrated range
    check("out-of-range confidence returns None uncertainty (nothing fabricated)", result["uncertainty_pm_pct_points"] is None, result)
    check("out-of-range confidence still reports raw_confidence unchanged", result["raw_confidence"] == 200, result)

    result_real = calibration.confidence_display(62)
    check("confidence_display always reports a sample_size", "sample_size" in result_real, result_real)
    if result_real["sample_size"] >= calibration.MIN_SAMPLE:
        check("above-min-sample bucket reports a numeric uncertainty half-width", result_real["uncertainty_pm_pct_points"] is not None, result_real)


# ---------------------------------------------------------------------------
# 3. Decision Audit — reuses decision.py's UNMODIFIED market_checklist()
# ---------------------------------------------------------------------------
def test_decision_audit():
    row = TradeOutcome(
        trend_score=20.0, momentum_score=10.0, volume_score=6.0, funding_score=8.0,
        structure_score=10.0, history_score=0.0, regime_score=3.0, ml_score=0.0,
        sentiment_score=0.0, liquidity_score=0.0, risk_score=-2.0, score=55.0,
        historic_probability=None, entry_indicators={"rsi14": 35}, direction="long",
    )
    audit = decision_audit.audit_trade(row)
    check("trend_pass in accepted_because (trend_score=20>=15)", "trend_pass" in audit["accepted_because"], audit)
    check("history_pass in rejected_checks (no historic_probability)", "history_pass" in audit["rejected_checks"], audit)
    check("rsi_chop_zone warning fires (rsi=35 is in the 30-49 chop zone)", "rsi_chop_zone" in audit["warnings"], audit)
    check("checklist is the exact dict decision.market_checklist() returns (7 keys)", len(audit["checklist"]) == 7, audit["checklist"])

    leaderboard = decision_audit.decision_audit_leaderboard(min_sample=3)
    check("leaderboard reports n_resolved and by_accepted_condition", "n_resolved" in leaderboard and "by_accepted_condition" in leaderboard, leaderboard.keys())


# ---------------------------------------------------------------------------
# 4. Strategy Attribution — each rule fires on its intended input
# ---------------------------------------------------------------------------
def test_strategy_attribution():
    fvg_row = TradeOutcome(level_reasoning={"fvg_used": {"direction": "up"}}, entry_indicators={}, direction="long")
    check("an active FVG at entry -> fvg_continuation", strategy_attribution.classify_strategy(fvg_row) == "fvg_continuation")

    late_row = TradeOutcome(entry_quality="late", entry_indicators={}, level_reasoning=None, direction="long")
    check("entry_quality=late -> breakout_chase", strategy_attribution.classify_strategy(late_row) == "breakout_chase")

    oversold_row = TradeOutcome(entry_indicators={"rsi14": 25}, level_reasoning=None, direction="long", entry_quality="neutral")
    check("oversold RSI on a long -> mean_reversion", strategy_attribution.classify_strategy(oversold_row) == "mean_reversion")

    ema_row = TradeOutcome(entry_indicators={"distance_to_ema20_pct": 0.5}, level_reasoning=None, direction="long", entry_quality="neutral")
    check("price close to EMA20 -> ema_pullback", strategy_attribution.classify_strategy(ema_row) == "ema_pullback")

    fallback_row = TradeOutcome(entry_indicators={}, level_reasoning=None, direction="long", entry_quality="neutral", structure_score=4.0)
    check("nothing else matches, weak structure -> trend_continuation_other (not a false BOS claim)", strategy_attribution.classify_strategy(fallback_row) == "trend_continuation_other", strategy_attribution.classify_strategy(fallback_row))


# ---------------------------------------------------------------------------
# 5. Trade Manager conditional_triggers() — level-based only, never
#    fabricates an indicator-conditioned trigger this app can't verify.
# ---------------------------------------------------------------------------
def test_conditional_triggers():
    row = TradeOutcome(tp1=110.0, tp2=120.0, tp3=None, entry=100.0)
    triggers_open = trade_manager.conditional_triggers(row, "OPEN")
    check("OPEN stage mentions the TP1 level", any("110" in t for t in triggers_open), triggers_open)

    triggers_tp1 = trade_manager.conditional_triggers(row, "TP1_REACHED")
    check("TP1_REACHED stage mentions the TP2 level", any("120" in t for t in triggers_tp1), triggers_tp1)
    check("no trigger ever mentions CMF (unverifiable — no live indicator snapshot exists)", not any("CMF" in t for t in triggers_open + triggers_tp1))


# ---------------------------------------------------------------------------
# 6. End-to-end: Karma Explain on a real (fake-symbol) trade
# ---------------------------------------------------------------------------
class FakePlan:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_karma_explain_end_to_end():
    symbol = FAKE_SYMBOLS[0]
    plan = FakePlan(
        recommendation="long", entry_low=100.0, entry_high=101.0, stop_loss=95.0,
        take_profit_1=110.0, take_profit_2=120.0, take_profit_3=None, time_horizon="swing",
        summary="Test summary.", reasons_for=["x"], reasons_against=["y"],
        entry_reasoning=None, sl_reasoning=None, tp1_reasoning=None, tp2_reasoning=None, tp3_reasoning=None,
    )
    breakdown = {
        "trend": 20.0, "momentum": 10.0, "volume": 5.0, "funding": 8.0, "structure": 12.0,
        "history": 0.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
        "risk": -2.0, "total": 60.0,
    }
    trade_outcomes.open_trade_outcome(
        symbol, plan, breakdown, {}, None, None, {"label": "mixed"}, now_ms=1_000_000,
        confidence=63, grade="B", entry_quality="excellent",
    )
    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=1_010_000)  # entry
    trade_outcomes.update_open_trades({symbol: 110.5}, now_ms=1_020_000)  # TP1

    session = SessionLocal()
    try:
        row = session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(TradeOutcome.id.desc()).first()
    finally:
        session.close()

    explanation = karma_explain.explain_trade(row.id)
    check("explain_trade returns a payload for a real trade", explanation is not None)
    check("bullish_evidence_count reports a fraction (e.g. '5/7')", "/" in explanation["bullish_evidence_count"], explanation["bullish_evidence_count"])
    check("action_plan present for an open trade at TP1", explanation["action_plan"] is not None and explanation["action_plan"]["stage"] == "TP1_REACHED", explanation["action_plan"])
    check("action_plan includes conditional_triggers", "conditional_triggers" in explanation["action_plan"], explanation["action_plan"])
    check("historical_context (pattern_similarity) is present", "matched_tags" in explanation["historical_context"] or "note" in explanation["historical_context"], explanation["historical_context"])
    check("explain_trade returns None for a nonexistent id", karma_explain.explain_trade(-999999) is None)

    tq = trade_quality.trade_quality_for_row(row)
    check("trade_quality_for_row returns a 0-100 score for the real row", 0 <= tq["trade_quality"] <= 100, tq)


try:
    test_trade_quality_formula()
    test_confidence_display()
    test_decision_audit()
    test_strategy_attribution()
    test_conditional_triggers()
    test_karma_explain_end_to_end()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
