"""Full forensic model redesign analysis — READ ONLY. No code, prompts,
weights, DB rows, or models are modified. Pulls every resolved TradeOutcome
plus PredictionSnapshot/ScanSnapshot context and prints structured data for
building karma_v2_forensic_redesign.md by hand (kept as two separate
artifacts deliberately: this script is the verifiable computation, the .md
is the authored report referencing its exact numbers)."""

import collections
import statistics
import sys

sys.path.insert(0, ".")

from app.db import SessionLocal
from app.engine import performance_center as pc
from app.models.db_models import PredictionSnapshot, ScanSnapshot, TradeOutcome
from sqlalchemy import select

session = SessionLocal()
all_trades = session.execute(select(TradeOutcome)).scalars().all()
all_scans = session.execute(select(ScanSnapshot)).scalars().all()
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


def pf(rows):
    rets = [r.realized_return_pct for r in rows if r.realized_return_pct is not None]
    g = sum(x for x in rets if x > 0)
    l = sum(x for x in rets if x < 0)
    return round(g / abs(l), 3) if l else None


def win_rate(rows):
    if not rows:
        return None
    w = sum(1 for r in rows if r.status == "closed_win")
    return pct(w, len(rows))


def corr(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs2, ys2 = zip(*pairs)
    try:
        return round(statistics.correlation(xs2, ys2), 3)
    except Exception:
        return None


# ===========================================================================
# PART 1 data availability check
# ===========================================================================
print("\n=== DATA AVAILABILITY CHECK ===")
sample = entered[0]
ei = sample.entry_indicators or {}
lr = sample.level_reasoning or {}
print("entry_indicators keys (sample):", list(ei.keys()))
print("level_reasoning keys (sample, may be None on older trades):", list(lr.keys()) if lr else None)
n_with_level_reasoning = sum(1 for r in entered if r.level_reasoning)
print(f"trades WITH level_reasoning (post b208c6f): {n_with_level_reasoning} / {len(entered)}")
n_with_fvg_data = sum(1 for r in entered if r.level_reasoning and r.level_reasoning.get("fvg_used") is not None)
print(f"trades with a recorded fvg_used value: {n_with_fvg_data}")
print("NOTE: no order_block, BOS, or CHoCH boolean is stored per-trade anywhere in this DB —")
print("      structure_score (aggregate 0-15) is the only per-trade structure signal available for ALL 86 trades.")
print("      order-block detection does not exist anywhere in this codebase (confirmed earlier this session).")

# ===========================================================================
# PART 1: MASTER LEDGER (CSV dump for the report table)
# ===========================================================================
print("\n=== MASTER LEDGER (writing CSV) ===")
import csv

with open("scratch_karma_ledger.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([
        "symbol", "direction", "created_at", "entry_time", "exit_time", "holding_minutes",
        "entry", "exit_price", "stop_loss", "tp1", "tp2", "tp3", "exit_reason", "status",
        "realized_return_pct", "max_runup_pct", "max_drawdown_pct", "confidence", "grade",
        "entry_quality", "market_regime", "trend_score", "momentum_score", "volume_score",
        "structure_score", "history_score", "risk_score", "ml_probability", "historic_probability",
        "fear_greed", "funding_score", "rsi14", "stoch_rsi", "adx14", "cmf", "bb_pct",
        "distance_to_ema20_pct", "atr_distance_to_ema20", "entry_to_sl_atr", "fvg_used",
        "tp1_hit", "tp2_hit", "tp3_hit", "stop_hit", "stop_slippage_pct",
    ])
    for r in entered:
        ei = r.entry_indicators or {}
        rr = ei.get("risk_reward") or {}
        lr = r.level_reasoning or {}
        if r.status == "closed_win":
            exit_reason = "target reached"
        elif r.stop_hit:
            exit_reason = "stop hit"
        else:
            exit_reason = "closed at loss (max holding)"
        w.writerow([
            r.symbol, r.direction, r.created_at, r.entry_time, r.exit_time, r.holding_minutes,
            r.entry, r.exit_price, r.stop_loss, r.tp1, r.tp2, r.tp3, exit_reason, r.status,
            r.realized_return_pct, r.max_runup_pct, r.max_drawdown_pct, r.confidence, r.grade,
            r.entry_quality, r.market_regime, r.trend_score, r.momentum_score, r.volume_score,
            r.structure_score, r.history_score, r.risk_score, r.ml_probability, r.historic_probability,
            r.fear_greed, r.funding_score, ei.get("rsi14"), ei.get("stoch_rsi"), ei.get("adx14"),
            ei.get("cmf"), ei.get("bb_pct"), ei.get("distance_to_ema20_pct"), ei.get("atr_distance_to_ema20"),
            rr.get("entry_to_sl_atr"), lr.get("fvg_used"),
            r.tp1_hit, r.tp2_hit, r.tp3_hit, r.stop_hit, r.stop_slippage_pct,
        ])
print("wrote scratch_karma_ledger.csv with", len(entered), "rows")

# ===========================================================================
# PART 2: FEATURE IMPORTANCE
# ===========================================================================
print("\n=== PART 2: FEATURE IMPORTANCE ===")


def bucket_report(name, rows, key_fn, buckets):
    print(f"\n-- {name} --")
    for lo, hi, label in buckets:
        sub = [r for r in rows if (v := key_fn(r)) is not None and lo <= v < hi]
        if not sub:
            print(f"  {label}: n=0")
            continue
        rets = [r.realized_return_pct for r in sub]
        tp2 = sum(1 for r in sub if r.tp2_hit)
        stops = sum(1 for r in sub if r.stop_hit)
        print(f"  {label}: n={len(sub)} win_rate={win_rate(sub)}% avg_return={avg(rets)}% PF={pf(sub)} "
              f"TP2_rate={pct(tp2,len(sub))}% stop_rate={pct(stops,len(sub))}%")


bucket_report("Trend score", entered, lambda r: r.trend_score, [(0, 15, "<15"), (15, 20, "15-19"), (20, 23, "20-22"), (23, 26, "23-25")])
bucket_report("Momentum score", entered, lambda r: r.momentum_score, [(0, 6, "0-5"), (6, 9, "6-8"), (9, 12, "9-11"), (12, 16, "12-15")])
bucket_report("Structure score", entered, lambda r: r.structure_score, [(0, 6, "0-5"), (6, 9, "6-8"), (9, 12, "9-11"), (12, 16, "12-15")])
bucket_report("Volume score", entered, lambda r: r.volume_score, [(0, 4, "0-3"), (4, 7, "4-6"), (7, 10, "7-9"), (10, 11, "10")])
bucket_report("History score", entered, lambda r: r.history_score, [(0, 1, "0 (no history)"), (1, 20, ">0 (has history)")])
bucket_report("Confidence", entered, lambda r: r.confidence, [(0, 55, "<55"), (55, 60, "55-59"), (60, 65, "60-64"), (65, 70, "65-69"), (70, 75, "70-74"), (75, 101, "75+")])
bucket_report("ADX (entry_indicators.adx14)", entered, lambda r: (r.entry_indicators or {}).get("adx14"), [(0, 20, "<20"), (20, 35, "20-34"), (35, 50, "35-49"), (50, 200, "50+")])
bucket_report("RSI (entry_indicators.rsi14)", entered, lambda r: (r.entry_indicators or {}).get("rsi14"), [(0, 30, "<30"), (30, 50, "30-49"), (50, 70, "50-69"), (70, 100, "70+")])
bucket_report("Funding score", entered, lambda r: r.funding_score, [(-20, 0, "<0"), (0, 5, "0-4"), (5, 8, "5-7"), (8, 11, "8-10")])
bucket_report("ML probability", entered, lambda r: r.ml_probability, [(0, 0.4, "<0.4"), (0.4, 0.5, "0.4-0.49"), (0.5, 0.6, "0.5-0.59"), (0.6, 1.01, "0.6+")])

print("\n-- entry_quality --")
for cat in ("excellent", "good", "neutral", "late", "exhausted"):
    sub = [r for r in entered if r.entry_quality == cat]
    if not sub:
        print(f"  {cat}: n=0")
        continue
    print(f"  {cat}: n={len(sub)} win_rate={win_rate(sub)}% avg_return={avg([r.realized_return_pct for r in sub])}% PF={pf(sub)}")

print("\n-- market_regime --")
for regime, sub in sorted(collections.defaultdict(list, {k: [r for r in entered if r.market_regime == k] for k in set(r.market_regime for r in entered)}).items(), key=lambda kv: -len(kv[1])):
    if not sub:
        continue
    print(f"  {regime}: n={len(sub)} win_rate={win_rate(sub)}% avg_return={avg([r.realized_return_pct for r in sub])}% PF={pf(sub)}")

print("\n-- correlations with realized_return_pct --")
rets = [r.realized_return_pct for r in entered]
for label, vals in [
    ("trend_score", [r.trend_score for r in entered]),
    ("momentum_score", [r.momentum_score for r in entered]),
    ("structure_score", [r.structure_score for r in entered]),
    ("volume_score", [r.volume_score for r in entered]),
    ("confidence", [r.confidence for r in entered]),
    ("history_score", [r.history_score for r in entered]),
    ("ml_probability", [r.ml_probability for r in entered]),
    ("adx14", [(r.entry_indicators or {}).get("adx14") for r in entered]),
    ("rsi14", [(r.entry_indicators or {}).get("rsi14") for r in entered]),
    ("atr_distance_to_ema20", [(r.entry_indicators or {}).get("atr_distance_to_ema20") for r in entered]),
]:
    print(f"  corr({label}, return) = {corr(vals, rets)}")

tp2_flags = [1 if r.tp2_hit else 0 for r in entered]
stop_flags = [1 if r.stop_hit else 0 for r in entered]
for label, vals in [
    ("trend_score", [r.trend_score for r in entered]),
    ("momentum_score", [r.momentum_score for r in entered]),
    ("structure_score", [r.structure_score for r in entered]),
    ("confidence", [r.confidence for r in entered]),
]:
    print(f"  corr({label}, tp2_hit) = {corr(vals, tp2_flags)}   corr({label}, stop_hit) = {corr(vals, stop_flags)}")

# ===========================================================================
# PART 3: CONFIDENCE CALIBRATION (40-44 ... 75+, 5-point buckets)
# ===========================================================================
print("\n=== PART 3: CONFIDENCE CALIBRATION ===")
conf_buckets = [(40, 45), (45, 50), (50, 55), (55, 60), (60, 65), (65, 70), (70, 75), (75, 81)]
for lo, hi in conf_buckets:
    sub = [r for r in entered if r.confidence is not None and lo <= r.confidence < hi]
    label = f"{lo}-{hi-1}"
    if not sub:
        print(f"  {label}: n=0")
        continue
    print(
        f"  {label}: n={len(sub)} win_rate={win_rate(sub)}% avg_return={avg([r.realized_return_pct for r in sub])}% "
        f"avg_MFE={avg([r.max_runup_pct for r in sub])}% avg_MAE={avg([r.max_drawdown_pct for r in sub])}% "
        f"TP1={pct(sum(1 for r in sub if r.tp1_hit),len(sub))}% TP2={pct(sum(1 for r in sub if r.tp2_hit),len(sub))}% "
        f"TP3={pct(sum(1 for r in sub if r.tp3_hit),len(sub))}% stop_rate={pct(sum(1 for r in sub if r.stop_hit),len(sub))}%"
    )

# ===========================================================================
# PART 4/5: WHY TRADES LOSE / WIN — rule-based clustering from stored fields
# ===========================================================================
print("\n=== PART 4: LOSS CLUSTERING ===")


def classify_loss(r):
    mfe = r.max_runup_pct or 0
    if not r.tp1_hit:
        if mfe < 1.0:
            return "immediate reversal (never reached TP1, MFE<1%)"
        return "never reached TP1 (some favorable move, no target hit)"
    if r.tp1_hit and not r.tp2_hit:
        return "reached TP1 then stopped"
    if r.tp2_hit and not r.tp3_hit:
        return "hit TP2 then reversed to stop"
    if r.tp3_hit:
        return "hit TP3 then still closed_loss (should not happen — max-holding edge case)"
    return "other/unclassified"


loss_clusters = collections.Counter(classify_loss(r) for r in losses)
for cluster, n in loss_clusters.most_common():
    print(f"  {cluster}: n={n} ({pct(n, len(losses))}%)")

print("\n=== PART 5: WIN CLUSTERING ===")


def classify_win(r):
    if r.tp3_hit:
        return "ran to TP3 (full continuation)"
    if r.tp2_hit:
        return "reached TP2, closed at TP2 (no TP3 defined or not reached)"
    if r.tp1_hit:
        return "closed at TP1 only (TP1 was outermost defined target)"
    return "closed_win without any TP flag set (max-holding edge case)"


win_clusters = collections.Counter(classify_win(r) for r in wins)
for cluster, n in win_clusters.most_common():
    print(f"  {cluster}: n={n} ({pct(n, len(wins))}%)")

print("\n-- winners vs losers: momentum/trend/structure comparison --")
for label, key in [("trend_score", lambda r: r.trend_score), ("momentum_score", lambda r: r.momentum_score),
                    ("structure_score", lambda r: r.structure_score), ("confidence", lambda r: r.confidence),
                    ("adx14", lambda r: (r.entry_indicators or {}).get("adx14")),
                    ("rsi14", lambda r: (r.entry_indicators or {}).get("rsi14")),
                    ("atr_distance_to_ema20", lambda r: (r.entry_indicators or {}).get("atr_distance_to_ema20"))]:
    print(f"  {label}: winners avg={avg([key(r) for r in wins])}  losers avg={avg([key(r) for r in losses])}")

# ===========================================================================
# PART 6: MOMENTUM INVESTIGATION
# ===========================================================================
print("\n=== PART 6: MOMENTUM INVESTIGATION ===")
maxed = [r for r in entered if r.momentum_score is not None and r.momentum_score >= 14]
not_maxed = [r for r in entered if r.momentum_score is not None and r.momentum_score < 14]
print(f"momentum>=14 (near-maxed): n={len(maxed)} win_rate={win_rate(maxed)}% avg_return={avg([r.realized_return_pct for r in maxed])}%")
print(f"momentum<14: n={len(not_maxed)} win_rate={win_rate(not_maxed)}% avg_return={avg([r.realized_return_pct for r in not_maxed])}%")
print(f"maxed avg RSI: {avg([(r.entry_indicators or {}).get('rsi14') for r in maxed])}   not-maxed avg RSI: {avg([(r.entry_indicators or {}).get('rsi14') for r in not_maxed])}")
print(f"maxed avg atr_distance_to_ema20: {avg([(r.entry_indicators or {}).get('atr_distance_to_ema20') for r in maxed])}   not-maxed: {avg([(r.entry_indicators or {}).get('atr_distance_to_ema20') for r in not_maxed])}")
print(f"maxed avg stoch_rsi: {avg([(r.entry_indicators or {}).get('stoch_rsi') for r in maxed])}   not-maxed: {avg([(r.entry_indicators or {}).get('stoch_rsi') for r in not_maxed])}")

# ===========================================================================
# PART 7: TREND INVESTIGATION
# ===========================================================================
print("\n=== PART 7: TREND INVESTIGATION ===")
for lo, hi, label in [(0, 18, "<18"), (18, 22, "18-21"), (22, 24, "22-23"), (24, 26, "24-25 (near max)")]:
    sub = [r for r in entered if r.trend_score is not None and lo <= r.trend_score < hi]
    print(f"  trend {label}: n={len(sub)} win_rate={win_rate(sub)}% avg_return={avg([r.realized_return_pct for r in sub])}% PF={pf(sub)}")

# ===========================================================================
# PART 8: STRUCTURE (BOS/CHoCH/FVG) — limited data
# ===========================================================================
print("\n=== PART 8: STRUCTURE (FVG only — BOS/CHoCH/OB not stored per-trade) ===")
with_fvg = [r for r in entered if r.level_reasoning and r.level_reasoning.get("fvg_used")]
without_fvg_data = [r for r in entered if not (r.level_reasoning and r.level_reasoning.get("fvg_used") is not None)]
print(f"trades with a recorded active FVG at entry: n={len(with_fvg)} win_rate={win_rate(with_fvg)}%")
print(f"trades WITHOUT fvg data recorded (pre-capture or no FVG active): n={len(without_fvg_data)} win_rate={win_rate(without_fvg_data)}%")
print("BOS/CHoCH/order-block presence: NOT reconstructable per-trade for historical rows — not computed, not fabricated.")

# ===========================================================================
# PART 9/10: TP BEHAVIOUR — reuse the already-built, tested engine function
# ===========================================================================
print("\n=== PART 9/10: TP CONTINUATION (via performance_center.tp_continuation_analytics) ===")
tp = pc.tp_continuation_analytics()
print({k: v for k, v in tp.items() if k != "per_trade"})

# ===========================================================================
# PART 11: LONG VS SHORT DEEP AUDIT
# ===========================================================================
print("\n=== PART 11: LONG VS SHORT ===")
for direction in ("long", "short"):
    sub = [r for r in entered if r.direction == direction]
    w = [r for r in sub if r.status == "closed_win"]
    l = [r for r in sub if r.status == "closed_loss"]
    print(f"\n-- {direction} (n={len(sub)}) --")
    print(f"  win_rate={win_rate(sub)}% PF={pf(sub)} avg_return={avg([r.realized_return_pct for r in sub])}%")
    print(f"  winners n={len(w)} avg_trend={avg([r.trend_score for r in w])} avg_momentum={avg([r.momentum_score for r in w])} avg_structure={avg([r.structure_score for r in w])} avg_conf={avg([r.confidence for r in w])}")
    print(f"  losers  n={len(l)} avg_trend={avg([r.trend_score for r in l])} avg_momentum={avg([r.momentum_score for r in l])} avg_structure={avg([r.structure_score for r in l])} avg_conf={avg([r.confidence for r in l])}")
    print(f"  avg RSI: {avg([(r.entry_indicators or {}).get('rsi14') for r in sub])}   avg ADX: {avg([(r.entry_indicators or {}).get('adx14') for r in sub])}")

# ===========================================================================
# PART 12: COIN FAMILY AUDIT
# ===========================================================================
print("\n=== PART 12: COIN FAMILY AUDIT ===")
FAMILIES = {
    "majors": {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"},
    "ai_coins": {"NEARUSDT", "WLDUSDT", "HYPEUSDT"},
    "meme_coins": {"DOGEUSDT", "1000PEPEUSDT", "PUMPUSDT"},
    "gold": {"XAUUSDT", "PAXGUSDT", "XAGUSDT"},
    "stocks_etfs": {"NVDAUSDT", "MSTRUSDT", "QQQUSDT", "CRCLUSDT", "SPCXUSDT", "SAMSUNGUSDT", "SOXLUSDT", "SNDKUSDT", "KORUUSDT", "SOXSUSDT", "SKHYNIXUSDT", "SKHYUSDT", "NBISUSDT"},
}


def classify_family(symbol):
    for fam, syms in FAMILIES.items():
        if symbol in syms:
            return fam
    return "defi_other_altcoin"


by_family = collections.defaultdict(list)
for r in entered:
    by_family[classify_family(r.symbol)].append(r)
for fam, sub in sorted(by_family.items(), key=lambda kv: -len(kv[1])):
    print(f"  {fam}: n={len(sub)} win_rate={win_rate(sub)}% avg_return={avg([r.realized_return_pct for r in sub])}% PF={pf(sub)}")

# ===========================================================================
# PART 13: MARKET REGIME AUDIT — indicator behavior split by regime
# ===========================================================================
print("\n=== PART 13: REGIME x FEATURE INTERACTION ===")
for regime in set(r.market_regime for r in entered if r.market_regime):
    sub = [r for r in entered if r.market_regime == regime]
    print(f"\n-- {regime} (n={len(sub)}) --")
    print(f"  corr(trend_score,return)={corr([r.trend_score for r in sub], [r.realized_return_pct for r in sub])}")
    print(f"  corr(momentum_score,return)={corr([r.momentum_score for r in sub], [r.realized_return_pct for r in sub])}")
    print(f"  corr(confidence,return)={corr([r.confidence for r in sub], [r.realized_return_pct for r in sub])}")

# ===========================================================================
# PART 15: HISTORICAL SIMILARITY AUDIT
# ===========================================================================
print("\n=== PART 15: HISTORICAL SIMILARITY ===")
has_hist = [r for r in entered if r.historic_probability is not None]
no_hist = [r for r in entered if r.historic_probability is None]
print(f"coins WITH history: n={len(has_hist)} ({pct(len(has_hist), len(entered))}%) win_rate={win_rate(has_hist)}%")
print(f"coins WITHOUT history: n={len(no_hist)} ({pct(len(no_hist), len(entered))}%) win_rate={win_rate(no_hist)}%")
print(f"distinct symbols with history ever: {len(set(r.symbol for r in has_hist))}  distinct symbols total: {len(set(r.symbol for r in entered))}")

# ===========================================================================
# PART 16: ML MODEL AUDIT (per-trade ml_probability vs outcome)
# ===========================================================================
print("\n=== PART 16: ML MODEL AUDIT (per-trade ml_probability) ===")
has_ml = [r for r in entered if r.ml_probability is not None]
print(f"trades with stored ml_probability: n={len(has_ml)} of {len(entered)}")
if has_ml:
    probs = [r.ml_probability for r in has_ml]
    outcomes = [1 if r.status == "closed_win" else 0 for r in has_ml]
    brier = round(sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(has_ml), 4)
    print(f"  Brier score: {brier}")
    for lo, hi, label in [(0, 0.45, "<0.45"), (0.45, 0.5, "0.45-0.49"), (0.5, 0.55, "0.5-0.54"), (0.55, 1.01, "0.55+")]:
        sub = [r for r in has_ml if lo <= r.ml_probability < hi]
        if sub:
            print(f"  predicted {label}: n={len(sub)} actual_win_rate={win_rate(sub)}%")

# ===========================================================================
# PART 17: SCANNER REJECTION AUDIT
# ===========================================================================
print("\n=== PART 17: SCANNER REJECTION AUDIT ===")
rejected = [s for s in all_scans if s.rejection_reason is not None]
print(f"total ScanSnapshot rows: {len(all_scans)}  rejected: {len(rejected)}")
reason_counts = collections.Counter(s.rejection_reason for s in rejected)
for reason, n in reason_counts.most_common(6):
    print(f"  {n:6d}  {reason}")
print("NOTE: no forward-price tracking exists for rejected candidates anywhere in this DB —")
print("      'did rejected trades outperform accepted ones' is NOT computable from stored data.")

print("\nDONE")
