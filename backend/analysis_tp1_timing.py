"""Part 5.5 — TP1 timing analysis. READ ONLY."""
import io, contextlib, statistics
_e = open("analysis_karma_engineering.py", encoding="utf-8").read()
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(_e, "eng", "exec"))
L.clear()
def h(ms): return None if ms is None else ms / 3600000
tp1 = [r for r in ENT if r.tp1_hit and r.tp1_hit_at and r.entry_time]
def t_to_tp1(r): return h(r.tp1_hit_at - r.entry_time)
def t12(r): return h(r.tp2_hit_at - r.tp1_hit_at) if r.tp2_hit_at else None
def t1stop(r): return h(r.exit_time - r.tp1_hit_at) if r.status == "closed_loss" and r.exit_time else None
def q(v, p): return round(float(np.percentile(v, p)), 1) if v else None
def desc(v): return [len(v), q(v, 25), q(v, 50), q(v, 75), q(v, 90), round(max(v), 1) if v else None]
W("# Part 5.5 — TP1 timing analysis"); W()
a = [t_to_tp1(r) for r in tp1 if t_to_tp1(r) is not None and t_to_tp1(r) >= 0]
b = [t12(r) for r in tp1 if t12(r) is not None and t12(r) >= 0]
c = [t1stop(r) for r in tp1 if t1stop(r) is not None and t1stop(r) >= 0]
table(["Interval (hours)", "n", "P25", "median", "P75", "P90", "max"], [["Entry → TP1"] + desc(a), ["TP1 → TP2"] + desc(b), ["TP1 → stop (TP1-then-loss trades)"] + desc(c)])
W(f"TP1-reachers with timestamps: n={len(tp1)} of {sum(1 for r in ENT if r.tp1_hit)}. Times are as recorded by the monitor, so any interval that spans a monitoring gap is stretched (detection delay); the gap-free rows below control for that.")
def gf(r): return gap_free(r)
a2 = [t_to_tp1(r) for r in tp1 if gf(r) and t_to_tp1(r) is not None and t_to_tp1(r) >= 0]; b2 = [t12(r) for r in tp1 if gf(r) and t12(r) is not None]
table(["Gap-free trades only", "n", "P25", "median", "P75", "P90", "max"], [["Entry → TP1"] + desc(a2), ["TP1 → TP2"] + desc(b2)])
med_t = statistics.median(a) if a else None
fast = [r for r in tp1 if t_to_tp1(r) is not None and t_to_tp1(r) <= med_t]; slow = [r for r in tp1 if t_to_tp1(r) is not None and t_to_tp1(r) > med_t]
def cont(rows): return [len(rows), f"{fn(pct(sum(1 for r in rows if r.tp2_hit), len(rows)),1)}%", f"{fn(pct(sum(1 for r in rows if r.tp3_hit), len(rows)),1)}%", f"{fn(pct(sum(1 for r in rows if r.status=='closed_loss'), len(rows)),1)}%", fn(avg([ret(r) for r in rows])), fn(med([ret(r) for r in rows]))]
table([f"Fast (TP1 within median {round(med_t,1)}h) vs slow", "n", "P(TP2)", "P(TP3)", "P(final loss)", "Avg ret%", "Median ret%"], [["Fast TP1"] + cont(fast), ["Slow TP1"] + cont(slow)])
t = two(lambda r: t_to_tp1(r) <= med_t if t_to_tp1(r) is not None else None, tp1)
W(f"Do fast-TP1 trades behave differently? Final-loss rate fast vs slow: OR {t['OR']}, Fisher p={t['p']} (n={t['nP']}/{t['nA']}) → {gate(min(t['nP'], t['nA']), t['p'])}. Correlation between hours-to-TP1 and return: Spearman {round(spearmanr([t_to_tp1(r) for r in tp1 if t_to_tp1(r) is not None],[ret(r) for r in tp1 if t_to_tp1(r) is not None]).statistic,3)}.")
bins = [(0, 1, "<1h"), (1, 6, "1–6h"), (6, 24, "6–24h"), (24, 1e9, ">24h")]
rows = []
for lo, hi, lb in bins:
    sub = [r for r in tp1 if t_to_tp1(r) is not None and lo <= t_to_tp1(r) < hi]
    rows.append([lb] + cont(sub) if sub else [lb, 0, "", "", "", "", ""])
table(["Time to TP1 bucket", "n", "P(TP2)", "P(TP3)", "P(final loss)", "Avg ret%", "Median ret%"], rows)
# trailing-stop timeout: how long after TP1 do TP2 hits arrive; what fraction of eventual TP2 hits arrive within X hours
if b:
    W("**Trailing-stop timeout guidance (from TP1→TP2 times):** share of eventual TP2 hits that arrived within X hours of TP1: " + ", ".join(f"≤{x}h: {fn(pct(sum(1 for v in b if v <= x), len(b)),0)}%" for x in (1, 4, 12, 24, 72)) + f" (n={len(b)}).")
# reversal speed
if c:
    W("**Reversal speed:** among TP1-then-loss trades, time from TP1 to the stop exit: " + ", ".join(f"≤{x}h: {fn(pct(sum(1 for v in c if v <= x), len(c)),0)}%" for x in (1, 4, 12, 24, 72)) + f" (n={len(c)}); {sum(1 for r in tp1 if r.status=='closed_loss' and in_outage(r.exit_time))} of the {len(c)} exited inside a monitoring gap, so these durations are upper bounds.")
W("Any timeout/trail parameter derived here is POSSIBLE at best (n small, intervals gap-stretched); the only shippable outcome is to LOG these timestamps for every TP1 trade (already stored: `tp1_hit_at`, `tp2_hit_at`, plus highest excursion/lowest retrace after TP1 to be added in shadow mode).")
open("karma_part5_5_tp1_timing.md", "w", encoding="utf-8").write("\n".join(L)); print("\n".join(L))
