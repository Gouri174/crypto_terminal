"""Manual verification for the new reasoning.py pipeline, using a mocked
Claude response instead of a real API call.

Written because the live end-to-end test was blocked: the configured
Anthropic account is out of credits (confirmed via a real 400
insufficient_credits error from api.anthropic.com, not a code bug). This
covers everything EXCEPT the real API round-trip: decide_direction,
compute_confidence, market_checklist, trade_grade, prompt construction,
JSON parsing, forced-field injection, and TradePlan validation. The actual
live call still needs to be checked once credits are available — see
README for the caveat.
"""

import json
import sys
from unittest.mock import patch

sys.path.insert(0, ".")

from app.engine import reasoning

FEATURES = {
    "symbol": "TESTUSDT",
    "indicators_1h": {"trend_vs_ema50": "above"},
    "indicators_4h": {"trend_vs_ema50": "above", "atr14": 2.0, "last_close": 100.0},
    "indicators_1d": {"trend_vs_ema50": "above"},
    "long_short_ratio": 1.2,
    "cross_exchange": {"price_spread_pct": 0.1},
}
BREAKDOWN = {
    "trend": 20, "momentum": 10, "volume": 8, "funding": 8, "structure": 12,
    "history": 10, "regime": 3, "ml": 4, "sentiment": 1, "liquidity": 0,
    "risk": -2, "total": 74,
}
HISTORY_STATS = {"win_rate": 65, "sample_size": 30, "mean_return_pct": 2.5,
                  "median_return_pct": 2.0, "total_history_available": 100}
ML_PREDICTION = {"win_probability": 0.6, "large_drawdown_probability": 0.1}
REGIME = {"label": "risk_on", "trend": "bullish", "confidence": 70,
          "btc_trend": "bull", "breadth_bullish_pct": 70.0, "breadth_bearish_pct": 30.0,
          "universe_size": 40, "summary": "test regime"}
ALTERNATIVE = {"symbol": "OTHERUSDT", "score": 68.0, "direction": "long"}

MOCK_CLAUDE_JSON = {
    "entry_low": 99.0, "entry_high": 100.5, "stop_loss": 96.0,
    "take_profit_1": 104.0, "take_profit_2": 108.0, "take_profit_3": 112.0,
    "risk_level": "medium", "time_horizon": "swing", "risk_reward": "~2:1 to TP1",
    "market_regime": "Aligned with the bullish regime.",
    "thesis": "Clean multi-timeframe trend agreement with confirming volume.",
    "reasons_for": ["Trend aligned on all three timeframes", "Volume confirms via OBV"],
    "reasons_against": ["Funding is not extreme but positioning is a bit long-heavy"],
    "invalidation": "A 4h close back below the EMA50 invalidates this.",
    "historical_comparison": "Similar past setups returned +2.5% on average.",
    "bullish_scenario": "Breaks resistance and runs to TP2.",
    "bearish_scenario": "Fails at resistance and reverts to the stop.",
    "biggest_risks": ["Crowded long positioning", "BTC-wide reversal risk"],
    "evidence_that_would_increase_confidence": "A fresh BOS on the 4h would help.",
    "alternative_trade_reason": "OTHERUSDT has cleaner structure and a tighter stop.",
    "summary": "A clean, if unremarkable, trend-continuation long.",
    "disclaimer": "Not financial advice.",
}


class FakeTextBlock:
    type = "text"
    text = json.dumps(MOCK_CLAUDE_JSON)


class FakeResponse:
    content = [FakeTextBlock()]


def test_full_pipeline():
    with patch.object(reasoning._client.messages, "create", return_value=FakeResponse()):
        plan = reasoning.analyze_symbol(
            FEATURES, BREAKDOWN, HISTORY_STATS, REGIME, ML_PREDICTION, ALTERNATIVE
        )

    assert plan.symbol == "TESTUSDT"
    assert plan.recommendation == "long", plan.recommendation
    assert plan.grade in ("A+", "A", "B+", "B", "C", "Avoid")
    assert plan.confidence_breakdown is not None
    assert set(plan.confidence_breakdown.components.keys()) == {
        "trend", "history", "ml", "structure", "volume", "funding", "regime", "sentiment"
    }
    assert plan.checklist["trend_confirms"] is True
    assert plan.thesis == MOCK_CLAUDE_JSON["thesis"]
    assert plan.alternative_trade is not None
    assert plan.alternative_trade.symbol == "OTHERUSDT"  # forced from ALTERNATIVE, not from Claude's JSON
    assert plan.alternative_trade.reason == MOCK_CLAUDE_JSON["alternative_trade_reason"]
    assert plan.take_profit_3 == 112.0
    assert plan.score_breakdown is not None
    assert plan.history_match is not None
    assert plan.ml_prediction is not None
    print(f"[PASS] full pipeline: direction={plan.recommendation}, "
          f"confidence={plan.confidence}, grade={plan.grade}, "
          f"alternative={plan.alternative_trade.symbol}")


def test_no_trade_direction_ignores_claude():
    """If the deterministic engine says no_trade, the forced recommendation
    must be no_trade even if Claude's (mocked) reasoning text sounds bullish
    — proving Claude's own text can never leak into the recommendation
    field."""
    mixed_features = dict(FEATURES)
    mixed_features["indicators_1h"] = {"trend_vs_ema50": "above"}
    mixed_features["indicators_4h"] = {"trend_vs_ema50": "below", "atr14": 2.0, "last_close": 100.0}
    mixed_features["indicators_1d"] = {}  # missing vote -> genuine 1-1 tie, not a majority

    with patch.object(reasoning._client.messages, "create", return_value=FakeResponse()):
        plan = reasoning.analyze_symbol(
            mixed_features, BREAKDOWN, HISTORY_STATS, REGIME, ML_PREDICTION, None
        )
    assert plan.recommendation == "no_trade", plan.recommendation
    assert plan.confidence == 0
    assert plan.grade == "Avoid"
    assert plan.alternative_trade is None
    print(f"[PASS] no_trade forced regardless of mocked JSON content: grade={plan.grade}")


def test_alternative_omitted_when_claude_says_null():
    with patch.object(reasoning._client.messages, "create", return_value=FakeResponse()):
        # ALTERNATIVE candidate exists, but simulate Claude declining to flag it
        mock = dict(MOCK_CLAUDE_JSON)
        mock["alternative_trade_reason"] = None
        with patch.object(FakeTextBlock, "text", json.dumps(mock)):
            plan = reasoning.analyze_symbol(
                FEATURES, BREAKDOWN, HISTORY_STATS, REGIME, ML_PREDICTION, ALTERNATIVE
            )
    assert plan.alternative_trade is None
    print("[PASS] alternative_trade stays null when Claude declines to flag one")


MOCK_BATCH_JSON = [
    {"symbol": "TESTUSDT", **MOCK_CLAUDE_JSON},
    {
        "symbol": "LOWGRADEUSDT",
        "entry_low": 10.0, "entry_high": 10.5, "stop_loss": 9.5,
        "take_profit_1": 11.0, "take_profit_2": None, "take_profit_3": None,
        "risk_level": "high", "time_horizon": "scalp",
        "reasons_for": ["Weak trend agreement only"],
        "reasons_against": ["Score is low, structure doesn't confirm"],
        "invalidation": "Any close below 9.5.",
        "summary": "Low-conviction setup, not a strong signal.",
        "disclaimer": "Not financial advice.",
    },
]


class FakeArrayTextBlock:
    type = "text"
    text = json.dumps(MOCK_BATCH_JSON)


class FakeArrayResponse:
    content = [FakeArrayTextBlock()]


def test_batch_pipeline():
    # LOWGRADEUSDT: engineered to score low -> grade should land in
    # decision._LOW_GRADES, exercising the short-schema path in the batch.
    low_breakdown = dict(BREAKDOWN)
    low_breakdown.update(trend=2, momentum=1, volume=1, funding=0, structure=1,
                          history=0, regime=0, ml=0, sentiment=0, liquidity=0, risk=-5, total=0)
    low_features = dict(FEATURES)
    low_features["symbol"] = "LOWGRADEUSDT"

    items = [
        {"symbol": "TESTUSDT", "features": FEATURES, "breakdown": BREAKDOWN,
         "history_stats": HISTORY_STATS, "ml_prediction": ML_PREDICTION, "alternative": ALTERNATIVE},
        {"symbol": "LOWGRADEUSDT", "features": low_features, "breakdown": low_breakdown,
         "history_stats": None, "ml_prediction": None, "alternative": None},
    ]

    with patch.object(reasoning._client.messages, "create", return_value=FakeArrayResponse()):
        plans = reasoning.analyze_batch(items, REGIME)

    assert set(plans.keys()) == {"TESTUSDT", "LOWGRADEUSDT"}, plans.keys()
    assert plans["TESTUSDT"].recommendation == "long"
    assert plans["TESTUSDT"].thesis == MOCK_CLAUDE_JSON["thesis"]
    assert plans["LOWGRADEUSDT"].grade in ("C", "Avoid")
    assert plans["LOWGRADEUSDT"].thesis is None  # short schema never asked for one
    print(f"[PASS] batch pipeline: {len(plans)} plans, "
          f"TESTUSDT grade={plans['TESTUSDT'].grade}, LOWGRADEUSDT grade={plans['LOWGRADEUSDT'].grade}")


def test_batch_skips_unrecognized_and_reports_missing():
    """A batch response naming a symbol we didn't ask about, or omitting
    one we did, must not crash the whole batch — just skip/report."""
    partial_response = [
        {"symbol": "TESTUSDT", **MOCK_CLAUDE_JSON},
        {"symbol": "NOT_IN_REQUEST", **MOCK_CLAUDE_JSON},
    ]
    items = [
        {"symbol": "TESTUSDT", "features": FEATURES, "breakdown": BREAKDOWN,
         "history_stats": HISTORY_STATS, "ml_prediction": ML_PREDICTION, "alternative": None},
        {"symbol": "MISSINGUSDT", "features": {**FEATURES, "symbol": "MISSINGUSDT"}, "breakdown": BREAKDOWN,
         "history_stats": None, "ml_prediction": None, "alternative": None},
    ]

    class PartialTextBlock:
        type = "text"
        text = json.dumps(partial_response)

    class PartialResponse:
        content = [PartialTextBlock()]

    with patch.object(reasoning._client.messages, "create", return_value=PartialResponse()):
        plans = reasoning.analyze_batch(items, REGIME)

    assert set(plans.keys()) == {"TESTUSDT"}, plans.keys()  # MISSINGUSDT absent, NOT_IN_REQUEST dropped
    print("[PASS] batch tolerates unrecognized/missing symbols without crashing")


if __name__ == "__main__":
    test_full_pipeline()
    test_no_trade_direction_ignores_claude()
    test_alternative_omitted_when_claude_says_null()
    test_batch_pipeline()
    test_batch_skips_unrecognized_and_reports_missing()
    print("\nALL MOCKED REASONING TESTS PASSED")
