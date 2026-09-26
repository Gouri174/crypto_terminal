"""Read-only forensic analysis at the 48-resolved-trade mark. No code under
app/ is touched. Run with `python analysis_48trade_forensic.py`."""

import collections
import statistics
import sys

sys.path.insert(0, ".")

from app.db import SessionLocal
from app.models.db_models import TradeOutcome
from sqlalchemy import select

ACTIVATION_MS = 1786342057000  # a69dcb4, see analysis_entry_quality_pre_post.py

session = SessionLocal()
all_rows = session.execute(select(TradeOutcome)).scalars().all()
session.close()

PRE = [r for r in all_rows if r.created_at < ACTIVATION_MS]
POST = [r for r in all_rows if r.created_at >= ACTIVATION_MS]


def entered(rows):
    return [r for r in rows if r.status in ("closed_win", "closed_loss")]


def resolved(rows):
    return [r for r in rows if r.status in ("closed_win", "closed_loss", "closed_stale")]


def wins(rows):
    return [r for r in rows if r.status == "closed_win"]


def losses(rows):
    return [r for r in rows if r.status == "closed_loss"]


def pct(n, d):
    return round(n / d * 100, 1) if d else None


def avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def med(vals):
    vals = [v for v in vals if v is not None]
    return round(statistics.median(vals), 3) if vals else None


def pf(rows):
    rets = [r.realized_return_pct for r in entered(rows) if r.realized_return_pct is not None]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    return round(gains / abs(loss), 3) if loss else None


def group_report(name, rows):
    e = entered(rows)
    r = resolved(rows)
    w, lo = wins(rows), losses(rows)
    print(f"===== {name} =====")
    print(f"n(entered)={len(e)}  resolved(incl stale)={len(r)}  wins={len(w)}  losses={len(lo)}")
    print(f"win rate: {pct(len(w),len(e))}%")
    rets = [x.realized_return_pct for x in e]
    print(f"avg return: {avg(rets)}%   median return: {med(rets)}%   PF: {pf(rows)}")
    def tp_rate(attr):
        return pct(sum(1 for x in e if getattr(x, attr)), len(e))
    print(f"TP1={tp_rate('tp1_hit')}%  TP2={tp_rate('tp2_hit')}%  TP3={tp_rate('tp3_hit')}%")
    l = losses(rows)
    sl_b4_tp1 = pct(sum(1 for x in l if not x.tp1_hit), len(l))
    print(f"SL-before-TP1 (of losses): {sl_b4_tp1}%")
    print(f"avg MFE: {avg([x.max_runup_pct for x in e])}%   avg MAE: {avg([x.max_drawdown_pct for x in e])}%")
    print(f"avg holding time: {avg([x.holding_minutes for x in e])} min")
    longs = [x for x in e if x.direction == "long"]
    shorts = [x for x in e if x.direction == "short"]
    print(f"long: n={len(longs)} win_rate={pct(len(wins(longs)),len(longs))}%   short: n={len(shorts)} win_rate={pct(len(wins(shorts)),len(shorts))}%")
    print(f"regime distribution: {dict(collections.Counter(x.market_regime for x in e))}")
    print()


group_report("PRE_CHANGE", PRE)
group_report("POST_CHANGE", POST)

# ---------------------------------------------------------------------------
# 3. POST outlier sensitivity
# ---------------------------------------------------------------------------
print("===== 3. POST outlier sensitivity =====")
post_e = entered(POST)
sorted_by_ret = sorted(post_e, key=lambda x: x.realized_return_pct)

def report_subset(label, rows):
    rets = [x.realized_return_pct for x in rows]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    pf_ = round(gains / abs(loss), 3) if loss else None
    print(f"{label}: n={len(rows)} win_rate={pct(len(wins(rows)),len(rows))}% avg_return={avg(rets)}% median={med(rets)}% PF={pf_}")

report_subset("ALL POST", post_e)
ace = [x for x in post_e if x.symbol == "ACEUSDT"]
report_subset("excl ACEUSDT", [x for x in post_e if x.symbol != "ACEUSDT"])
top2 = sorted(post_e, key=lambda x: -x.realized_return_pct)[:2]
print(f"  top2 winners: {[(x.symbol, x.realized_return_pct) for x in top2]}")
report_subset("excl top 2 winners", [x for x in post_e if x not in top2])
worst2 = sorted(post_e, key=lambda x: x.realized_return_pct)[:2]
print(f"  worst2 losers: {[(x.symbol, x.realized_return_pct) for x in worst2]}")
report_subset("excl worst 2 losers", [x for x in post_e if x not in worst2])
report_subset("excl top2 winners AND worst2 losers", [x for x in post_e if x not in top2 and x not in worst2])
print()

# ---------------------------------------------------------------------------
# 5. Target progression (conditional)
# ---------------------------------------------------------------------------
print("===== 5. Target progression (POST) =====")
e = post_e
n = len(e)
tp1 = [x for x in e if x.tp1_hit]
tp2 = [x for x in e if x.tp2_hit]
tp3 = [x for x in e if x.tp3_hit]
print(f"n={n}")
print(f"%% reaching TP1: {pct(len(tp1), n)}%")

# Correct conditional-probability form: intersection / condition, not a
# naive len(tp2)/len(tp1) ratio — that assumes every tp2_hit row is also a
# tp1_hit row (TP2 strictly farther than TP1), which does NOT hold in this
# data: one POST trade (SOXSUSDT, short, tp1=39.88 tp2=41.82) has Claude's
# TP1 placed FARTHER from entry than its own TP2, so price crossed TP2
# (the nearer level) without ever crossing TP1 first, giving tp2_hit=True,
# tp1_hit=False. A naive len(tp2)/len(tp1) ratio would read >100% off that
# one row. Flagged here as a genuine data-quality finding, not "fixed" —
# per instructions, no code/threshold change is made for it.
tp1_and_tp2 = [x for x in tp1 if x.tp2_hit]
tp2_and_tp3 = [x for x in tp2 if x.tp3_hit]
print(f"P(TP2 | TP1): {pct(len(tp1_and_tp2), len(tp1))}%   ({len(tp1_and_tp2)} of the {len(tp1)} that reached TP1 also reached TP2)")
print(f"P(TP3 | TP2): {pct(len(tp2_and_tp3), len(tp2))}%   ({len(tp2_and_tp3)} of the {len(tp2)} that reached TP2 also reached TP3)")
anomalies = [x for x in e if x.tp2_hit and not x.tp1_hit]
if anomalies:
    print(f"DATA ANOMALY: {len(anomalies)} trade(s) have tp2_hit=True with tp1_hit=False (TP1/TP2 placed out of order by Claude): {[(x.symbol, x.tp1, x.tp2, x.direction) for x in anomalies]}")
# reversal after TP1: reached TP1 but closed as a loss (i.e. gave it back and stopped out)
tp1_then_loss = [x for x in tp1 if x.status == "closed_loss"]
print(f"P(reversal / closed_loss | reached TP1): {pct(len(tp1_then_loss), len(tp1))}%")
tp2_then_loss = [x for x in tp2 if x.status == "closed_loss"]
print(f"P(reversal / closed_loss | reached TP2): {pct(len(tp2_then_loss), len(tp2))}%")
print()

# ---------------------------------------------------------------------------
# 6. Loss breakdown (POST)
# ---------------------------------------------------------------------------
print("===== 6. Loss breakdown (POST, closed_loss only) =====")
l = losses(POST)
stopped_before_tp1 = [x for x in l if not x.tp1_hit]
reached_tp1_then_stopped = [x for x in l if x.tp1_hit and not x.tp2_hit]
reached_tp2_then_stopped = [x for x in l if x.tp2_hit and not x.tp3_hit]
reached_tp3_loss = [x for x in l if x.tp3_hit]
print(f"total losses: {len(l)}")
print(f"stopped before TP1: {len(stopped_before_tp1)} ({pct(len(stopped_before_tp1), len(l))}%)")
print(f"reached TP1 then stopped (never TP2): {len(reached_tp1_then_stopped)} ({pct(len(reached_tp1_then_stopped), len(l))}%)")
print(f"reached TP2 then stopped (never TP3): {len(reached_tp2_then_stopped)} ({pct(len(reached_tp2_then_stopped), len(l))}%)")
print(f"reached TP3 and still closed_loss: {len(reached_tp3_loss)} ({pct(len(reached_tp3_loss), len(l))}%)")
inval = [x for x in POST if x.status == "invalidated"]
stale = [x for x in POST if x.status == "closed_stale"]
print(f"(separately, POST also has {len(inval)} invalidated and {len(stale)} closed_stale rows — not losses, excluded above)")
print()

# ---------------------------------------------------------------------------
# 7. Confidence calibration (POST)
# ---------------------------------------------------------------------------
print("===== 7. Confidence calibration (POST, entered trades) =====")
buckets = [(50, 60), (60, 70), (70, 80), (80, 101)]
labels = ["50-59", "60-69", "70-79", "80+"]
for (lo, hi), label in zip(buckets, labels):
    b = [x for x in post_e if x.confidence is not None and lo <= x.confidence < hi]
    if not b:
        print(f"{label}: n=0")
        continue
    rets = [x.realized_return_pct for x in b]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    pf_ = round(gains / abs(loss), 3) if loss else None
    print(
        f"{label}: n={len(b)} win_rate={pct(len(wins(b)),len(b))}% avg_return={avg(rets)}% PF={pf_} "
        f"TP1={pct(sum(1 for x in b if x.tp1_hit),len(b))}% TP2={pct(sum(1 for x in b if x.tp2_hit),len(b))}%"
    )
print("NOTE: buckets below n=10 are not treated as evidence of real calibration, per instruction.")
print()

# ---------------------------------------------------------------------------
# 8. entry_quality breakdown (POST)
# ---------------------------------------------------------------------------
print("===== 8. entry_quality breakdown (POST, entered trades) =====")
for cat in ("excellent", "good", "neutral", "late", "exhausted"):
    b = [x for x in post_e if x.entry_quality == cat]
    if not b:
        print(f"{cat}: n=0")
        continue
    rets = [x.realized_return_pct for x in b]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    pf_ = round(gains / abs(loss), 3) if loss else None
    print(
        f"{cat}: n={len(b)} win_rate={pct(len(wins(b)),len(b))}% avg_return={avg(rets)}% PF={pf_} "
        f"TP1={pct(sum(1 for x in b if x.tp1_hit),len(b))}% TP2={pct(sum(1 for x in b if x.tp2_hit),len(b))}% TP3={pct(sum(1 for x in b if x.tp3_hit),len(b))}%"
    )
print()

# ---------------------------------------------------------------------------
# 9. Long vs short (POST)
# ---------------------------------------------------------------------------
print("===== 9. Long vs short (POST, entered trades) =====")
for d in ("long", "short"):
    b = [x for x in post_e if x.direction == d]
    if not b:
        print(f"{d}: n=0")
        continue
    rets = [x.realized_return_pct for x in b]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    pf_ = round(gains / abs(loss), 3) if loss else None
    print(f"{d}: n={len(b)} win_rate={pct(len(wins(b)),len(b))}% avg_return={avg(rets)}% PF={pf_}")
print()

# ---------------------------------------------------------------------------
# 10. Composition check: 28-trade state -> 48-trade state
# ---------------------------------------------------------------------------
print("===== 10. Composition: what changed between the 28-trade and 48-trade snapshots =====")
sorted_post = sorted(post_e, key=lambda x: x.created_at)
first13 = sorted_post[:13]   # the POST group analyzed at the 28-trade mark
new35 = sorted_post[13:]     # everything entered since then
print(f"POST at 28-trade mark: n={len(first13)}")
report_subset("  first 13 (28-trade-mark POST)", first13)
report_subset("  new since then (48-trade-mark delta)", new35)
longs_new = [x for x in new35 if x.direction == "long"]
shorts_new = [x for x in new35 if x.direction == "short"]
print(f"  new-since-then direction mix: long n={len(longs_new)} win_rate={pct(len(wins(longs_new)),len(longs_new))}%   short n={len(shorts_new)} win_rate={pct(len(wins(shorts_new)),len(shorts_new))}%")
print(f"  new-since-then regime: {dict(collections.Counter(x.market_regime for x in new35))}")
print(f"  new-since-then entry_quality: {dict(collections.Counter(x.entry_quality for x in new35))}")
eq_new = collections.Counter(x.entry_quality for x in new35)
for cat, n_ in eq_new.items():
    b = [x for x in new35 if x.entry_quality == cat]
    print(f"    {cat}: n={n_} win_rate={pct(len(wins(b)),len(b))}%")
print()
