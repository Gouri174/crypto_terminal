"""Karma V3.3-B — primary verdict taxonomy. Synthetic (unpersisted) rows + read-only real-DB consistency."""
import sys

from app.analytics import trade_verdict as tv
from app.models.db_models import TradeOutcome

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"PASS  {name}")
    else:
        FAIL += 1; print(f"FAIL  {name}  {detail}")


def row(**kw):
    base = dict(id=1, symbol="TESTUSDT", direction="long", status="closed_loss", entry=100.0, stop_loss=95.0, tp1=105.0, tp2=110.0, tp3=None,
                tp1_hit=False, tp2_hit=False, tp3_hit=False, stop_hit=True, entry_time=1_000_000, exit_time=2_000_000,
                realized_return_pct=-5.0, max_runup_pct=0.2, max_drawdown_pct=-5.0, stop_slippage_pct=-0.1,
                structure_score=12.0, trend_score=22.0, liquidity_score=0.0, entry_indicators={"rsi14": 55, "btc_trend": "bull"})
    base.update(kw)
    return TradeOutcome(**base)


def v(r, outages=None, high=None):
    return tv.primary_verdict(r, outages or [], high)["verdict"]


# ---- losses: each label reachable, priority respected
check("gap-through-stop slippage -> Infrastructure Failure", v(row(stop_slippage_pct=-8.0)) == "Infrastructure Failure")
check("exit inside outage -> Scanner Gap", v(row(), outages=[{"start": 1_500_000, "end": 2_500_000}]) == "Scanner Gap")
check("Infrastructure outranks Scanner Gap", v(row(stop_slippage_pct=-8.0), outages=[{"start": 1_500_000, "end": 2_500_000}]) == "Infrastructure Failure")
check("loss after TP1 -> TP Management Failure", v(row(tp1_hit=True, max_runup_pct=6.0)) == "TP Management Failure")
check("near-miss (MFE>=80% of TP1 dist) -> Good Entry Early Stop", v(row(max_runup_pct=4.5)) == "Good Entry Early Stop")
check("thin liquidity -> Liquidity / Volatility Failure", v(row(liquidity_score=-3.0)) == "Liquidity / Volatility Failure")
check("overbought RSI -> Momentum Exhaustion", v(row(entry_indicators={"rsi14": 78, "btc_trend": "bull"})) == "Momentum Exhaustion")
check("weak structure -> Structure Failure", v(row(structure_score=6.0)) == "Structure Failure")
check("weak trend -> Trend Failure", v(row(trend_score=15.0)) == "Trend Failure")
check("long against a bear BTC trend -> Trend Failure", v(row(entry_indicators={"rsi14": 55, "btc_trend": "bear"})) == "Trend Failure")
check("clean immediate reversal -> Bad Entry", v(row()) == "Bad Entry")
check("Momentum outranks Structure", v(row(structure_score=6.0, entry_indicators={"rsi14": 78, "btc_trend": "bull"})) == "Momentum Exhaustion")
check("Structure outranks Trend", v(row(structure_score=6.0, trend_score=15.0)) == "Structure Failure")
check("loss that reversed after some MFE, no tags -> Unknown or Bad Entry (never a win label)", v(row(max_runup_pct=2.0)) in ("Unknown", "Bad Entry"))

# ---- wins
check("shallow-drawdown win -> Perfect Trade", v(row(status="closed_win", stop_hit=False, tp1_hit=True, realized_return_pct=5.0, max_drawdown_pct=-0.8)) == "Perfect Trade")
check("deep-drawdown win never gets a loss label", v(row(status="closed_win", stop_hit=False, tp1_hit=True, realized_return_pct=5.0, max_drawdown_pct=-6.0, max_runup_pct=8.0)) in ("Unknown", "Good Entry Bad Exit"))

# ---- robustness: missing fields must not crash
sparse = row(entry_indicators=None, structure_score=None, trend_score=None, liquidity_score=None, stop_slippage_pct=None, max_drawdown_pct=None, max_runup_pct=None)
check("sparse row does not raise and returns an allowed verdict", v(sparse) in tv.VERDICTS)
check("every verdict returned is in the fixed taxonomy", all(v(r) in tv.VERDICTS for r in (row(), row(stop_slippage_pct=-9), row(structure_score=5.0), row(tp1_hit=True))))
res = tv.primary_verdict(row(), [], None)
check("result explains itself (rule + traits)", isinstance(res["rule"], str) and "weak_structure" in res["traits"])
check("volatility clause is off when no ATR cutoff is supplied", v(row(stop_slippage_pct=-3.0, entry_indicators={"rsi14": 55, "btc_trend": "bull", "risk_reward": {"risk_to_sl_pct": 9, "entry_to_sl_atr": 1.0}}), high=None) != "Liquidity / Volatility Failure")
check("volatility clause fires for top-tercile ATR% with >=2% slippage", v(row(stop_slippage_pct=-3.0, entry_indicators={"rsi14": 55, "btc_trend": "bull", "risk_reward": {"risk_to_sl_pct": 9, "entry_to_sl_atr": 1.0}}), high=5.0) == "Liquidity / Volatility Failure")

# ---- real DB consistency (read-only)
b = tv.verdict_leaderboard()
check("leaderboard covers every resolved trade exactly once", sum(x["n"] for x in b["verdicts"]) == b["n"] and b["n"] > 0, b["n"])
check("leaderboard lists the full fixed taxonomy", [x["verdict"] for x in b["verdicts"]] == tv.VERDICTS)
check("loss verdicts have 0% win rate; win verdicts 100%", all((x["win_rate_pct"] in (None, 0.0)) for x in b["verdicts"] if x["verdict"] in ("Infrastructure Failure", "Scanner Gap", "Structure Failure", "Bad Entry", "Trend Failure", "TP Management Failure")))
check("base rates reported next to trait-based labels", len(b["base_rates"]) == 3 and "descriptive" in b["note"])
_tot = sum(r.realized_return_pct for r in tv._rows() if r.realized_return_pct is not None)
check("PnL contributions sum to total realized return", abs(sum(x["total_pnl_contribution_pp"] for x in b["verdicts"]) - _tot) < 0.5, (sum(x["total_pnl_contribution_pp"] for x in b["verdicts"]), _tot))
one = tv.verdict_for_trade(next(r.id for r in tv._rows()))
check("verdict_for_trade returns an explained verdict for a real trade", one is not None and one["verdict"] in tv.VERDICTS and one["rule"])
check("unknown / non-resolved id -> None", tv.verdict_for_trade(-1) is None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
