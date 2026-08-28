"""Manual verification script for the Performance Center V1 analytics
module (app/engine/performance_center.py) and its API routes
(app/routes/performance.py).

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_performance_center.py`. Runs against the real dev DB using
clearly-fake symbols (ZZZPC*) and cleans up after itself, including on
failure.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import performance_center as pc
from app.models.db_models import PredictionSnapshot, TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZPCAUSDT", "ZZZPCBUSDT", "ZZZPCCUSDT", "ZZZPCDUSDT"]
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


BASE_TRADE_KWARGS = dict(
    exchange="binance", spot_or_futures="futures", timeframe="swing",
    score=60.0, trend_score=20.0, momentum_score=10.0, volume_score=5.0,
    funding_score=5.0, structure_score=10.0, history_score=0.0, regime_score=0.0,
    ml_score=0.0, sentiment_score=0.0, liquidity_score=0.0, risk_score=0.0,
    reasoning="test", reasons_for=[], reasons_against=[],
)


def make_trade(session, symbol, **overrides) -> TradeOutcome:
    kwargs = {**BASE_TRADE_KWARGS, "symbol": symbol}
    kwargs.update(overrides)
    row = TradeOutcome(**kwargs)
    session.add(row)
    session.flush()
    return row


def make_snapshot(session, trade_id, symbol, **overrides) -> PredictionSnapshot:
    kwargs = dict(
        trade_outcome_id=trade_id, symbol=symbol, current_price=0.0, current_pnl_pct=0.0,
        distance_to_stop_pct=0.0, status="open", reason="test",
    )
    kwargs.update(overrides)
    row = PredictionSnapshot(**kwargs)
    session.add(row)
    session.flush()
    return row


# ---------------------------------------------------------------------------
# 1. Scanner Health — gap detection
# ---------------------------------------------------------------------------
def test_scanner_health_gap_detection():
    session = SessionLocal()
    try:
        t = make_trade(
            session, FAKE_SYMBOLS[0], direction="long", status="open",
            created_at=1_000_000, entry_time=1_000_500, entry_low=100.0, entry_high=101.0,
            entry=100.5, stop_loss=95.0, tp1=110.0,
        )
        # Two snapshots 20 minutes apart — a real gap under a 10-minute threshold.
        make_snapshot(session, t.id, FAKE_SYMBOLS[0], timestamp=2_000_000, current_price=100.0)
        make_snapshot(session, t.id, FAKE_SYMBOLS[0], timestamp=2_000_000 + 20 * 60_000, current_price=101.0)
        session.commit()
    finally:
        session.close()

    result = pc.scanner_health(gap_threshold_minutes=10)
    outage = next((o for o in result["outages"] if o["start"] == 2_000_000), None)
    check("a 20-minute gap is detected as an outage under a 10-minute threshold", outage is not None, result["outages"])
    if outage:
        check("outage duration computed correctly (20 min)", outage["duration_minutes"] == 20.0, outage)
        check("the open trade spanning the gap is listed as affected", FAKE_SYMBOLS[0] in outage["affected_open_trades"], outage)


# ---------------------------------------------------------------------------
# 2. Stop Execution Audit — direction split, volatility bucket, outage flag
# ---------------------------------------------------------------------------
def test_stop_execution_audit():
    session = SessionLocal()
    try:
        # Long, small slippage, tight ATR-normalized stop (volatility bucket).
        make_trade(
            session, FAKE_SYMBOLS[1], direction="long", status="closed_loss", stop_hit=True,
            created_at=1_000_000, entry_time=1_000_500, entry_low=100.0, entry_high=101.0,
            entry=100.5, stop_loss=95.0, tp1=110.0, exit_time=3_000_000, exit_price=94.5,
            stop_slippage_pct=-0.526,
            entry_indicators={"risk_reward": {"entry_to_sl_atr": 0.5, "risk_to_sl_pct": 5.0}},
        )
        # Short, large slippage — deliberately placed inside a fabricated outage window.
        make_trade(
            session, FAKE_SYMBOLS[2], direction="short", status="closed_loss", stop_hit=True,
            created_at=1_000_000, entry_time=1_000_500, entry_low=100.0, entry_high=101.0,
            entry=100.5, stop_loss=105.0, tp1=90.0, exit_time=5_000_000, exit_price=130.0,
            stop_slippage_pct=-23.8,
            entry_indicators={"risk_reward": {"entry_to_sl_atr": 2.5, "risk_to_sl_pct": 4.5}},
        )
        session.commit()
    finally:
        session.close()

    result = pc.stop_execution_audit(outage_gap_threshold_minutes=10)
    check("overall slippage distribution includes both fake trades", result["overall"]["n"] >= 2, result["overall"])
    check("long slippage distribution present", result["by_direction"]["long"]["n"] >= 1)
    check("short slippage distribution present and worse than long", result["by_direction"]["short"]["mean"] < result["by_direction"]["long"]["mean"])
    check(
        "volatility bucket uses ATR-normalized distance when available (<1.0 ATR bucket exists)",
        "<1.0 ATR" in result["by_volatility_bucket"], result["by_volatility_bucket"].keys(),
    )


# ---------------------------------------------------------------------------
# 3. TP Continuation — the two sign-convention bugs, tested directly
# ---------------------------------------------------------------------------
def test_tp_continuation_sign_bugs():
    session = SessionLocal()
    try:
        # A LONG trade that hits TP1, then genuinely pulls back to entry
        # (real reversal) before eventually winning via TP2 — must read
        # returned_to_entry=True, not a false negative OR a false 100%.
        t1 = make_trade(
            session, FAKE_SYMBOLS[3], direction="long", status="closed_win",
            created_at=1_000_000, entry_time=1_000_500, entry_low=100.0, entry_high=101.0,
            entry=100.0, stop_loss=95.0, tp1=105.0, tp2=110.0,
            tp1_hit=True, tp1_hit_at=2_000_000, tp2_hit=True, exit_time=4_000_000,
        )
        make_snapshot(session, t1.id, FAKE_SYMBOLS[3], timestamp=1_500_000, current_price=102.0, status="open")
        make_snapshot(session, t1.id, FAKE_SYMBOLS[3], timestamp=2_000_000, current_price=105.5, status="open")
        # Genuine pullback all the way back to entry (100.0) while still open.
        make_snapshot(session, t1.id, FAKE_SYMBOLS[3], timestamp=2_500_000, current_price=99.5, status="open")
        make_snapshot(session, t1.id, FAKE_SYMBOLS[3], timestamp=3_000_000, current_price=108.0, status="open")
        # Closing snapshot — current_pnl_pct is 0.0 here by the app's own
        # convention (status != "open"); must NOT be misread as "at entry".
        make_snapshot(session, t1.id, FAKE_SYMBOLS[3], timestamp=4_000_000, current_price=111.0, current_pnl_pct=0.0, status="closed_win")
        session.commit()
        trade_id = t1.id
    finally:
        session.close()

    result = pc.tp_continuation_analytics()
    per_trade = next(p for p in result["per_trade"] if p["trade_outcome_id"] == trade_id)
    check(
        "returned_to_entry correctly detects the real 99.5 pullback (not a false negative, "
        "and not a false positive from the closing snapshot's zeroed pnl_pct)",
        per_trade["returned_to_entry"] is True, per_trade,
    )
    check(
        "returned_to_stop is False — price never actually reached stop_loss=95.0",
        per_trade["returned_to_stop"] is False, per_trade,
    )
    check(
        "continuation_after_tp1 reflects the real best price after TP1 (111 vs entry 100 = +11%)",
        per_trade["continuation_after_tp1"] == 11.0, per_trade,
    )


# ---------------------------------------------------------------------------
# 4. Confidence Lab — Brier score and ECE arithmetic
# ---------------------------------------------------------------------------
def test_confidence_lab_arithmetic():
    # Uses in-memory TradeOutcome objects against the pure
    # _confidence_lab_from_rows() function directly — NOT the live DB —
    # since confidence_lab() itself deliberately reads every resolved
    # trade in the whole app, and this dev DB already has real trades
    # sitting in the same 60-64 bucket that would otherwise contaminate
    # the hand-computed expected values below.
    rows = [TradeOutcome(confidence=60, status="closed_win") for _ in range(3)]
    rows += [TradeOutcome(confidence=60, status="closed_loss") for _ in range(2)]

    result = pc._confidence_lab_from_rows(rows, min_bucket_n=1)
    bucket = next(b for b in result["buckets"] if b["bucket"] == "60-64")
    check("60-64 bucket has n=5 (3 wins, 2 losses)", bucket["n"] == 5, bucket)
    check("actual_win_rate_pct = 60.0 (3/5)", bucket["actual_win_rate_pct"] == 60.0, bucket)
    check("avg_predicted_confidence = 60.0", bucket["avg_predicted_confidence"] == 60.0, bucket)
    check("calibration_gap = 0.0 (predicted matches actual exactly here)", bucket["calibration_gap"] == 0.0, bucket)
    # Brier score for 3 trades at p=0.6,outcome=1 and 2 at p=0.6,outcome=0:
    # 3*(0.6-1)^2 + 2*(0.6-0)^2 = 3*0.16 + 2*0.36 = 0.48+0.72=1.2; /5=0.24
    check("brier_score matches hand-computed 0.24", result["brier_score"] == 0.24, result["brier_score"])
    check("expected_calibration_error = 0.0 (only bucket, gap is 0)", result["expected_calibration_error"] == 0.0, result)


# ---------------------------------------------------------------------------
# 5. Coin Leaderboard — min_sample gating
# ---------------------------------------------------------------------------
def test_coin_leaderboard_min_sample():
    session = SessionLocal()
    try:
        # Only 2 trades for this symbol — below min_sample=3, must be excluded.
        for i in range(2):
            make_trade(
                session, "ZZZPCLBUSDT", direction="long", status="closed_win",
                created_at=1_000_000 + i, entry_time=1_000_500, entry_low=100.0, entry_high=101.0,
                entry=100.0, stop_loss=95.0, tp1=110.0, confidence=60, realized_return_pct=5.0,
            )
        session.commit()
    finally:
        session.close()
    FAKE_SYMBOLS.append("ZZZPCLBUSDT")

    result = pc.coin_leaderboard(min_sample=3)
    ranked_symbols = {c["symbol"] for c in result["symbols_ranked"]}
    check("a symbol with only 2 trades is excluded below min_sample=3", "ZZZPCLBUSDT" not in ranked_symbols, ranked_symbols)


# ---------------------------------------------------------------------------
# 6. Trade Replay — shape and 404-equivalent None
# ---------------------------------------------------------------------------
def test_trade_replay():
    session = SessionLocal()
    try:
        t = make_trade(
            session, FAKE_SYMBOLS[0], direction="long", status="closed_win",
            created_at=1_000_000, entry_time=1_000_500, entry_low=100.0, entry_high=101.0,
            entry=100.5, stop_loss=95.0, tp1=110.0, tp1_hit=True, tp1_hit_at=2_000_000,
            exit_time=3_000_000, exit_price=111.0, realized_return_pct=10.4,
            level_reasoning={"entry_reasoning": "test reasoning"},
        )
        session.commit()
        trade_id = t.id
    finally:
        session.close()

    replay = pc.trade_replay(trade_id)
    check("trade_replay returns a payload for a real id", replay is not None)
    check("exit_reason correctly reads 'target reached' for closed_win", replay["exit_reason"] == "target reached", replay.get("exit_reason"))
    check("level_reasoning passed through untouched", replay["level_reasoning"] == {"entry_reasoning": "test reasoning"})
    check("trade_replay returns None for a nonexistent id (routes/performance.py turns this into 404)", pc.trade_replay(-999999) is None)


# ---------------------------------------------------------------------------
# 7. Trade Manager Analytics — recommendation logic
# ---------------------------------------------------------------------------
def test_trade_manager_recommendations():
    session = SessionLocal()
    try:
        # TP1 hit, still open -> should recommend moving stop to breakeven.
        t = make_trade(
            session, FAKE_SYMBOLS[1], direction="long", status="open",
            created_at=1_000_000, entry_time=1_000_500, entry_low=100.0, entry_high=101.0,
            entry=100.5, stop_loss=95.0, tp1=110.0, tp2=120.0, tp1_hit=True, tp1_hit_at=2_000_000,
            market_regime="risk_on",
        )
        make_snapshot(session, t.id, FAKE_SYMBOLS[1], timestamp=2_000_000, current_price=111.0, status="open")
        session.commit()
        trade_id = t.id
    finally:
        session.close()

    result = pc.open_trade_management_analytics()
    entry = next(x for x in result["trades"] if x["trade_outcome_id"] == trade_id)
    check("recommends Move Stop to Breakeven once TP1 is hit and TP2 is not yet", entry["recommendation"] == "Move Stop to Breakeven", entry)
    check("distances computed relative to the latest snapshot price", entry["distances"]["to_tp2_pct"] is not None, entry["distances"])
    check("note explicitly states analytics-only, no execution", "Analytics only" in result["note"])


try:
    test_scanner_health_gap_detection()
    test_stop_execution_audit()
    test_tp_continuation_sign_bugs()
    test_confidence_lab_arithmetic()
    test_coin_leaderboard_min_sample()
    test_trade_replay()
    test_trade_manager_recommendations()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
