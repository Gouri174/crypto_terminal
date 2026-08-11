"""Manual verification script for the V1.1 data-collection pass.

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_v11_data_collection.py`. Runs against the real dev DB using
clearly-fake symbols (ZZZV11*) and cleans up after itself, including on
failure.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import entry_flags, trade_outcomes
from app.models.db_models import PredictionSnapshot, TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZV11AUSDT", "ZZZV11BUSDT", "ZZZV11CUSDT", "ZZZV11DUSDT"]
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


def make_plan(symbol, direction="long", entry_low=100.0, entry_high=101.0, stop_loss=97.0,
              tp1=105.0, tp2=110.0, tp3=None, time_horizon="swing"):
    return FakePlan(
        recommendation=direction, entry_low=entry_low, entry_high=entry_high,
        stop_loss=stop_loss, take_profit_1=tp1, take_profit_2=tp2, take_profit_3=tp3,
        time_horizon=time_horizon, summary="v1.1 test plan",
        reasons_for=["test reason for"], reasons_against=["test reason against"],
    )


BREAKDOWN_STRONG = {
    "trend": 20.0, "momentum": 14.0, "volume": 5.0, "funding": 8.0, "structure": 4.0,
    "history": 5.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
    "risk": -2.0, "total": 65.0,
}
FEATURES_FULL = {
    "indicators_4h": {
        "last_close": 100.0, "ema20": 98.0, "ema50": 95.0, "ema200": 90.0, "atr14": 1.0,
        "rsi14": 55.0, "stoch_rsi": 0.5, "adx14": 25.0, "macd_hist": 0.3, "cmf": 0.1, "mfi": 50.0, "bb_pct": 0.6,
    },
    "fear_greed": {"value": 35},
    "news_context": {"headlines": [], "reddit_mention_count": 0, "reddit_sample_titles": []},
}
REGIME_FULL = {
    "label": "risk_on", "trend": "bullish", "btc_trend": "bull",
    "breadth_bullish_pct": 62.5, "breadth_bearish_pct": 37.5, "universe_size": 40,
}


def get_row(symbol):
    session = SessionLocal()
    try:
        return session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(
            TradeOutcome.id.desc()
        ).first()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. Safety fix: Avoid-grade trade is NOT tracked as pending.
# ---------------------------------------------------------------------------
def test_avoid_grade_not_pending():
    symbol = FAKE_SYMBOLS[0]
    plan = make_plan(symbol)
    trade_outcomes.open_trade_outcome(
        symbol, plan, BREAKDOWN_STRONG, FEATURES_FULL, None, None, REGIME_FULL,
        now_ms=2_000_000, confidence=40, grade="Avoid",
    )
    row = get_row(symbol)
    check("Avoid-grade trade gets status=rejected_avoid, not pending", row.status == "rejected_avoid", row.status)

    # A rejected_avoid row must be invisible to update_open_trades — it
    # should never transition, never get a PredictionSnapshot.
    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=2_060_000)
    row2 = get_row(symbol)
    check("rejected_avoid row untouched by update_open_trades", row2.status == "rejected_avoid", row2.status)

    session = SessionLocal()
    try:
        snap_count = session.query(PredictionSnapshot).filter(PredictionSnapshot.trade_outcome_id == row.id).count()
    finally:
        session.close()
    check("rejected_avoid row never gets a PredictionSnapshot", snap_count == 0, snap_count)


# ---------------------------------------------------------------------------
# 2. A real (non-Avoid) trade still tracks normally as "pending".
# ---------------------------------------------------------------------------
def test_normal_grade_still_pending():
    symbol = FAKE_SYMBOLS[1]
    plan = make_plan(symbol)
    trade_outcomes.open_trade_outcome(
        symbol, plan, BREAKDOWN_STRONG, FEATURES_FULL, None, None, REGIME_FULL,
        now_ms=2_000_000, confidence=70, grade="B+",
    )
    row = get_row(symbol)
    check("B+-grade trade still gets status=pending", row.status == "pending", row.status)


# ---------------------------------------------------------------------------
# 3. Full entry-state capture: new entry_indicators fields.
# ---------------------------------------------------------------------------
def test_full_entry_state_captured():
    row = get_row(FAKE_SYMBOLS[1])
    ind = row.entry_indicators
    check("macd_hist captured", ind.get("macd_hist") == 0.3, ind)
    check("cmf captured", ind.get("cmf") == 0.1, ind)
    check("mfi captured", ind.get("mfi") == 50.0, ind)
    check("bb_pct captured", ind.get("bb_pct") == 0.6, ind)
    check("btc_trend captured from regime", ind.get("btc_trend") == "bull", ind)
    check("breadth_bullish_pct captured from regime", ind.get("breadth_bullish_pct") == 62.5, ind)
    check("market_cluster classified", ind.get("market_cluster") == "Altcoin", ind)
    check("risk_reward computed", ind.get("risk_reward", {}).get("rr_tp1") is not None, ind.get("risk_reward"))
    check("same_window_signal_count present", isinstance(ind.get("same_window_signal_count"), int), ind)


# ---------------------------------------------------------------------------
# 4. Diagnostic flags — a known scenario should trip specific flags.
# ---------------------------------------------------------------------------
def test_diagnostic_flags():
    row = get_row(FAKE_SYMBOLS[1])
    flags = row.diagnostic_flags
    # BREAKDOWN_STRONG: momentum=14 (>=12), structure=4 (<8) -> HIGH_MOMENTUM_WEAK_STRUCTURE
    check("HIGH_MOMENTUM_WEAK_STRUCTURE flagged", "HIGH_MOMENTUM_WEAK_STRUCTURE" in flags, flags)
    # total=65 (>=60), structure=4 (<8) -> HIGH_SCORE_WEAK_STRUCTURE
    check("HIGH_SCORE_WEAK_STRUCTURE flagged", "HIGH_SCORE_WEAK_STRUCTURE" in flags, flags)
    # no history_stats, no ml_prediction passed -> NO_HISTORY, NO_ML
    check("NO_HISTORY flagged", "NO_HISTORY" in flags, flags)
    check("NO_ML flagged", "NO_ML" in flags, flags)
    # tp1=105 vs entry~100.5, stop=97 -> risk 3.5%, reward 4.5% -> rr_tp1 ~1.3, NOT low
    check("LOW_TP1_RR correctly NOT flagged for RR>1", "LOW_TP1_RR" not in flags, flags)


def test_low_tp1_rr_flag():
    symbol = FAKE_SYMBOLS[2]
    # Tight TP1 relative to stop distance -> RR < 1.
    plan = make_plan(symbol, entry_low=100.0, entry_high=100.0, stop_loss=90.0, tp1=102.0, tp2=110.0)
    trade_outcomes.open_trade_outcome(
        symbol, plan, BREAKDOWN_STRONG, FEATURES_FULL, None, None, REGIME_FULL,
        now_ms=2_100_000, confidence=70, grade="B+",
    )
    row = get_row(symbol)
    rr = row.entry_indicators["risk_reward"]
    check("RR_TP1 computed correctly (2% reward / 10% risk = 0.2)", abs(rr["rr_tp1"] - 0.2) < 0.01, rr)
    check("LOW_TP1_RR flagged when RR<1", "LOW_TP1_RR" in row.diagnostic_flags, row.diagnostic_flags)


# ---------------------------------------------------------------------------
# 5. exit_price / stop_slippage_pct captured at close.
# ---------------------------------------------------------------------------
def test_exit_price_and_slippage():
    symbol = FAKE_SYMBOLS[3]
    plan = make_plan(symbol, entry_low=100.0, entry_high=101.0, stop_loss=97.0, tp1=105.0, tp2=110.0)
    trade_outcomes.open_trade_outcome(
        symbol, plan, BREAKDOWN_STRONG, FEATURES_FULL, None, None, REGIME_FULL,
        now_ms=3_000_000, confidence=70, grade="B+",
    )
    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=3_060_000)  # triggers entry
    # Price gaps past the stop (simulating the scan-interval gap risk the
    # forensic report flagged) — scanner only ever observes 90.0, not the
    # true crossing point.
    trade_outcomes.update_open_trades({symbol: 90.0}, now_ms=3_120_000)

    row = get_row(symbol)
    check("status closed_loss", row.status == "closed_loss", row.status)
    check("exit_price recorded as the observed price (90.0)", row.exit_price == 90.0, row.exit_price)
    expected_slippage = round((90.0 - 97.0) / 97.0 * 100, 3)
    check("stop_slippage_pct computed correctly", row.stop_slippage_pct == expected_slippage, row.stop_slippage_pct)


# ---------------------------------------------------------------------------
# 6. Old rows remain untouched (new columns NULL, not backfilled).
# ---------------------------------------------------------------------------
def test_old_rows_untouched():
    session = SessionLocal()
    try:
        old_row = session.query(TradeOutcome).filter(TradeOutcome.symbol == "BEATUSDT").first()
    finally:
        session.close()
    if old_row is None:
        check("old-row check skipped (BEATUSDT not present in this DB)", True)
        return
    check("old row exit_price is NULL, not backfilled", old_row.exit_price is None, old_row.exit_price)
    check("old row diagnostic_flags is NULL, not backfilled", old_row.diagnostic_flags is None, old_row.diagnostic_flags)


# ---------------------------------------------------------------------------
# 7. No new Claude calls — structural check.
# ---------------------------------------------------------------------------
def test_no_new_claude_calls():
    import app.engine.entry_flags as ef
    import app.engine.forensic_diagnostics as fd

    check("entry_flags.py never imports anthropic", "anthropic" not in ef.__dict__)
    check("forensic_diagnostics.py never imports anthropic", "anthropic" not in fd.__dict__)


# ---------------------------------------------------------------------------
# 8. Risk/reward helper — pure arithmetic, no missing-value guessing.
# ---------------------------------------------------------------------------
def test_risk_reward_helper():
    rr = entry_flags.compute_risk_reward(100.0, 95.0, 110.0, 120.0, None)
    check("risk_to_sl_pct correct", abs(rr["risk_to_sl_pct"] - 5.0) < 0.01, rr)
    check("rr_tp1 correct (10% reward / 5% risk = 2.0)", abs(rr["rr_tp1"] - 2.0) < 0.01, rr)
    check("rr_tp3 is None when tp3 is None, not guessed", rr["rr_tp3"] is None, rr)

    rr_missing = entry_flags.compute_risk_reward(None, 95.0, 110.0, None, None)
    check("all-None when entry is missing", rr_missing["risk_to_sl_pct"] is None, rr_missing)


try:
    test_avoid_grade_not_pending()
    test_normal_grade_still_pending()
    test_full_entry_state_captured()
    test_diagnostic_flags()
    test_low_tp1_rr_flag()
    test_exit_price_and_slippage()
    test_old_rows_untouched()
    test_no_new_claude_calls()
    test_risk_reward_helper()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
