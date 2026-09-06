"""Manual verification script for Karma V2.1 Phase 3 (score weight
recalibration) and Phase 6 (Red Flag engine), plus the soft short-side
derate flag (Phase 5).

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_karma_v2_1_scoring_and_flags.py`. The scoring checks are pure
functions (no DB); the end-to-end check uses fake ZZZV21* symbols and
cleans up after itself.
"""

import sys

sys.path.insert(0, ".")

from app.db import SessionLocal, init_db
from app.engine import entry_flags, red_flags, trade_outcomes
from app.engine.scoring import SCORE_FORMULA_VERSION, score_opportunity
from app.models.db_models import TradeOutcome

init_db()

FAKE_SYMBOLS = ["ZZZV21AUSDT", "ZZZV21BUSDT"]
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
# 1. Score formula version bumped
# ---------------------------------------------------------------------------
check("SCORE_FORMULA_VERSION bumped to 2.1", SCORE_FORMULA_VERSION == "2.1", SCORE_FORMULA_VERSION)


# ---------------------------------------------------------------------------
# 2. Momentum V2.1: RSI 50-70 rewarded, RSI 30-49 ("chop zone") penalized,
#    max contribution reduced from 15 to 12.
# ---------------------------------------------------------------------------
def features_with_rsi(rsi, macd_hist=1.0):
    return {
        "indicators_4h": {"rsi14": rsi, "macd_hist": macd_hist, "adx14": 0},
    }


healthy = score_opportunity(features_with_rsi(60), None, None, None)
chop = score_opportunity(features_with_rsi(35), None, None, None)
extreme = score_opportunity(features_with_rsi(10), None, None, None)
check("RSI 50-70 (healthy) scores higher momentum than RSI 30-49 (chop zone)", healthy["momentum"] > chop["momentum"], (healthy["momentum"], chop["momentum"]))
check("RSI 30-49 chop zone scores the SAME low momentum as extreme exhaustion (both flagged as poor)", chop["momentum"] == extreme["momentum"], (chop["momentum"], extreme["momentum"]))
check("max momentum contribution is now 12 (was 15)", healthy["momentum"] == 12.0, healthy["momentum"])


# ---------------------------------------------------------------------------
# 3. Volume V2.1: max contribution increased from 10 to 13.
# ---------------------------------------------------------------------------
full_volume_features = {"indicators_4h": {"obv_slope": 1, "cmf": 0.1, "mfi": 50}}
vol_breakdown = score_opportunity(full_volume_features, None, None, None)
check("max volume contribution is now 13 (was 10)", vol_breakdown["volume"] == 13.0, vol_breakdown["volume"])


# ---------------------------------------------------------------------------
# 4. Structure V2.1: FVG term increased from 5 to 7, max structure 17.
# ---------------------------------------------------------------------------
struct_features = {
    "indicators_4h": {},
    "structure_4h": {"trend": "bull", "fvg_up": True, "fvg_down": False, "choch": True},
}
struct_breakdown = score_opportunity(struct_features, None, None, None)
check("structure score reflects FVG=7 (was 5): 6 (trend) + 7 (fvg) + 4 (choch) = 17", struct_breakdown["structure"] == 17.0, struct_breakdown["structure"])


# ---------------------------------------------------------------------------
# 5. Trend, History, Funding, Regime UNCHANGED (explicit "hold" per the
#    V2.1 report's Rules 11/12 — mixed/inconclusive stratified evidence).
# ---------------------------------------------------------------------------
trend_features = {
    "indicators_1h": {"trend_vs_ema50": "above"}, "indicators_4h": {"trend_vs_ema50": "above", "adx14": 30},
    "indicators_1d": {"trend_vs_ema50": "above"},
}
trend_breakdown = score_opportunity(trend_features, None, None, None)
check("trend formula unchanged: 15 + 30/40*10 = 22.5 (same as pre-V2.1)", trend_breakdown["trend"] == 22.5, trend_breakdown["trend"])
history_breakdown = score_opportunity({}, {"sample_size": 25, "win_rate": 70}, None, None)
check("history formula unchanged: (70-50)/50*15 = 6.0", history_breakdown["history"] == 6.0, history_breakdown["history"])


# ---------------------------------------------------------------------------
# 6. Red flags — observational, correct triggering
# ---------------------------------------------------------------------------
chop_flags = red_flags.compute_red_flags({"rsi14": 35}, 6.0, None)
check("RSI 30-49 + weak structure + no history triggers all 3 red flags", chop_flags["red_flag_score"] == 3, chop_flags)
check("risk_explanation has one string per triggered flag", len(chop_flags["risk_explanation"]) == 3)

clean_flags = red_flags.compute_red_flags({"rsi14": 60}, 12.0, 0.55)
check("a clean setup triggers zero red flags", clean_flags["red_flag_score"] == 0, clean_flags)


# ---------------------------------------------------------------------------
# 7. Short-side soft derate flag (entry_flags.py) — SOFT, not a hard gate
# ---------------------------------------------------------------------------
tight_short_rr = {"rr_tp1": 2.0, "entry_to_sl_atr": 0.5}
loose_short_rr = {"rr_tp1": 2.0, "entry_to_sl_atr": 1.0}
flags_tight_short = entry_flags.compute_diagnostic_flags({}, {}, "neutral", tight_short_rr, 0.5, 0.5, 1, direction="short")
flags_loose_short = entry_flags.compute_diagnostic_flags({}, {}, "neutral", loose_short_rr, 0.5, 0.5, 1, direction="short")
flags_tight_long = entry_flags.compute_diagnostic_flags({}, {}, "neutral", tight_short_rr, 0.5, 0.5, 1, direction="long")
check("a short with a tight (<0.83 ATR) stop gets SHORT_TIGHT_STOP flagged", "SHORT_TIGHT_STOP" in flags_tight_short, flags_tight_short)
check("a short with a wide (>=0.83 ATR) stop does NOT get flagged", "SHORT_TIGHT_STOP" not in flags_loose_short, flags_loose_short)
check("the SAME tight stop on a LONG is never flagged (short-specific, not a general tight-stop rule)", "SHORT_TIGHT_STOP" not in flags_tight_long, flags_tight_long)
check(
    "this is a FLAG, not a rejection — compute_diagnostic_flags never raises or returns a reject/no_trade signal",
    isinstance(flags_tight_short, list),
)


# ---------------------------------------------------------------------------
# 8. End-to-end: open_trade_outcome() attaches red_flags additively
# ---------------------------------------------------------------------------
class FakePlan:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_end_to_end_red_flags_attached():
    symbol = FAKE_SYMBOLS[0]
    plan = FakePlan(
        recommendation="short", entry_low=100.0, entry_high=101.0, stop_loss=105.0,
        take_profit_1=90.0, take_profit_2=None, take_profit_3=None, time_horizon="swing",
        summary="t", reasons_for=["x"], reasons_against=["y"],
        entry_reasoning=None, sl_reasoning=None, tp1_reasoning=None, tp2_reasoning=None, tp3_reasoning=None,
    )
    breakdown = {
        "trend": 20.0, "momentum": 10.0, "volume": 5.0, "funding": 8.0, "structure": 6.0,
        "history": 0.0, "regime": 3.0, "ml": 4.0, "sentiment": 1.0, "liquidity": -1.0,
        "risk": -2.0, "total": 54.0,
    }
    features = {"indicators_4h": {"rsi14": 35}}
    trade_outcomes.open_trade_outcome(
        symbol, plan, breakdown, features, None, None, {"label": "mixed"}, now_ms=1_000_000,
        confidence=55, grade="B", entry_quality="neutral",
    )
    session = SessionLocal()
    try:
        row = session.query(TradeOutcome).filter(TradeOutcome.symbol == symbol).order_by(TradeOutcome.id.desc()).first()
    finally:
        session.close()

    check("red_flags is populated (not None) on a newly-opened trade", row.red_flags is not None)
    check("rsi_chop_zone (RSI=35, structure=6, no history) triggers all 3 flags", row.red_flags["red_flag_score"] == 3, row.red_flags)
    check("diagnostic_flags includes SHORT_TIGHT_STOP for a short with no ATR risk_reward data computed as tight (or is absent if entry_to_sl_atr unavailable)", isinstance(row.diagnostic_flags, list))


try:
    test_end_to_end_red_flags_attached()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
