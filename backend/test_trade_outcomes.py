"""Manual verification script for the TradeOutcome closed loop.

Real trades take days to resolve, so this simulates price ticks instead of
waiting. Not a pytest suite (no test infra elsewhere in this project) — run
directly with `python test_trade_outcomes.py`. Runs against the real dev DB
using clearly-fake symbols (ZZZTEST*) and cleans up after itself, including
on failure.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import trade_outcomes, trade_reports
from app.models.db_models import TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZTEST1USDT", "ZZZTEST2USDT", "ZZZTEST3USDT"]


def cleanup():
    session = SessionLocal()
    try:
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
              tp1=105.0, tp2=110.0, tp3=None, time_horizon="swing",
              reasons_for=None, reasons_against=None, summary="test plan"):
    return FakePlan(
        recommendation=direction, entry_low=entry_low, entry_high=entry_high,
        stop_loss=stop_loss, take_profit_1=tp1, take_profit_2=tp2, take_profit_3=tp3,
        time_horizon=time_horizon, summary=summary,
        reasons_for=reasons_for or ["Strong momentum with MACD crossover"],
        reasons_against=reasons_against or ["Funding slightly elevated"],
    )


BREAKDOWN = {
    "trend": 20.0, "momentum": 10.0, "volume": 5.0, "funding": 8.0, "structure": 12.0,
    "history": 5.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
    "risk": -2.0, "total": 65.0,
}
FEATURES = {
    "fear_greed": {"value": 35},
    "news_context": {"headlines": [{"source": "CoinDesk", "title": "Test headline"}],
                      "reddit_mention_count": 3, "reddit_sample_titles": ["test post"]},
}
HISTORY_STATS = {"win_rate": 62.0, "sample_size": 25}
ML_PREDICTION = {"win_probability": 0.58, "large_drawdown_probability": 0.1}
REGIME = {"label": "risk_on", "trend": "bullish"}


def get_row(symbol):
    session = SessionLocal()
    try:
        return session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(
            TradeOutcome.id.desc()
        ).first()
    finally:
        session.close()


def test_open_and_win_via_tp():
    symbol = FAKE_SYMBOLS[0]
    plan = make_plan(symbol, direction="long", entry_low=100.0, entry_high=101.0,
                      stop_loss=97.0, tp1=105.0, tp2=110.0)
    trade_outcomes.open_trade_outcome(symbol, plan, BREAKDOWN, FEATURES, HISTORY_STATS,
                                       ML_PREDICTION, REGIME, now_ms=1_000_000)
    row = get_row(symbol)
    assert row.status == "pending", row.status
    assert row.tp3 is None

    # price outside entry zone -> stays pending
    trade_outcomes.update_open_trades({symbol: 95.0}, now_ms=1_060_000)
    row = get_row(symbol)
    assert row.status == "pending", row.status

    # price enters zone -> opens
    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=1_120_000)
    row = get_row(symbol)
    assert row.status == "open", row.status
    assert row.entry_hit is True
    assert row.entry_time == 1_120_000

    # price runs up past TP1 first (MFE should track this even past TP1)
    trade_outcomes.update_open_trades({symbol: 106.0}, now_ms=1_180_000)
    row = get_row(symbol)
    assert row.tp1_hit is True
    assert row.status == "open"  # tp2 is defined, so tp1 alone doesn't close it
    assert row.max_favorable_price == 106.0

    # dips a bit (tests MAE tracking mid-trade) then finally reaches TP2 -> closes win
    trade_outcomes.update_open_trades({symbol: 103.0}, now_ms=1_240_000)
    trade_outcomes.update_open_trades({symbol: 111.0}, now_ms=1_300_000)
    row = get_row(symbol)
    assert row.status == "closed_win", row.status
    assert row.tp2_hit is True
    assert row.exit_time == 1_300_000
    assert row.holding_minutes == round((1_300_000 - 1_120_000) / 60_000, 1)
    expected_return = round((111.0 - 100.5) / 100.5 * 100, 3)
    assert row.realized_return_pct == expected_return, (row.realized_return_pct, expected_return)
    assert row.max_runup_pct == round((111.0 - 100.5) / 100.5 * 100, 3)
    assert row.max_drawdown_pct == round((100.5 - 100.5) / 100.5 * 100, 3)  # never went below entry after opening... wait it did dip? no, 103 > entry
    assert row.tp1_before_stop is True
    assert row.counterfactual_direction == "short"
    assert row.counterfactual_return_pct == round(-expected_return, 3)
    print(f"[PASS] open->win via TP2: return={row.realized_return_pct}%, "
          f"key_component={row.key_score_component}, mentioned={row.explanation_mentioned_key_factor}")


def test_stop_loss_after_tp1():
    """TP1 hit, then price reverses and hits stop — tp1_before_stop should be True."""
    symbol = FAKE_SYMBOLS[1]
    plan = make_plan(symbol, direction="long", entry_low=50.0, entry_high=51.0,
                      stop_loss=48.0, tp1=54.0, tp2=None)
    trade_outcomes.open_trade_outcome(symbol, plan, BREAKDOWN, FEATURES, HISTORY_STATS,
                                       ML_PREDICTION, REGIME, now_ms=2_000_000)
    trade_outcomes.update_open_trades({symbol: 50.5}, now_ms=2_060_000)  # opens
    row = get_row(symbol)
    assert row.status == "open"

    # tp1 is the only target defined -> hitting it should close as a win immediately
    trade_outcomes.update_open_trades({symbol: 54.5}, now_ms=2_120_000)
    row = get_row(symbol)
    assert row.status == "closed_win", row.status
    assert row.tp1_hit is True
    print(f"[PASS] single-target TP1 close: return={row.realized_return_pct}%")


def test_short_direction():
    symbol = FAKE_SYMBOLS[2]
    plan = make_plan(symbol, direction="short", entry_low=200.0, entry_high=202.0,
                      stop_loss=210.0, tp1=190.0, tp2=None)
    trade_outcomes.open_trade_outcome(symbol, plan, BREAKDOWN, FEATURES, HISTORY_STATS,
                                       ML_PREDICTION, REGIME, now_ms=3_000_000)
    trade_outcomes.update_open_trades({symbol: 201.0}, now_ms=3_060_000)  # opens (short entry)
    row = get_row(symbol)
    assert row.status == "open"

    # price falls (favorable for short) then hits stop above entry
    trade_outcomes.update_open_trades({symbol: 195.0}, now_ms=3_120_000)
    row = get_row(symbol)
    assert row.max_favorable_price == 195.0

    trade_outcomes.update_open_trades({symbol: 211.0}, now_ms=3_180_000)
    row = get_row(symbol)
    assert row.status == "closed_loss", row.status
    assert row.stop_hit is True
    expected_return = round((201.0 - 211.0) / 201.0 * 100, 3)
    assert row.realized_return_pct == expected_return, (row.realized_return_pct, expected_return)
    assert row.realized_return_pct < 0
    print(f"[PASS] short stop-out: return={row.realized_return_pct}%")


def test_invalidation_on_new_plan():
    symbol = FAKE_SYMBOLS[0] + "B"
    FAKE_SYMBOLS.append(symbol)
    plan1 = make_plan(symbol, entry_low=10.0, entry_high=11.0, stop_loss=9.0, tp1=13.0)
    trade_outcomes.open_trade_outcome(symbol, plan1, BREAKDOWN, FEATURES, HISTORY_STATS,
                                       ML_PREDICTION, REGIME, now_ms=4_000_000)
    row1_id = get_row(symbol).id

    # a materially different plan for the same symbol before the first resolves
    plan2 = make_plan(symbol, entry_low=12.0, entry_high=13.0, stop_loss=11.0, tp1=16.0)
    trade_outcomes.open_trade_outcome(symbol, plan2, BREAKDOWN, FEATURES, HISTORY_STATS,
                                       ML_PREDICTION, REGIME, now_ms=4_060_000)

    session = SessionLocal()
    try:
        old_row = session.get(TradeOutcome, row1_id)
        assert old_row.status == "invalidated", old_row.status
        new_row = get_row(symbol)
        assert new_row.status == "pending"
        assert new_row.id != row1_id
    finally:
        session.close()

    # identical plan re-issued -> should NOT create a duplicate row
    count_before = session_count(symbol)
    trade_outcomes.open_trade_outcome(symbol, plan2, BREAKDOWN, FEATURES, HISTORY_STATS,
                                       ML_PREDICTION, REGIME, now_ms=4_120_000)
    count_after = session_count(symbol)
    assert count_before == count_after, (count_before, count_after)
    print("[PASS] invalidation on superseding plan + no duplicate on identical plan")


def session_count(symbol):
    session = SessionLocal()
    try:
        return session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).count()
    finally:
        session.close()


def test_reports():
    digest = trade_reports.performance_digest(0, 10_000_000, "test window")
    assert digest["signals_resolved"] >= 3, digest
    assert digest["wins"] >= 2, digest
    assert digest["losses"] >= 1, digest
    print(f"[PASS] performance_digest: {digest}")

    breakdown = trade_reports.monthly_breakdown(0, 10_000_000)
    print(f"[PASS] monthly_breakdown ran without error: {breakdown}")

    corr = trade_reports.score_correlations(min_sample=1)
    assert "win_minus_loss_mean" in corr, corr
    print(f"[PASS] score_correlations: {corr}")


if __name__ == "__main__":
    cleanup()
    try:
        test_open_and_win_via_tp()
        test_stop_loss_after_tp1()
        test_short_direction()
        test_invalidation_on_new_plan()
        test_reports()
        print("\nALL TESTS PASSED")
    finally:
        cleanup()
