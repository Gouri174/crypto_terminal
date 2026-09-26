"""Karma V2.1 Model Improvement Report — READ ONLY. No code, weights,
prompts, models, or DB rows are modified. Computes everything needed for
karma_v2_1_model_improvement_report.md against the live SQLite DB."""

import collections
import math
import statistics
import sys

sys.path.insert(0, ".")

from app.db import SessionLocal
from app.engine import performance_center as pc
from app.models.db_models import ScanSnapshot, TradeOutcome
from sqlalchemy import select

session = SessionLocal()
all_trades = session.execute(select(TradeOutcome)).scalars().all()
session.close()

entered = [r for r in all_trades if r.status in ("closed_win", "closed_loss")]
wins = [r for r in entered if r.status == "closed_win"]
losses = [r for r in entered if r.status == "closed_loss"]
print(f"n={len(entered)} wins={len(wins)} losses={len(losses)}")


def pct(n, d):
    return round(n / d * 100, 1) if d else None


def avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def wilson_ci(successes: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None)
    phat = successes / n
    denom = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    half = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    lo = (center - half) / denom
    hi = (center + half) / denom
    return (round(lo * 100, 1), round(hi * 100, 1))


def odds_ratio(a, b, c, d):
    """a=feature+&win, b=feature+&loss, c=feature-&win, d=feature-&loss"""
    if b == 0 or c == 0:
        b, c = b + 0.5, c + 0.5
        a, d = a + 0.5, d + 0.5
    try:
        return round((a * d) / (b * c), 3)
    except ZeroDivisionError:
        return None


# ===========================================================================
# 1. TP CONTINUATION ENGINE — base + breakdowns + Wilson CIs
# ===========================================================================
print("\n=== 1. TP CONTINUATION ENGINE ===")
base = pc.tp_continuation_analytics()
print("base:", {k: v for k, v in base.items() if k != "per_trade"})

tp1_rows = [r for r in entered if r.tp1_hit]
tp2_rows = [r for r in entered if r.tp2_hit]


def continuation_breakdown(label, group_fn):
    print(f"\n-- by {label} --")
    groups = collections.defaultdict(list)
    for r in entered:
        groups[group_fn(r)].append(r)
    for g, rows in sorted(groups.items(), key=lambda kv: str(kv[0])):
        if not rows or g is None:
            continue
        tp1 = [r for r in rows if r.tp1_hit]
        n_tp1 = len(tp1)
        p_tp1_lo, p_tp1_hi = wilson_ci(n_tp1, len(rows))
        tp1_tp2 = [r for r in tp1 if r.tp2_hit]
        n_tp1_tp2 = len(tp1_tp2)
        p_tp2_lo, p_tp2_hi = wilson_ci(n_tp1_tp2, n_tp1) if n_tp1 else (None, None)
        print(
            f"  {g}: n={len(rows)}  P(TP1)={pct(n_tp1,len(rows))}% [{p_tp1_lo}-{p_tp1_hi}] (n={len(rows)})  "
            f"P(TP2|TP1)={pct(n_tp1_tp2,n_tp1) if n_tp1 else None}% [{p_tp2_lo}-{p_tp2_hi}] (n={n_tp1})"
        )


continuation_breakdown("direction", lambda r: r.direction)
continuation_breakdown("regime", lambda r: r.market_regime)
continuation_breakdown("entry_quality", lambda r: r.entry_quality)
continuation_breakdown("confidence bucket", lambda r: (
    "<55" if r.confidence is None else "<55" if r.confidence < 55 else
    "55-59" if r.confidence < 60 else "60-64" if r.confidence < 65 else
    "65-69" if r.confidence < 70 else "70-74" if r.confidence < 75 else "75+"
))


def atr_percentile_bucket(r):
    rr = (r.entry_indicators or {}).get("risk_reward") or {}
    atr = rr.get("entry_to_sl_atr")
    if atr is None:
        return None
    if atr < 1.0:
        return "p0-33 (<1.0 ATR)"
    if atr < 2.0:
        return "p33-66 (1.0-2.0 ATR)"
    return "p66-100 (>=2.0 ATR)"


continuation_breakdown("ATR-normalized stop distance (proxy for volatility percentile)", atr_percentile_bucket)

# stop-before-tp1 and return-to-entry/stop overall with Wilson CI
n_entered = len(entered)
n_tp1 = len(tp1_rows)
lo, hi = wilson_ci(n_tp1, n_entered)
print(f"\nP(TP1) overall = {pct(n_tp1,n_entered)}% [{lo}-{hi}] n={n_entered}")
stop_before_tp1 = [r for r in entered if r.stop_hit and not r.tp1_hit]
lo, hi = wilson_ci(len(stop_before_tp1), n_entered)
print(f"P(stop before TP1) overall = {pct(len(stop_before_tp1),n_entered)}% [{lo}-{hi}] n={n_entered}")

# ===========================================================================
# 2. FEATURE IMPORTANCE AUDIT — winner freq, loser freq, odds ratio,
#    lift after controlling for entry_quality (stratified)
# ===========================================================================
print("\n=== 2. FEATURE IMPORTANCE AUDIT ===")


def feature_presence(r, name):
    ei = r.entry_indicators or {}
    if name == "trend_high":
        return r.trend_score is not None and r.trend_score >= 22
    if name == "structure_high":
        return r.structure_score is not None and r.structure_score >= 9
    if name == "volume_high":
        return r.volume_score is not None and r.volume_score >= 8
    if name == "funding_high":
        return r.funding_score is not None and r.funding_score >= 8
    if name == "momentum_high":
        return r.momentum_score is not None and r.momentum_score >= 14
    if name == "history_present":
        return r.history_score is not None and r.history_score > 0
    if name == "cmf_positive":
        return (ei.get("cmf") or 0) > 0
    if name == "rsi_healthy_50_70":
        v = ei.get("rsi14")
        return v is not None and 50 <= v < 70
    if name == "adx_trending_20_50":
        v = ei.get("adx14")
        return v is not None and 20 <= v < 50
    if name == "fvg_present":
        return bool(r.level_reasoning and r.level_reasoning.get("fvg_used"))
    if name == "obv":
        return None  # not stored — reported as unavailable
    if name == "bos":
        return None
    if name == "choch":
        return None
    return None


FEATURES = [
    "trend_high", "structure_high", "volume_high", "funding_high", "momentum_high",
    "history_present", "cmf_positive", "rsi_healthy_50_70", "adx_trending_20_50",
    "fvg_present", "obv", "bos", "choch",
]

for feat in FEATURES:
    flags = [feature_presence(r, feat) for r in entered]
    if all(f is None for f in flags):
        print(f"  {feat}: NOT STORED per-trade — unavailable, not computed")
        continue
    present = [r for r, f in zip(entered, flags) if f is True]
    absent = [r for r, f in zip(entered, flags) if f is False]
    if not present or not absent:
        print(f"  {feat}: insufficient variation (present={len(present)}, absent={len(absent)})")
        continue
    win_pres = sum(1 for r in present if r.status == "closed_win")
    win_abs = sum(1 for r in absent if r.status == "closed_win")
    winner_freq = pct(sum(1 for r in wins if feature_presence(r, feat) is True), len(wins))
    loser_freq = pct(sum(1 for r in losses if feature_presence(r, feat) is True), len(losses))
    orat = odds_ratio(win_pres, len(present) - win_pres, win_abs, len(absent) - win_abs)
    # stratify by entry_quality for a crude "controlled" lift
    strat_lifts = []
    for eq in ("excellent", "good", "neutral"):
        p_eq = [r for r in present if r.entry_quality == eq]
        a_eq = [r for r in absent if r.entry_quality == eq]
        if len(p_eq) >= 3 and len(a_eq) >= 3:
            strat_lifts.append(pct(sum(1 for r in p_eq if r.status == "closed_win"), len(p_eq)) - pct(sum(1 for r in a_eq if r.status == "closed_win"), len(a_eq)))
    print(
        f"  {feat}: winner_freq={winner_freq}% loser_freq={loser_freq}% odds_ratio={orat} "
        f"present(n={len(present)})_win_rate={pct(win_pres,len(present))}% absent(n={len(absent)})_win_rate={pct(win_abs,len(absent))}% "
        f"stratified_lift_by_entry_quality={strat_lifts}"
    )

# ===========================================================================
# 3. CONFIDENCE CALIBRATION — reuse pc.confidence_lab, add Wilson CI
# ===========================================================================
print("\n=== 3. CONFIDENCE CALIBRATION ===")
cal = pc.confidence_lab(min_bucket_n=1)
print(f"brier={cal['brier_score']} ece={cal['expected_calibration_error']}")
for b in cal["buckets"]:
    if b["n"] == 0:
        continue
    wins_in_bucket = round(b["actual_win_rate_pct"] / 100 * b["n"])
    lo, hi = wilson_ci(wins_in_bucket, b["n"])
    print(f"  {b['bucket']}: n={b['n']} predicted={b['avg_predicted_confidence']}% actual={b['actual_win_rate_pct']}% [{lo}-{hi}] gap={b['calibration_gap']}")

# ===========================================================================
# 4. EXPECTED VALUE AUDIT
# ===========================================================================
print("\n=== 4. EXPECTED VALUE AUDIT ===")
# Aggregate historical probabilities to use as the "expected reward at
# entry" prior (per-trade priors don't exist — this app doesn't store a
# forward-looking probability per trade beyond ml_probability, which only
# covers 10 trades). Uses the same P(TP1)/P(TP2|TP1)/P(TP3|TP2) figures
# computed in section 1.
P_TP1 = n_tp1 / n_entered
P_TP2_GIVEN_TP1 = base["tp2_probability_given_tp1"] / 100
P_TP3_GIVEN_TP2 = base["tp3_probability_given_tp2"] / 100
P_STOP_BEFORE_TP1 = len(stop_before_tp1) / n_entered
print(f"priors used: P(TP1)={P_TP1:.3f} P(TP2|TP1)={P_TP2_GIVEN_TP1:.3f} P(TP3|TP2)={P_TP3_GIVEN_TP2:.3f} P(stop_before_TP1)={P_STOP_BEFORE_TP1:.3f}")

ev_rows = []
for r in entered:
    ei = r.entry_indicators or {}
    rr = ei.get("risk_reward") or {}
    risk_pct = rr.get("risk_to_sl_pct")
    reward_tp1_pct = rr.get("reward_to_tp1_pct")
    reward_tp2_pct = rr.get("reward_to_tp2_pct")
    if risk_pct is None or risk_pct == 0:
        continue
    realized_r = round(r.realized_return_pct / risk_pct, 3) if r.realized_return_pct is not None else None
    # simple EV: P(TP1)*reward_to_tp1 - P(stop_before_tp1)*risk, in R units
    expected_r = None
    if reward_tp1_pct is not None:
        expected_r = round((P_TP1 * (reward_tp1_pct / risk_pct)) - (P_STOP_BEFORE_TP1 * 1.0), 3)
    ev_rows.append({
        "symbol": r.symbol, "score": r.score, "risk_r": 1.0, "realized_r": realized_r,
        "expected_r_at_entry": expected_r, "status": r.status,
    })

with_ev = [e for e in ev_rows if e["expected_r_at_entry"] is not None and e["realized_r"] is not None]
print(f"trades with computable expected_r: {len(with_ev)} of {len(entered)}")
print(f"avg expected_r_at_entry: {avg([e['expected_r_at_entry'] for e in with_ev])}   avg realized_r: {avg([e['realized_r'] for e in with_ev])}")

# score vs EV disagreement: for each pair, does a lower-score trade have
# higher expected_r? Report correlation + top disagreements.
scores = [e["score"] for e in with_ev]
evs = [e["expected_r_at_entry"] for e in with_ev]
try:
    score_ev_corr = round(statistics.correlation(scores, evs), 3)
except Exception:
    score_ev_corr = None
print(f"corr(score, expected_r_at_entry) = {score_ev_corr}")
top_ev = sorted(with_ev, key=lambda e: -e["expected_r_at_entry"])[:5]
top_score = sorted(with_ev, key=lambda e: -e["score"])[:5]
print("top 5 by EV:", [(e["symbol"], e["score"], e["expected_r_at_entry"]) for e in top_ev])
print("top 5 by score:", [(e["symbol"], e["score"], e["expected_r_at_entry"]) for e in top_score])
disagreements = sum(1 for e in with_ev if e in top_ev and e not in top_score)
print(f"disagreement count (in top-5 EV but not top-5 score): {disagreements}")

# ===========================================================================
# 5. SHORT VS LONG AUDIT — excluding outage-affected trades
# ===========================================================================
print("\n=== 5. SHORT VS LONG AUDIT (excluding outage-affected) ===")
health = pc.scanner_health(gap_threshold_minutes=10)
outages = health.get("outages", [])


def in_outage(exit_time):
    if exit_time is None:
        return False
    return any(o["start"] <= exit_time <= o["end"] for o in outages)


clean = [r for r in entered if not in_outage(r.exit_time)]
print(f"trades excluded as outage-affected: {len(entered) - len(clean)}")

for direction in ("long", "short"):
    sub = [r for r in clean if r.direction == direction]
    w = [r for r in sub if r.status == "closed_win"]
    ei_list = [(r.entry_indicators or {}) for r in sub]
    rr_list = [(ei.get("risk_reward") or {}) for ei in ei_list]
    print(f"\n-- {direction} excl. outages (n={len(sub)}) --")
    print(f"  win_rate={pct(len(w),len(sub))}%  avg_return={avg([r.realized_return_pct for r in sub])}%")
    print(f"  avg_rsi={avg([ei.get('rsi14') for ei in ei_list])}  avg_adx={avg([ei.get('adx14') for ei in ei_list])}")
    print(f"  avg_funding_score={avg([r.funding_score for r in sub])}  avg_structure_score={avg([r.structure_score for r in sub])}")
    print(f"  avg_entry_to_sl_atr={avg([rr.get('entry_to_sl_atr') for rr in rr_list])}  avg_risk_to_sl_pct={avg([rr.get('risk_to_sl_pct') for rr in rr_list])}")
    print(f"  avg_holding_minutes={avg([r.holding_minutes for r in sub])}")

# ===========================================================================
# 6. RED FLAG DISCOVERY
# ===========================================================================
print("\n=== 6. RED FLAG DISCOVERY ===")


def flag_rsi_cmf(r):
    ei = r.entry_indicators or {}
    rsi, cmf = ei.get("rsi14"), ei.get("cmf")
    return rsi is not None and cmf is not None and rsi > 70 and cmf < 0


def flag_bb(r):
    ei = r.entry_indicators or {}
    v = ei.get("bb_pct")
    return v is not None and v > 0.95


def flag_no_structure(r):
    return r.structure_score is not None and r.structure_score < 9


def flag_no_history(r):
    return r.historic_probability is None


def flag_rsi_low_chop(r):
    ei = r.entry_indicators or {}
    v = ei.get("rsi14")
    return v is not None and 30 <= v < 50


RED_FLAGS = {
    "RSI>70 + CMF negative": flag_rsi_cmf,
    "BB%>0.95": flag_bb,
    "structure_score<9 (weak structure)": flag_no_structure,
    "no historical analogue": flag_no_history,
    "RSI 30-49 (chop zone)": flag_rsi_low_chop,
}

for name, fn in RED_FLAGS.items():
    present = [r for r in entered if fn(r)]
    absent = [r for r in entered if not fn(r)]
    if not present:
        print(f"  {name}: n=0 present")
        continue
    print(
        f"  {name}: n={len(present)} loss_rate={pct(len(present)-sum(1 for r in present if r.status=='closed_win'),len(present))}% "
        f"vs baseline_loss_rate(absent)={pct(len(absent)-sum(1 for r in absent if r.status=='closed_win'),len(absent))}%"
    )

print("\nDONE")
