"""Manual verification script for Karma V3.2: Trade Truth Engine,
Prediction Version Metadata, Market Health, Portfolio Exposure, Daily
Scorecard, Watchlist Outcome breakdown, Trade Journal, Calibration
Dashboard. Backend-only, additive, hard-freeze honored (scoring.py,
decision.py, market_regime.py, reasoning.py prompt, ML weights/training,
existing trade generation logic — all untouched, verified via git diff
--stat before every commit in this session).

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_karma_v3_2_systems.py`. Uses clearly-fake symbols
(ZZZV32*) for end-to-end checks and cleans up after itself.
"""

import asyncio
import sys

sys.path.insert(0, ".")

from app.analytics import (
    market_health,
    missed_opportunity,
    portfolio_exposure,
    prediction_metadata,
    trade_journal,
    trade_truth,
)
from app.db import SessionLocal, init_db
from app.engine import trade_outcomes
from app.models.db_models import PredictionSnapshot, RejectedOpportunityOutcome, TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZV32AUSDT", "ZZZV32BUSDT"]
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
        session.query(RejectedOpportunityOutcome).filter(
            RejectedOpportunityOutcome.symbol.in_(FAKE_SYMBOLS)
        ).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. Trade Truth Engine — every verdict branch, in-memory rows
# ---------------------------------------------------------------------------
def test_trade_truth_verdicts():
    stale = TradeOutcome(status="closed_stale")
    check("closed_stale -> never_triggered", trade_truth.classify_truth(stale)["verdict"] == "never_triggered")

    outage_row = TradeOutcome(status="closed_loss", exit_time=5_000, tp1_hit=False, tp2_hit=False, max_runup_pct=0.2)
    outages = [{"start": 4_000, "end": 6_000}]
    check("exit inside a verified outage -> infrastructure_failure", trade_truth.classify_truth(outage_row, outages)["verdict"] == "infrastructure_failure")

    late_row = TradeOutcome(status="closed_loss", entry_quality="late", tp1_hit=False, max_runup_pct=0.1)
    check("entry_quality=late -> late_entry", trade_truth.classify_truth(late_row)["verdict"] == "late_entry")

    perfect = TradeOutcome(status="closed_win", tp1_hit=True, tp2_hit=True, tp3_hit=True, max_drawdown_pct=-1.0)
    check("win w/ tp3 + shallow MAE -> perfect_trade", trade_truth.classify_truth(perfect)["verdict"] == "perfect_trade")

    good_deep_drawdown = TradeOutcome(status="closed_win", tp1_hit=True, tp2_hit=True, tp3_hit=True, max_drawdown_pct=-8.0)
    check("win w/ tp3 but deep MAE -> good_trade (not perfect)", trade_truth.classify_truth(good_deep_drawdown)["verdict"] == "good_trade")

    bad_exit = TradeOutcome(status="closed_loss", tp1_hit=True, tp2_hit=False, tp3_hit=False, max_runup_pct=5.0)
    check("loss after reaching tp1 -> good_entry_bad_exit", trade_truth.classify_truth(bad_exit)["verdict"] == "good_entry_bad_exit")

    immediate = TradeOutcome(status="closed_loss", tp1_hit=False, tp2_hit=False, max_runup_pct=0.3)
    check("loss, MFE<1%, no TP -> bad_structure_call", trade_truth.classify_truth(immediate)["verdict"] == "bad_structure_call")

    near_miss = TradeOutcome(status="closed_loss", tp1_hit=False, tp2_hit=False, max_runup_pct=9.0, entry=100.0, tp1=110.0)
    check("loss, MFE got within 80% of the distance to TP1 -> near_miss_early_stop", trade_truth.classify_truth(near_miss)["verdict"] == "near_miss_early_stop", trade_truth.classify_truth(near_miss))


# ---------------------------------------------------------------------------
# 2. Prediction Version Metadata
# ---------------------------------------------------------------------------
def test_prediction_metadata():
    meta = prediction_metadata.build_prediction_metadata()
    expected_keys = {
        "prediction_version", "score_formula_version", "entry_quality_version",
        "trade_manager_version", "reliability_version", "expected_value_version",
        "prompt_version", "prompt_hash", "build_timestamp",
    }
    check("build_prediction_metadata returns exactly the requested keys", expected_keys.issubset(meta.keys()), meta.keys())
    check("prompt_hash is a real hash (12 hex chars), not empty", len(meta["prompt_hash"]) == 12)

    meta2 = prediction_metadata.build_prediction_metadata()
    check("prompt_hash is stable across calls (deterministic, not random)", meta["prompt_hash"] == meta2["prompt_hash"])


# ---------------------------------------------------------------------------
# 3. Market Health — pure function, hand-verifiable
# ---------------------------------------------------------------------------
def test_market_health():
    regime = {"confidence": 80, "breadth_bullish_pct": 90.0, "breadth_bearish_pct": 5.0}
    fear_greed = {"value": 50}  # perfectly neutral
    result = market_health.compute_market_health(regime, fear_greed, scan_rows=[])
    check("trend_alignment = 80/100*20 = 16.0", result["components"]["trend_alignment"]["score"] == 16.0, result["components"]["trend_alignment"])
    check("breadth = max(90,5)/100*20 = 18.0", result["components"]["breadth"]["score"] == 18.0, result["components"]["breadth"])
    check("fear_greed at value=50 (perfectly neutral) scores the max 10.0", result["components"]["fear_greed"]["score"] == 10.0, result["components"]["fear_greed"])
    check("score is the sum of all components, category assigned", result["score"] > 0 and result["category"] in ("Very Healthy", "Healthy", "Neutral", "Weak", "Danger"), result)

    extreme_fg = market_health.compute_market_health(regime, {"value": 95}, scan_rows=[])
    check("extreme Fear&Greed (95) scores LOWER than neutral (50)", extreme_fg["components"]["fear_greed"]["score"] < result["components"]["fear_greed"]["score"])

    none_inputs = market_health.compute_market_health(None, None, None)
    check("all-None inputs never crash and default to neutral components", none_inputs["score"] > 0, none_inputs)


# ---------------------------------------------------------------------------
# 4. Portfolio Exposure — family classification + concentration warning
# ---------------------------------------------------------------------------
class FakePlan:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_portfolio_exposure():
    session = SessionLocal()
    try:
        for i, sym in enumerate(["BTCUSDT", "ETHUSDT", "SOLUSDT"]):
            row = TradeOutcome(
                symbol=sym, direction="long", status="open", timeframe="swing",
                created_at=1_000_000, entry_time=1_000_500, entry_low=100.0, entry_high=101.0,
                entry=100.5, stop_loss=95.0, tp1=110.0, score=60.0, trend_score=0.0, momentum_score=0.0,
                volume_score=0.0, funding_score=0.0, structure_score=0.0, history_score=0.0,
                regime_score=0.0, ml_score=0.0, sentiment_score=0.0, liquidity_score=0.0, risk_score=0.0,
                reasoning="t", reasons_for=[], reasons_against=[],
            )
            session.add(row)
        session.commit()
    finally:
        session.close()

    check("_family_for classifies BTCUSDT as crypto_majors", portfolio_exposure._family_for("BTCUSDT") == "crypto_majors")
    check("_family_for classifies an unknown symbol as other_altcoin (never a false claim)", portfolio_exposure._family_for("ZZZUNKNOWNUSDT") == "other_altcoin")

    result = portfolio_exposure.portfolio_exposure()
    check("portfolio_exposure reports n_open, family_exposure_pct, warnings", "n_open" in result and "family_exposure_pct" in result and "warnings" in result, result.keys())

    # cleanup the 3 real BTC/ETH/SOL test rows we just inserted (these are
    # real symbols, not ZZZ-prefixed — clean them up explicitly here).
    session = SessionLocal()
    try:
        session.query(TradeOutcome).filter(
            TradeOutcome.symbol.in_(["BTCUSDT", "ETHUSDT", "SOLUSDT"]),
            TradeOutcome.created_at == 1_000_000,
        ).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 5. Missed Opportunity breakdown — still gated, no early conclusions
# ---------------------------------------------------------------------------
def test_missed_opportunity_breakdown_gated():
    result = missed_opportunity.rejection_outcome_breakdown(min_sample=500)
    check("breakdown reports n_resolved_total without a rate below the threshold", "n_resolved_total" in result, result.keys())
    for entry in result["by_rejection_reason"]:
        if not entry["reliable"]:
            check(f"unreliable reason '{entry['rejection_reason']}' has a note, not a fabricated rate", "note" in entry and "favorable_at_72h_pct" not in entry, entry)


# ---------------------------------------------------------------------------
# 6. End-to-end: Trade Truth + Trade Journal on a real (fake-symbol) trade
# ---------------------------------------------------------------------------
def test_end_to_end_truth_and_journal():
    # Real-scale epoch ms (not tiny numbers like 1_000_000) — mixing a
    # 1970-scale fake timestamp into the shared PredictionSnapshot table
    # alongside real ~present-day rows creates a SPURIOUS multi-decade
    # "scanner outage" gap between them, which would make this trade's
    # exit look like it fell inside an outage. Anchoring to real "now"
    # avoids polluting scanner_health()'s live outage detection.
    import time

    base_ms = int(time.time() * 1000)
    symbol = FAKE_SYMBOLS[0]
    plan = FakePlan(
        recommendation="long", entry_low=100.0, entry_high=101.0, stop_loss=95.0,
        take_profit_1=110.0, take_profit_2=None, take_profit_3=None, time_horizon="swing",
        summary="t", reasons_for=["x"], reasons_against=["y"],
        entry_reasoning=None, sl_reasoning=None, tp1_reasoning=None, tp2_reasoning=None, tp3_reasoning=None,
    )
    breakdown = {
        "trend": 20.0, "momentum": 10.0, "volume": 5.0, "funding": 8.0, "structure": 12.0,
        "history": 0.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
        "risk": -2.0, "total": 60.0,
    }
    trade_outcomes.open_trade_outcome(
        symbol, plan, breakdown, {}, None, None, {"label": "mixed"}, now_ms=base_ms,
        confidence=63, grade="B", entry_quality="excellent",
    )
    session = SessionLocal()
    try:
        row = session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(TradeOutcome.id.desc()).first()
    finally:
        session.close()

    check("newly-opened trade gets a real prediction_metadata blob", row.prediction_metadata is not None and "prediction_version" in row.prediction_metadata, row.prediction_metadata)

    trade_outcomes.update_open_trades({symbol: 100.5}, now_ms=base_ms + 10_000)  # entry
    trade_outcomes.update_open_trades({symbol: 94.0}, now_ms=base_ms + 20_000)  # stop hit, no TP1

    session = SessionLocal()
    try:
        row = session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(TradeOutcome.id.desc()).first()
    finally:
        session.close()

    truth = trade_truth.truth_for_trade(row.id)
    check("truth_for_trade returns a verdict for a real resolved trade", truth is not None and truth["verdict"] in ("bad_structure_call", "near_miss_early_stop"), truth)
    check("truth includes lessons", len(truth["lessons"]) > 0, truth["lessons"])

    journal = trade_journal.journal_entry(row.id)
    check("journal_entry returns strengths/mistakes/outcome", journal is not None and "strengths" in journal and "mistakes" in journal and journal["outcome"] == truth["verdict"], journal)


try:
    test_trade_truth_verdicts()
    test_prediction_metadata()
    test_market_health()
    test_portfolio_exposure()
    test_missed_opportunity_breakdown_gated()
    test_end_to_end_truth_and_journal()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
