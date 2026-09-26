"""Performance Center V1 — read-only forensic analysis. No code, weights,
prompts, models, or DB rows are modified. Run with
`python analysis_performance_center_v1.py`."""

import collections
import statistics
import sys

sys.path.insert(0, ".")

from app.db import SessionLocal
from app.models.db_models import OHLCVCandle, PredictionSnapshot, ScanSnapshot, TradeOutcome
from sqlalchemy import select

session = SessionLocal()
all_trades = session.execute(select(TradeOutcome)).scalars().all()
all_snapshots = session.execute(select(PredictionSnapshot)).scalars().all()
all_scans = session.execute(select(ScanSnapshot)).scalars().all()
candle_symbols = set(session.execute(select(OHLCVCandle.symbol).distinct()).scalars().all())
session.close()

snaps_by_trade = collections.defaultdict(list)
for s in all_snapshots:
    snaps_by_trade[s.trade_outcome_id].append(s)
for tid in snaps_by_trade:
    snaps_by_trade[tid].sort(key=lambda s: s.timestamp)

entered = [r for r in all_trades if r.status in ("closed_win", "closed_loss")]
wins = [r for r in entered if r.status == "closed_win"]
losses = [r for r in entered if r.status == "closed_loss"]


def pct(n, d):
    return round(n / d * 100, 1) if d else None


def avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def med(vals):
    vals = [v for v in vals if v is not None]
    return round(statistics.median(vals), 3) if vals else None


def pf(rows):
    rets = [r.realized_return_pct for r in rows if r.realized_return_pct is not None]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    return round(gains / abs(loss), 3) if loss else None


print(f"Universe: {len(all_trades)} TradeOutcome rows, {len(entered)} entered (wins={len(wins)}, losses={len(losses)}), "
      f"{len(all_snapshots)} PredictionSnapshot rows, {len(all_scans)} ScanSnapshot rows")
print(f"OHLCV candle coverage: {sorted(candle_symbols)} (4h interval only)")
print()

# ===========================================================================
# 1. STOP EXECUTION AUDIT
# ===========================================================================
print("=" * 70)
print("1. STOP EXECUTION AUDIT")
print("=" * 70)

stop_hit_trades = [r for r in entered if r.stop_hit]
print(f"trades with stop_hit=True: {len(stop_hit_trades)}  (closed_loss total: {len(losses)})")
has_slippage = [r for r in stop_hit_trades if r.stop_slippage_pct is not None]
no_slippage = [r for r in stop_hit_trades if r.stop_slippage_pct is None]
print(f"stop_slippage_pct recorded: {len(has_slippage)}   NOT recorded (pre-V1.1-instrumentation trades, exit_price never captured): {len(no_slippage)}")
if no_slippage:
    print(f"  pre-instrumentation symbols: {[r.symbol for r in no_slippage]}")
print()

slips = [r.stop_slippage_pct for r in has_slippage]
print(f"ALL stop-hit slippage: n={len(slips)} mean={avg(slips)}% median={med(slips)}% worst={round(min(slips),3) if slips else None}% best={round(max(slips),3) if slips else None}%")

long_slip = [r.stop_slippage_pct for r in has_slippage if r.direction == "long"]
short_slip = [r.stop_slippage_pct for r in has_slippage if r.direction == "short"]
print(f"LONG stop slippage: n={len(long_slip)} mean={avg(long_slip)}% median={med(long_slip)}%")
print(f"SHORT stop slippage: n={len(short_slip)} mean={avg(short_slip)}% median={med(short_slip)}%")
print()

print("Full stop-hit ledger (symbol, direction, stop_loss, exit_price, slippage%, exit_time):")
for r in sorted(has_slippage, key=lambda r: r.stop_slippage_pct):
    print(f"  {r.symbol:15s} {r.direction:5s} stop={r.stop_loss:<12} exit={r.exit_price:<12} slippage={r.stop_slippage_pct:>8}%  exit_time={r.exit_time}")
print()

# Clustering by exit_time within a 2-hour window
print("Clusters of stop-hit events within 2 hours of each other:")
CLUSTER_WINDOW_MS = 2 * 3_600_000
ordered = sorted([r for r in has_slippage if r.exit_time], key=lambda r: r.exit_time)
clusters = []
current_cluster = []
for r in ordered:
    if current_cluster and r.exit_time - current_cluster[0].exit_time > CLUSTER_WINDOW_MS:
        clusters.append(current_cluster)
        current_cluster = []
    current_cluster.append(r)
if current_cluster:
    clusters.append(current_cluster)
multi_clusters = [c for c in clusters if len(c) > 1]
if multi_clusters:
    for c in multi_clusters:
        print(f"  cluster of {len(c)}: {[(r.symbol, r.direction, r.stop_slippage_pct, r.exit_time) for r in c]}")
else:
    print("  none found (no two stop-hit events fell within the same 2h window)")
print()

# Theoretical stop fill via candle high/low, for symbols with OHLCV coverage
print("Theoretical stop-fill check (candle high/low, only for symbols with OHLCV coverage):")
covered = [r for r in has_slippage if r.symbol in candle_symbols]
if not covered:
    print(f"  none of the {len(has_slippage)} stop-hit trades with recorded slippage involve a candle-covered symbol "
          f"({sorted(candle_symbols)}) — no theoretical-fill comparison is possible for this dataset.")
else:
    for r in covered:
        print(f"  {r.symbol} {r.direction} stop={r.stop_loss} exit={r.exit_price} slippage={r.stop_slippage_pct}% — see manual candle check")
print()

print("Flagged: trades where slippage magnitude suggests scanner-latency amplification (|slippage| > 5%, using the ALREADY-RECORDED value, no new threshold introduced into production code):")
flagged = [r for r in has_slippage if abs(r.stop_slippage_pct) > 5]
for r in sorted(flagged, key=lambda r: r.stop_slippage_pct):
    print(f"  {r.symbol} {r.direction} slippage={r.stop_slippage_pct}% exit_time={r.exit_time}")
print()

# Root-cause check: is there an app-wide monitoring gap (scanner not
# running) around each flagged trade's exit_time? Uses ALL PredictionSnapshot
# timestamps (not just this trade's own) to distinguish "the whole app was
# offline" from "this one trade's price moved fast between normal cycles."
all_snap_ts = sorted(set(s.timestamp for s in all_snapshots))
print("App-wide PredictionSnapshot monitoring gaps (>1 hour between ANY two consecutive snapshot timestamps, across the whole app):")
gaps = []
for a, b in zip(all_snap_ts, all_snap_ts[1:]):
    if b - a > 3_600_000:
        gaps.append((a, b, b - a))
for a, b, g in gaps:
    print(f"  gap: {a} -> {b}  ({g/3600000:.2f} hours)")
print(f"  total gaps > 1h: {len(gaps)}")
print()
print("Cross-referencing flagged high-slippage trades against these monitoring gaps:")
for r in sorted(flagged, key=lambda r: r.stop_slippage_pct):
    covering_gap = next((g for g in gaps if g[0] <= r.exit_time <= g[1]), None)
    if covering_gap:
        print(f"  {r.symbol} ({r.stop_slippage_pct}% slippage) exit_time={r.exit_time} falls INSIDE a {covering_gap[2]/3600000:.2f}h monitoring gap ({covering_gap[0]} -> {covering_gap[1]})")
    else:
        print(f"  {r.symbol} ({r.stop_slippage_pct}% slippage) — no app-wide gap covers this exit_time")
print()

# ===========================================================================
# 2. TP CONTINUATION ANALYSIS
# ===========================================================================
print("=" * 70)
print("2. TP CONTINUATION ANALYSIS")
print("=" * 70)

tp1_trades = [r for r in entered if r.tp1_hit]
tp1_and_tp2 = [r for r in tp1_trades if r.tp2_hit]
tp2_trades = [r for r in entered if r.tp2_hit]
tp2_and_tp3 = [r for r in tp2_trades if r.tp3_hit]

print(f"trades that hit TP1: {len(tp1_trades)} of {len(entered)} ({pct(len(tp1_trades), len(entered))}%)")
print(f"P(TP2 | TP1) = {pct(len(tp1_and_tp2), len(tp1_trades))}%  ({len(tp1_and_tp2)}/{len(tp1_trades)})")
print(f"P(TP3 | TP2) = {pct(len(tp2_and_tp3), len(tp2_trades))}%  ({len(tp2_and_tp3)}/{len(tp2_trades)})")
anomalies = [r for r in entered if r.tp2_hit and not r.tp1_hit]
if anomalies:
    print(f"DATA ANOMALY (TP1/TP2 placed out of order): {[(r.symbol, r.tp1, r.tp2, r.direction) for r in anomalies]}")
print()


def post_tp1_path(row):
    """Uses PredictionSnapshot rows after tp1_hit_at to answer: did price
    return to entry, did it return to stop, and what were the best/worst
    excursions relative to entry AFTER TP1 was reached. Snapshot-cadence
    resolution (whatever the scanner's interval is), not tick-level."""
    snaps = snaps_by_trade.get(row.id, [])
    if not row.tp1_hit_at:
        return None
    after = [s for s in snaps if s.timestamp >= row.tp1_hit_at]
    if not after:
        return {"returned_to_entry": None, "returned_to_stop": None, "mfe_after_tp1": None, "mae_after_tp1": None, "n_snapshots_after": 0}
    is_long = row.direction == "long"
    sign = 1 if is_long else -1
    # NOTE: current_pnl_pct is hardcoded to 0.0 by record_snapshot() for any
    # snapshot where status != "open" (i.e. the closing snapshot itself) —
    # see trade_outcomes.py: "pnl_pct = ... if row.status == 'open' else
    # 0.0". Checking "current_pnl_pct <= 0" would therefore read 0.0 as
    # "returned to entry" on EVERY trade's final snapshot regardless of its
    # real exit price, producing a false 100% rate. Comparing current_price
    # to row.entry directly avoids this.
    is_long_ = row.direction == "long"
    open_prices = [s.current_price for s in after if s.current_price is not None and s.status == "open"]
    if not open_prices:
        returned_to_entry = None
    elif is_long_:
        returned_to_entry = any(p <= row.entry for p in open_prices)
    else:
        returned_to_entry = any(p >= row.entry for p in open_prices)
    # NOTE: distance_to_stop_pct = (stop_loss - price)/price*100*sign is
    # NEGATIVE during normal healthy operation for a long (price above
    # stop) and POSITIVE only once price actually crosses the stop — the
    # opposite sign convention from distance_to_tp*_pct. An earlier version
    # of this script checked "<= 0" (borrowed from the TP-distance
    # convention) which is trivially true almost immediately and produced
    # a false 100% "returned to stop" rate for every trade. Fixed to
    # compare current_price directly against row.stop_loss instead.
    is_long = row.direction == "long"
    prices_only = [s.current_price for s in after if s.current_price is not None]
    if is_long:
        returned_to_stop = any(p <= row.stop_loss for p in prices_only) if prices_only else None
    else:
        returned_to_stop = any(p >= row.stop_loss for p in prices_only) if prices_only else None
    prices = [(s.current_price, s.timestamp) for s in after]
    excursions = [round((p - row.entry) / row.entry * 100 * sign, 3) for p, _ in prices]
    mfe_after = max(excursions) if excursions else None
    mae_after = min(excursions) if excursions else None
    return {
        "returned_to_entry": returned_to_entry, "returned_to_stop": returned_to_stop,
        "mfe_after_tp1": mfe_after, "mae_after_tp1": mae_after, "n_snapshots_after": len(after),
    }


print("Per-trade continuation detail (trades that hit TP1):")
have_path = 0
entry_determined, entry_true = 0, 0
stop_determined, stop_true = 0, 0
mfe_afters, mae_afters = [], []
for r in tp1_trades:
    path = post_tp1_path(r)
    if path is None:
        continue
    have_path += 1
    if path["returned_to_entry"] is not None:
        entry_determined += 1
        if path["returned_to_entry"]:
            entry_true += 1
    if path["returned_to_stop"] is not None:
        stop_determined += 1
        if path["returned_to_stop"]:
            stop_true += 1
    if path["mfe_after_tp1"] is not None:
        mfe_afters.append(path["mfe_after_tp1"])
    if path["mae_after_tp1"] is not None:
        mae_afters.append(path["mae_after_tp1"])
    print(f"  {r.symbol:15s} status={r.status:12s} tp2={r.tp2_hit!s:5s} tp3={r.tp3_hit!s:5s} "
          f"returned_to_entry={path['returned_to_entry']!s:5s} returned_to_stop={path['returned_to_stop']!s:5s} "
          f"mfe_after_tp1={path['mfe_after_tp1']}% mae_after_tp1={path['mae_after_tp1']}% (n_snaps={path['n_snapshots_after']})")

print()
print(f"of {have_path} TP1 trades with any post-TP1 snapshot:")
print(f"  returned to entry after TP1: {entry_true}/{entry_determined} determinable ({pct(entry_true, entry_determined)}%) — "
      f"{have_path - entry_determined} trades had only the single closing snapshot (status already != 'open'), so this can't be determined for them")
print(f"  returned to stop after TP1: {stop_true}/{stop_determined} determinable ({pct(stop_true, stop_determined)}%)")
print(f"  avg MFE after TP1: {avg(mfe_afters)}%   avg MAE after TP1: {avg(mae_afters)}%")
print()

# ===========================================================================
# 3. CONFIDENCE CALIBRATION
# ===========================================================================
print("=" * 70)
print("3. CONFIDENCE CALIBRATION")
print("=" * 70)
buckets = [(50, 55), (55, 60), (60, 65), (65, 70), (70, 75), (75, 101)]
labels = ["50-54", "55-59", "60-64", "65-69", "70-74", "75+"]
for (lo, hi), label in zip(buckets, labels):
    b = [r for r in entered if r.confidence is not None and lo <= r.confidence < hi]
    if not b:
        print(f"{label}: n=0")
        continue
    bw = [r for r in b if r.status == "closed_win"]
    rets = [r.realized_return_pct for r in b]
    print(
        f"{label}: n={len(b)} wins={len(bw)} win_rate={pct(len(bw),len(b))}% avg_return={avg(rets)}% "
        f"PF={pf(b)} avg_MFE={avg([r.max_runup_pct for r in b])}% avg_MAE={avg([r.max_drawdown_pct for r in b])}%"
    )
below_50 = [r for r in entered if r.confidence is not None and r.confidence < 50]
if below_50:
    bw = [r for r in below_50 if r.status == "closed_win"]
    print(f"(below 50, outside requested buckets): n={len(below_50)} win_rate={pct(len(bw),len(below_50))}%")
print()

# ===========================================================================
# 4. COIN LEADERBOARD
# ===========================================================================
print("=" * 70)
print("4. COIN LEADERBOARD (symbols with >= 3 entered trades)")
print("=" * 70)
by_symbol = collections.defaultdict(list)
for r in entered:
    by_symbol[r.symbol].append(r)

coin_rows = []
for symbol, rows in by_symbol.items():
    if len(rows) < 3:
        continue
    w = [r for r in rows if r.status == "closed_win"]
    rets = [r.realized_return_pct for r in rows]
    coin_rows.append({
        "symbol": symbol, "n": len(rows), "win_rate": pct(len(w), len(rows)),
        "avg_return": avg(rets), "pf": pf(rows),
        "tp1_rate": pct(sum(1 for r in rows if r.tp1_hit), len(rows)),
        "stop_rate": pct(sum(1 for r in rows if r.stop_hit), len(rows)),
        "avg_confidence": avg([r.confidence for r in rows]),
        "avg_hold_min": avg([r.holding_minutes for r in rows]),
    })
coin_rows.sort(key=lambda c: c["avg_return"] if c["avg_return"] is not None else -999, reverse=True)
print(f"{len(coin_rows)} symbols qualify (n>=3). Ranked by avg_return, best to worst:")
for c in coin_rows:
    print(f"  {c['symbol']:15s} n={c['n']:3d} win_rate={c['win_rate']}% avg_return={c['avg_return']}% PF={c['pf']} "
          f"TP1={c['tp1_rate']}% stop_rate={c['stop_rate']}% avg_conf={c['avg_confidence']} avg_hold={c['avg_hold_min']}min")
print()

# ===========================================================================
# 5. REGIME LEADERBOARD
# ===========================================================================
print("=" * 70)
print("5. REGIME LEADERBOARD")
print("=" * 70)
by_regime = collections.defaultdict(list)
for r in entered:
    by_regime[r.market_regime or "unknown"].append(r)
for regime, rows in sorted(by_regime.items(), key=lambda kv: -len(kv[1])):
    w = [r for r in rows if r.status == "closed_win"]
    rets = [r.realized_return_pct for r in rows]
    print(
        f"{regime:12s}: n={len(rows)} win_rate={pct(len(w),len(rows))}% avg_return={avg(rets)}% PF={pf(rows)} "
        f"avg_MFE={avg([r.max_runup_pct for r in rows])}% avg_MAE={avg([r.max_drawdown_pct for r in rows])}%"
    )
print()

# ===========================================================================
# 6. ENTRY QUALITY AUDIT
# ===========================================================================
print("=" * 70)
print("6. ENTRY QUALITY AUDIT")
print("=" * 70)
for cat in ("excellent", "good", "neutral", "late", "exhausted"):
    b = [r for r in entered if r.entry_quality == cat]
    if not b:
        print(f"{cat}: n=0")
        continue
    w = [r for r in b if r.status == "closed_win"]
    rets = [r.realized_return_pct for r in b]
    print(
        f"{cat}: n={len(b)} win_rate={pct(len(w),len(b))}% "
        f"TP1={pct(sum(1 for r in b if r.tp1_hit),len(b))}% TP2={pct(sum(1 for r in b if r.tp2_hit),len(b))}% TP3={pct(sum(1 for r in b if r.tp3_hit),len(b))}% "
        f"avg_return={avg(rets)}% avg_hold={avg([r.holding_minutes for r in b])}min"
    )
print(
    "\nNOTE: late/exhausted show n=0 by construction — confirmed from the code (reasoning.py forces "
    "no_trade on exhausted; background_scanner.py forces needs_llm=False on late), not from data sparsity.\n"
)

print("Rejected ScanSnapshot opportunities (candidates NEVER given a TradeOutcome row):")
rejected = [s for s in all_scans if s.rejection_reason is not None]
print(f"total ScanSnapshot rows: {len(all_scans)}   rejected (non-null rejection_reason): {len(rejected)}")
reason_counts = collections.Counter(s.rejection_reason for s in rejected)
for reason, n in reason_counts.most_common(15):
    print(f"  {n:5d}  {reason}")
late_or_exhausted = [s for s in all_scans if s.entry_quality in ("late", "exhausted")]
print(f"\nScanSnapshot rows classified late/exhausted: {len(late_or_exhausted)} of {len(all_scans)}")
if late_or_exhausted:
    print(f"  avg score_total: {avg([s.score_total for s in late_or_exhausted])}")
    print(f"  avg confidence (where computed): {avg([s.confidence for s in late_or_exhausted])}")
    eq_dist = collections.Counter(s.entry_quality for s in late_or_exhausted)
    print(f"  breakdown: {dict(eq_dist)}")
    top_symbols = collections.Counter(s.symbol for s in late_or_exhausted).most_common(10)
    print(f"  most frequently rejected symbols: {top_symbols}")
print(
    "\nLIMITATION (honest, not fixable without new code): this codebase has NO forward-price tracking "
    "for REJECTED candidates — only accepted TradeOutcome rows get PredictionSnapshot history. There is "
    "no stored data anywhere that shows what a late/exhausted candidate's price actually did afterward. "
    "This section can report WHAT got rejected and HOW OFTEN, but cannot answer whether those rejections "
    "were correct calls without a new (not-yet-built) forward-tracking mechanism.\n"
)

# ===========================================================================
# 7. DIRECTION AUDIT
# ===========================================================================
print("=" * 70)
print("7. DIRECTION AUDIT")
print("=" * 70)
for d in ("long", "short"):
    rows = [r for r in entered if r.direction == d]
    w = [r for r in rows if r.status == "closed_win"]
    slip = [r.stop_slippage_pct for r in rows if r.stop_slippage_pct is not None]
    print(
        f"{d}: n={len(rows)} win_rate={pct(len(w),len(rows))}% PF={pf(rows)} "
        f"avg_stop_slippage={avg(slip)}% avg_trend_score={avg([r.trend_score for r in rows])} "
        f"avg_risk_score={avg([r.risk_score for r in rows])} avg_confidence={avg([r.confidence for r in rows])}"
    )
print()
print("Per instruction: re-checking SHORT after removing CLUSTERED slippage events (from section 1's >1-trade clusters):")
clustered_ids = {r.id for c in multi_clusters for r in c}
shorts = [r for r in entered if r.direction == "short"]
shorts_excl_clustered = [r for r in shorts if r.id not in clustered_ids]
w_all = [r for r in shorts if r.status == "closed_win"]
w_excl = [r for r in shorts_excl_clustered if r.status == "closed_win"]
print(f"  short, ALL: n={len(shorts)} win_rate={pct(len(w_all),len(shorts))}% avg_return={avg([r.realized_return_pct for r in shorts])}% PF={pf(shorts)}")
print(f"  short, EXCLUDING clustered-slippage trades ({len(clustered_ids)} flagged): n={len(shorts_excl_clustered)} "
      f"win_rate={pct(len(w_excl),len(shorts_excl_clustered))}% avg_return={avg([r.realized_return_pct for r in shorts_excl_clustered])}% PF={pf(shorts_excl_clustered)}")
print()

# ===========================================================================
# 8. BIGGEST WINNERS AND LOSERS
# ===========================================================================
print("=" * 70)
print("8. BIGGEST WINNERS AND LOSERS (top 10 each)")
print("=" * 70)


def describe(r, label):
    print(f"--- {label}: {r.symbol} ({r.realized_return_pct}%) ---")
    print(f"  direction={r.direction}  entry={r.entry}  exit={r.exit_price}  stop={r.stop_loss}")
    print(f"  confidence={r.confidence}  grade={r.grade}  entry_quality={r.entry_quality}")
    print(f"  trend_score={r.trend_score}  momentum_score={r.momentum_score}  structure_score={r.structure_score}  risk_score={r.risk_score}")
    print(f"  regime={r.market_regime}  MFE={r.max_runup_pct}%  MAE={r.max_drawdown_pct}%")
    print(f"  key_score_component={r.key_score_component}  explanation_mentioned_key_factor={r.explanation_mentioned_key_factor}")
    print(f"  reasoning (why Claude entered): {(r.reasoning or '')[:220]}")
    print(f"  reasons_for: {r.reasons_for}")
    print(f"  reasons_against: {r.reasons_against}")
    print()


top_winners = sorted(wins, key=lambda r: -r.realized_return_pct)[:10]
top_losers = sorted(losses, key=lambda r: r.realized_return_pct)[:10]
print(f"\n### TOP {len(top_winners)} WINNERS ###\n")
for r in top_winners:
    describe(r, "WINNER")
print(f"\n### TOP {len(top_losers)} LOSERS ###\n")
for r in top_losers:
    describe(r, "LOSER")
