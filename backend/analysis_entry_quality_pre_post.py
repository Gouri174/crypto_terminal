"""Read-only PRE vs POST entry_quality analysis. No code under app/ is
touched. Run with `python analysis_entry_quality_pre_post.py`."""

import statistics
import sys

sys.path.insert(0, ".")

from app.db import SessionLocal
from app.models.db_models import TradeOutcome
from sqlalchemy import select

# a69dcb4f57a37ffab8d2961fa3c97003fe2117cb — "Add entry-quality diagnostic
# layer" — the commit that actually WIRES classify_entry_quality() into
# reasoning.py:_precompute() (exhausted->no_trade override) and
# background_scanner.py's needs_llm gate (late->withhold new plan). Commit
# timestamp (git show -s --format=%at), not a separate deploy log — this is
# a local dev app with no deploy pipeline, so the commit time is the best
# available proxy for "when this code started running," with the caveat
# that --reload means the running process only actually picked it up the
# next time the dev server (re)started after this commit, which could lag
# the commit itself by an unknown amount.
ACTIVATION_MS = 1786342057000

session = SessionLocal()
all_rows = session.execute(select(TradeOutcome)).scalars().all()
session.close()

# "signal/entry was generated" -> split on created_at (when Claude issued
# the plan), not entry_time (when price later crossed into the zone) and
# not exit_time. A trade created pre-activation that happens to enter or
# resolve post-activation is still governed by whatever the engine was at
# the moment the LEVELS were generated, so it stays in PRE.
PRE = [r for r in all_rows if r.created_at < ACTIVATION_MS]
POST = [r for r in all_rows if r.created_at >= ACTIVATION_MS]

print(f"Activation timestamp (a69dcb4): {ACTIVATION_MS} ms")
print(f"Total TradeOutcome rows: {len(all_rows)}  (PRE={len(PRE)}, POST={len(POST)})")
print()


def resolved(rows):
    return [r for r in rows if r.status in ("closed_win", "closed_loss", "closed_stale")]


def entered(rows):
    # closed_stale = NEVER ENTERED (expired while still pending) — has no
    # realized_return_pct, no entry_time, no MFE/MAE. Return/holding-time/
    # TP-hit stats must exclude it or they'd silently average in zeros/Nones.
    return [r for r in rows if r.status in ("closed_win", "closed_loss")]


def wins(rows):
    return [r for r in rows if r.status == "closed_win"]


def losses(rows):
    return [r for r in rows if r.status == "closed_loss"]


def stale(rows):
    return [r for r in rows if r.status == "closed_stale"]


def pct(n, d):
    return round(n / d * 100, 1) if d else None


def avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def med(vals):
    vals = [v for v in vals if v is not None]
    return round(statistics.median(vals), 3) if vals else None


def profit_factor(rows):
    rets = [r.realized_return_pct for r in entered(rows) if r.realized_return_pct is not None]
    gains = sum(r for r in rets if r > 0)
    loss = sum(r for r in rets if r < 0)
    if loss == 0:
        return None
    return round(gains / abs(loss), 3)


def tp_rate(rows, attr):
    e = entered(rows)
    return pct(sum(1 for r in e if getattr(r, attr)), len(e))


def sl_before_tp1_rate(rows):
    l = losses(rows)
    if not l:
        return None
    return pct(sum(1 for r in l if not r.tp1_hit), len(l))


def group_report(name, rows):
    e = entered(rows)
    r = resolved(rows)
    w, lo, st = wins(rows), losses(rows), stale(rows)
    print(f"===== {name} =====")
    print(f"resolved (win+loss+stale): {len(r)}   entered (win+loss): {len(e)}")
    print(f"wins: {len(w)}   losses: {len(lo)}   stale/never-entered: {len(st)}")
    print(f"win rate (wins/entered): {pct(len(w), len(e))}%")
    print(f"win rate (wins/resolved incl. stale): {pct(len(w), len(r))}%")
    rets = [x.realized_return_pct for x in e]
    print(f"average return: {avg(rets)}%   median return: {med(rets)}%")
    print(f"profit factor: {profit_factor(rows)}")
    print(f"TP1 hit rate: {tp_rate(rows,'tp1_hit')}%   TP2 hit rate: {tp_rate(rows,'tp2_hit')}%   TP3 hit rate: {tp_rate(rows,'tp3_hit')}%")
    print(f"SL-before-TP1 rate (of losses): {sl_before_tp1_rate(rows)}%")
    print(f"avg MFE (max_runup_pct): {avg([x.max_runup_pct for x in e])}%   avg MAE (max_drawdown_pct): {avg([x.max_drawdown_pct for x in e])}%")
    print(f"avg holding time: {avg([x.holding_minutes for x in e])} min")

    longs = [x for x in e if x.direction == "long"]
    shorts = [x for x in e if x.direction == "short"]
    print(f"direction: long n={len(longs)} win_rate={pct(len(wins(longs)),len(longs))}%   short n={len(shorts)} win_rate={pct(len(wins(shorts)),len(shorts))}%")

    print("confidence distribution (entered trades):")
    buckets = [(0, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 101)]
    for lo_b, hi_b in buckets:
        b = [x for x in e if x.confidence is not None and lo_b <= x.confidence < hi_b]
        if b:
            print(f"  {lo_b}-{hi_b}: n={len(b)} win_rate={pct(len(wins(b)),len(b))}%")

    print("grade distribution (entered trades):")
    import collections
    gc = collections.Counter(x.grade for x in e)
    for grade, n in sorted(gc.items(), key=lambda kv: str(kv[0])):
        gb = [x for x in e if x.grade == grade]
        print(f"  {grade}: n={n} win_rate={pct(len(wins(gb)),len(gb))}%")

    print("entry_quality distribution (entered trades):")
    eqc = collections.Counter(x.entry_quality for x in e)
    for eq, n in sorted(eqc.items(), key=lambda kv: str(kv[0])):
        print(f"  {eq}: n={n}")
    print()


group_report("PRE_CHANGE", PRE)
group_report("POST_CHANGE", POST)

# ---------------------------------------------------------------------------
# 4. POST_CHANGE by entry_quality category
# ---------------------------------------------------------------------------
print("===== POST_CHANGE by entry_quality category =====")
for cat in ("excellent", "good", "neutral", "late", "exhausted"):
    sub = [r for r in POST if r.entry_quality == cat]
    e = entered(sub)
    if not e:
        print(f"{cat}: n=0 (no TradeOutcome rows exist at this classification — see note below)")
        continue
    rets = [x.realized_return_pct for x in e]
    print(
        f"{cat}: n={len(e)} win_rate={pct(len(wins(sub)),len(e))}% "
        f"TP1={tp_rate(sub,'tp1_hit')}% TP2={tp_rate(sub,'tp2_hit')}% TP3={tp_rate(sub,'tp3_hit')}% "
        f"avg_return={avg(rets)}% avg_MFE={avg([x.max_runup_pct for x in e])}% avg_MAE={avg([x.max_drawdown_pct for x in e])}%"
    )
print(
    "\nNOTE: 'late' and 'exhausted' show n=0 by construction, not by chance. "
    "reasoning.py:_precompute() forces direction='no_trade' whenever "
    "entry_quality=='exhausted' (so open_trade_outcome() no-ops — it only "
    "records long/short recommendations), and background_scanner.py forces "
    "needs_llm=False whenever entry_quality=='late' (so Claude is never "
    "called and no plan/TradeOutcome is ever created that cycle). Both gates "
    "run BEFORE a trade can be opened, so there is no post-hoc TradeOutcome "
    "data for what a late/exhausted trade would have done — only the "
    "counterfactual visible in ScanSnapshot.rejection_reason (a separate "
    "table, not analyzed here). This is confirmed directly from the code, "
    "not inferred from the data being empty.\n"
)

# ---------------------------------------------------------------------------
# 8. POST_CHANGE excluding the single best trade
# ---------------------------------------------------------------------------
print("===== POST_CHANGE: overall vs excluding best trade =====")
post_entered = entered(POST)
if post_entered:
    best = max(post_entered, key=lambda x: x.realized_return_pct or -999)
    print(f"best trade: {best.symbol} realized_return_pct={best.realized_return_pct}%  created_at={best.created_at}")
    rest = [x for x in post_entered if x.id != best.id]
    rest_rets = [x.realized_return_pct for x in rest]
    all_rets = [x.realized_return_pct for x in post_entered]
    print(f"overall: n={len(post_entered)} win_rate={pct(len(wins(post_entered)),len(post_entered))}% avg_return={avg(all_rets)}% PF={profit_factor(POST)}%")
    gains = sum(r for r in rest_rets if r > 0)
    loss = sum(r for r in rest_rets if r < 0)
    pf_excl = round(gains / abs(loss), 3) if loss else None
    print(f"excl. best: n={len(rest)} win_rate={pct(len(wins(rest)),len(rest))}% avg_return={avg(rest_rets)}% PF={pf_excl}%")
print()

# ---------------------------------------------------------------------------
# 9. Matched-N: last N PRE resolved trades vs first N POST resolved trades
# ---------------------------------------------------------------------------
print("===== Matched N: last N PRE-entered trades vs first N POST-entered trades =====")
pre_entered_sorted = sorted(entered(PRE), key=lambda x: x.created_at)
post_entered_sorted = sorted(entered(POST), key=lambda x: x.created_at)
N = min(len(pre_entered_sorted), len(post_entered_sorted))
print(f"N = min({len(pre_entered_sorted)} PRE-entered, {len(post_entered_sorted)} POST-entered) = {N}")
if N > 0:
    last_pre_N = pre_entered_sorted[-N:]
    first_post_N = post_entered_sorted[:N]

    def mini_report(label, rows):
        rets = [x.realized_return_pct for x in rows]
        print(
            f"{label}: n={len(rows)} win_rate={pct(len(wins(rows)),len(rows))}% "
            f"avg_return={avg(rets)}% median_return={med(rets)}% "
            f"TP1={pct(sum(1 for r in rows if r.tp1_hit),len(rows))}%"
        )

    mini_report("last N PRE", last_pre_N)
    mini_report("first N POST", first_post_N)
else:
    print("N=0 — one side has zero entered trades, no comparison possible.")
print()

# ---------------------------------------------------------------------------
# 7. Confound check: symbols, regime, direction mix, confidence mix, volume
# ---------------------------------------------------------------------------
print("===== Confound check: PRE vs POST composition =====")
import collections
pre_e, post_e = entered(PRE), entered(POST)
print(f"distinct symbols traded: PRE={len(set(x.symbol for x in pre_e))}  POST={len(set(x.symbol for x in post_e))}")
overlap = set(x.symbol for x in pre_e) & set(x.symbol for x in post_e)
print(f"symbol overlap between groups: {len(overlap)} symbols in both")
print(f"short-trade share: PRE={pct(sum(1 for x in pre_e if x.direction=='short'),len(pre_e))}%  POST={pct(sum(1 for x in post_e if x.direction=='short'),len(post_e))}%")
print(f"avg confidence: PRE={avg([x.confidence for x in pre_e])}  POST={avg([x.confidence for x in post_e])}")
print(f"regime distribution PRE: {dict(collections.Counter(x.market_regime for x in pre_e))}")
print(f"regime distribution POST: {dict(collections.Counter(x.market_regime for x in post_e))}")
print(f"trade volume (entered/day): PRE spans {(max(x.created_at for x in PRE)-min(x.created_at for x in PRE))/86400000:.1f} days, {len(pre_e)} entered -> {len(pre_e)/max((max(x.created_at for x in PRE)-min(x.created_at for x in PRE))/86400000,0.01):.2f}/day" if PRE else "PRE empty")
if POST:
    span_days = (max(x.created_at for x in POST) - min(x.created_at for x in POST)) / 86400000
    print(f"POST spans {span_days:.1f} days, {len(post_e)} entered -> {len(post_e)/max(span_days,0.01):.2f}/day")
