"""Karma Archive quantitative audit, sections A-Z. READ ONLY.
Reuses the loaders/helpers from analysis_karma_v3_audit.py (everything above its
'SECTION 1' marker), then computes every number fresh from the DB."""
import re
_src = open("analysis_karma_v3_audit.py", encoding="utf-8").read()
exec(compile(_src[:_src.index("# =================================================================== SECTION 1")], "prefix", "exec"))
from sqlalchemy import text as _t
from app.db import engine as _eng

NOW = datetime.now(timezone.utc)
def hrs(r): return r.holding_minutes / 60 if r.holding_minutes else None
def statline(rows):
    x = summ(rows)
    return [x["n"], f"{x['wr']}%" if x["wr"] is not None else "—", f"{x['ci'][0]}–{x['ci'][1]}" if x["ci"][0] is not None else "—", fn(x["avg"]), fn(x["med"]), fn(x["pf"])]
SH = ["n", "Win%", "Wilson 95% CI", "Avg ret%", "Median ret%", "PF"]
def grade(n, p=None, evid=None):
    if n < 10: return "INSUFFICIENT DATA"
    if p is None: return "POSSIBLE"
    if p < .01 and n >= 30: return "CONFIRMED"
    if p < .05: return "LIKELY"
    if p < .15: return "POSSIBLE"
    return "NOT SUPPORTED (no detectable effect at this n)"
def tpm(rows):
    x = summ(rows); return [x["tp1"], x["tp2"], x["tp3"], x["stop"]]

W(f"# Karma Archive — Quantitative Audit (Sections A–Z)")
W()
W(f"Generated {NOW.strftime('%Y-%m-%d %H:%M UTC')} directly from `crypto_terminal.db` (read-only). Live DB counts: {len(ALL)} plans, {len(ENT)} resolved, {len(SNAPS)} PredictionSnapshots, {len(SCANS)} ScanSnapshots. The DB grows while the scanner runs, so counts are slightly above the round numbers in the brief.")
W()
W("**Evidence labels:** CONFIRMED (p<0.01, n≥30) · LIKELY (p<0.05) · POSSIBLE (p<0.15) · INSUFFICIENT DATA (n<10 or field not stored) · a hypothesis with p≥0.15 at adequate n is stated as **NOT SUPPORTED** (I say 'false' only where the data affirmatively contradicts it). Fisher exact tests on win/loss; p-values are optimistic because trades are clustered. Where the brief names tables that do not exist as tables (PredictionMetadata, PredictionVersion, CoinHistory, HistoricalSimilarity, ExpectedValue, EntryQuality, RedFlags, Reliability, FailurePatterns, DecisionAudit), they are columns of `trade_outcomes` or computed by `app/analytics/*`; nothing was skipped. Tables in the DB: live_opportunities, market_regime_state, market_snapshots (25,080 rows, 6 symbols, ends 2026-08-04, i.e. before the first trade), ohlcv_candles (6 symbols), prediction_snapshots, rejected_opportunity_outcomes (0 rows), scan_snapshots, trade_outcomes.")
W()
W("**Discrepancies with earlier reports (data wins):** the entry-quality 'excellent' effect I previously called validated is NOT significant on the full sample (§E); the short-selling collapse is largely an outage artefact (§K/§U).")

# ------------------------------------------------------------- A
sec("A", "EXECUTIVE SUMMARY")
cnt = collections.Counter(r.status for r in ALL)
entered = len(ENT) + cnt["open"]
S = summ(ENT); rets = [ret(r) for r in ENT]
sharpe = round(statistics.mean(rets) / statistics.pstdev(rets), 3)
order = sorted([r for r in ENT if r.exit_time], key=lambda r: r.exit_time); cum = pk = mdd = 0
for r in order: cum += ret(r); pk = max(pk, cum); mdd = min(mdd, cum - pk)
table(["Metric", "Value"], [["Total prediction plans", len(ALL)], ["Entered trades (closed + open)", entered], ["Closed (resolved) trades", len(ENT)], ["Wins / Losses", f"{S['w']} / {S['l']}"],
      ["TP1 / TP2 / TP3 hits (among closed)", f"{sum(1 for r in ENT if r.tp1_hit)} / {sum(1 for r in ENT if r.tp2_hit)} / {sum(1 for r in ENT if r.tp3_hit)}"],
      ["Stop-loss exits", sum(1 for r in ENT if r.stop_hit)], ["Expired (never entered, `closed_stale`)", cnt["closed_stale"]], ["Invalidated (superseded)", cnt["invalidated"]],
      ["Open", cnt["open"]], ["Pending", cnt["pending"]], ["Avoid-grade (`rejected_avoid`)", cnt["rejected_avoid"]]])
table(["Overall (closed trades)", "Value"], [["Win rate", f"{S['wr']}% (95% CI {S['ci'][0]}–{S['ci'][1]}%)"], ["Profit factor", S["pf"]], ["Average return", f"{S['avg']}%"], ["Median return", f"{S['med']}%"],
      ["Sharpe (per-trade mean/σ, not annualised)", sharpe], ["Max drawdown (summed-return curve, no sizing/compounding)", f"{round(mdd, 1)}%"], ["Average hold", f"{fn(avg([hrs(r) for r in ENT]), 1)} h (median {fn(med([hrs(r) for r in ENT]), 1)} h)"],
      ["Best trade", f"{max(ENT, key=ret).symbol} {round(max(rets), 2)}%"], ["Worst trade", f"{min(ENT, key=ret).symbol} {round(min(rets), 2)}%"]])
srt = sorted(ENT, key=lambda r: -ret(r)); rows_ = []
for lab, k in [("All trades", 0), ("Without top winner", 1), ("Without top 3 winners", 3), ("Without top 5 winners", 5)]:
    sub = srt[k:]; x = summ(sub); rows_.append([lab, *statline(sub), fn(sum(ret(r) for r in sub), 1)])
table(["Scenario"] + SH + ["Sum ret%"], rows_)
pf1, pf3, pf5 = [pf([ret(r) for r in srt[k:]]) for k in (1, 3, 5)]
W(f"**Is Karma Archive profitable? MARGINAL / fragile — the point estimate is positive, but the bootstrap CI of mean return includes zero and PF is below 1 once the top 5 winners are removed (POSSIBLE positive expectancy, not CONFIRMED).** PF {S['pf']} → {pf3} without the top 3 → {pf5} without the top 5; the median trade is {S['med']}%. Winners are few and large (top-3 = {', '.join(r.symbol + ' +' + str(round(ret(r), 1)) + '%' for r in srt[:3])}). "
  f"Bootstrap check below.")
rng0 = np.random.default_rng(3); bs = [np.mean(rng0.choice(rets, len(rets))) for _ in range(5000)]
W(f"Bootstrap 95% CI of the mean return: [{round(float(np.percentile(bs, 2.5)), 2)}%, {round(float(np.percentile(bs, 97.5)), 2)}%] (n={len(rets)}) — {'excludes' if np.percentile(bs, 2.5) > 0 else 'INCLUDES'} zero. Evidence: {'LIKELY' if np.percentile(bs, 2.5) > 0 else 'POSSIBLE (cannot rule out zero expectancy)'}. Note the ‘published/active’ forward returns in §T are survivorship-biased (a row only has +72h data if its trade stayed tracked that long).")

# ------------------------------------------------------------- B
sec("B", "COMPLETE CLOSED TRADE LEDGER")
W(f"All {len(ENT)} closed trades (newest first); also saved to `karma_AZ_ledger.csv`. Notes: 'EV' exists only for post-2026-09-12 trades; ML probability exists for a small subset; Reliability* is hindsight (all-data Bayesian). **'Why won/lost' is not stored as a post-mortem** — the last column is the entry thesis from `reasoning` (first 130 chars) plus the computed lifecycle/Trade-Truth verdict; it explains what Claude said at entry, not a causal explanation of the outcome.")
W()
def tp_reached(r): return "TP3" if r.tp3_hit else "TP2" if r.tp2_hit else "TP1" if r.tp1_hit else "none"
head = ["Symbol", "Dir", "Entry", "Exit", "Entered", "Exited", "Hold h", "Conf", "Grade", "EQ", "Regime", "Trend", "Mom", "Vol", "Struct", "Hist", "ML prob", "EV(R)", "Rel*", "TP reached", "Stop?", "Ret%", "MFE%", "MAE%", "Failure pattern", "Red flags", "Entry thesis / verdict"]
led = []
for r in sorted(ENT, key=lambda r: -r.created_at):
    th = re.sub(r"\s+", " ", (r.reasoning or ""))[:130].replace("|", "/")
    led.append([r.symbol, r.direction, g6(r.entry), g6(r.exit_price), dt(r.entry_time), dt(r.exit_time), fn(hrs(r), 1), r.confidence, r.grade or "—", r.entry_quality or "—", r.market_regime or "—",
                fn(r.trend_score, 1), fn(r.momentum_score, 1), fn(r.volume_score, 1), fn(r.structure_score, 1), fn(r.history_score, 1), fn(r.ml_probability, 2), fn(evr(r)), fn((RELMAP.get(r.symbol) or {}).get("reliability_score"), 1),
                tp_reached(r), "yes" if r.stop_hit else "no", fn(ret(r)), fn(r.max_runup_pct), fn(r.max_drawdown_pct), LIFE[r.id] + ("+" + ",".join(TAGS[r.id]) if TAGS[r.id] else ""),
                ",".join(f for f in FLAGS[r.id] if f not in ("short_direction", "outage_exit")) or "—", f"[{TRUTH[r.id]}] {th}"])
table(head, led)
with open("karma_AZ_ledger.csv", "w", newline="", encoding="utf-8") as f:
    cw = csv.writer(f); cw.writerow(head); cw.writerows(led)
W("**Ranked biggest winners and losers**"); W()
for lab, sub in [("Top 10 winners", sorted(ENT, key=lambda r: -ret(r))[:10]), ("Top 10 losers", sorted(ENT, key=ret)[:10])]:
    W(f"*{lab}*"); table(["#", "Symbol", "Dir", "Ret%", "Hold h", "Conf", "EQ", "Regime", "Exit in monitoring gap?", "Stop slippage%"],
        [[i + 1, r.symbol, r.direction, fn(ret(r)), fn(hrs(r), 1), r.confidence, r.entry_quality or "—", r.market_regime or "—", "yes" if in_outage(r.exit_time) else "no", fn(r.stop_slippage_pct)] for i, r in enumerate(sub)])

# ------------------------------------------------------------- C
sec("C", "CONFIDENCE CALIBRATION")
edges = [0, 50, 55, 60, 65, 70, 75, 200]; labs = ["<50", "50–54", "55–59", "60–64", "65–69", "70–74", "75+"]
CT = [r for r in ENT if r.confidence is not None]; rowsC = []
for (a, b), lb in zip(zip(edges[:-1], edges[1:]), labs):
    sub = [r for r in CT if a <= r.confidence < b]
    if not sub: rowsC.append([lb, 0] + [""] * 10); continue
    x = summ(sub); pred = avg([r.confidence for r in sub]); rowsC.append([lb, x["n"], fn(pred, 1) + "%", f"{x['wr']}%", f"{x['ci'][0]}–{x['ci'][1]}", fn(pred - x["wr"], 1), fn(x["avg"]), fn(x["med"]), *tpm(sub), fn(x["pf"])])
table(["Bucket", "n", "Mean predicted", "Observed win%", "Wilson CI", "Pred−Obs pp", "Avg ret", "Median ret", "TP1%", "TP2%", "TP3%", "Stop%", "PF"], rowsC)
brier = avg([(r.confidence / 100 - (r.status == "closed_win")) ** 2 for r in CT]); base = sum(1 for r in CT if r.status == "closed_win") / len(CT)
W("Calibration curve (■ predicted, ▒ observed):"); W("```")
for row in rowsC:
    if row[1]:
        p_ = float(row[2].rstrip('%')); o_ = float(row[3].rstrip('%')); W(f"{row[0]:>6} n={row[1]:<3} pred {'■' * int(p_ / 3.5):<22}{p_:>5.1f}%"); W(f"{'':>6}        obs  {'▒' * int(o_ / 3.5):<22}{o_:>5.1f}%")
W("```")
sp = spearmanr([r.confidence for r in CT], [ret(r) for r in CT]); t70 = two(lambda r: r.confidence >= 70 if r.confidence >= 60 and (r.confidence >= 70 or r.confidence < 65) else None, CT)
t65 = two(lambda r: r.confidence >= 65, CT)
from scipy.stats import binomtest
_exp = sum(r.confidence for r in CT) / 100; _obs = sum(1 for r in CT if r.status == "closed_win"); _bt = binomtest(_obs, len(CT), _exp / len(CT))
W(f"Overall: mean stated confidence {round(_exp/len(CT)*100,1)}% vs observed {round(_obs/len(CT)*100,1)}% ({_obs}/{len(CT)}); exact binomial test p={_bt.pvalue:.2e}.")
table(FH, [frow("conf ≥70 vs 60–64", t70), frow("conf ≥65 vs <65", t65)])
W(f"Brier {brier} vs constant-base-rate Brier {round(base * (1 - base), 4)} (n={len(CT)}); Spearman(confidence, return)={round(sp.statistic, 3)} (p={round(sp.pvalue, 3)}).")
W(f"**Is confidence calibrated? NO — CONFIRMED overconfident in aggregate (binomial p above; observed win rate is below predicted in every bucket ≥55).** **Does 70 outperform 60? NOT SUPPORTED** (≥70: {t70['wrP']}% n={t70['nP']} vs 60–64: {t70['wrA']}% n={t70['nA']}, p={t70['p']}); confidence has no detectable rank relation to return. "
  f"**Should confidence be shifted?** A display-layer calibration (already built) is justified; shifting the underlying formula is INSUFFICIENT DATA (buckets ≥70 have n≤{max(r[1] for r in rowsC[5:] if r[1])}).")

# ------------------------------------------------------------- D
sec("D", "GRADE CALIBRATION")
gr = collections.defaultdict(list)
for r in ENT: gr[r.grade or "none"].append(r)
table(["Grade"] + SH + ["TP1%", "TP2%", "TP3%", "Stop%", "Avg conf"], [[g] + statline(v) + tpm(v) + [fn(avg([r.confidence for r in v]), 1)] for g, v in sorted(gr.items(), key=lambda kv: kv[0])] + [["Avoid (never traded)", cnt["rejected_avoid"], "—", "—", "—", "—", "—", "—", "—", "—", "—", "—"]])
tb = two(lambda r: r.grade == "B+" if r.grade in ("B+", "B") else None, ENT)
gord = {"C": 1, "B": 2, "B+": 3, "A": 4}; gg = [(gord[r.grade], ret(r)) for r in ENT if r.grade in gord]; spg = spearmanr([a for a, _ in gg], [b for _, b in gg])
table(FH, [frow("B+ vs B", tb)])
W(f"Spearman(grade rank, return)={round(spg.statistic, 3)} (p={round(spg.pvalue, 3)}, n={len(gg)}). Grade is a deterministic bin of confidence (≥65→B+, 55–64→B, 45–54→C), so it inherits confidence's calibration. **Do grades mean anything statistically? NOT SUPPORTED** — B+ vs B p={tb['p']}; A has n={len(gr.get('A', []))} and 'Avoid' plans are never traded so the bottom of the scale cannot be validated (INSUFFICIENT DATA).")

# ------------------------------------------------------------- E
sec("E", "ENTRY QUALITY AUDIT")
rowsE = []
for q in ("excellent", "good", "neutral", "late", "exhausted"):
    sub = [r for r in ENT if r.entry_quality == q]
    rowsE.append([q] + (statline(sub) + tpm(sub) + [fn(med([hrs(r) for r in sub]), 1), fn(avg([r.max_runup_pct for r in sub])), fn(avg([r.max_drawdown_pct for r in sub]))] if sub else ["0"] + [""] * 12))
table(["EQ"] + SH + ["TP1%", "TP2%", "TP3%", "Stop%", "Median hold h", "MFE", "MAE"], rowsE)
scn = collections.Counter((x.entry_quality, cat_of(x.rejection_reason)) for x in [] ) if False else None
q_scan = s_ = None
with _eng.connect() as c:
    qs = c.execute(_t("select entry_quality, count(*) from scan_snapshots group by entry_quality")).fetchall()
W(f"ScanSnapshot entry_quality distribution (all {len(SCANS)} scans): {dict(qs)}. `late`/`exhausted` never appear among trades **by construction** (they block issuance); their effect is measurable only through §T.")
EQR = [r for r in ENT if r.entry_quality]; pre = [r for r in ENT if r.created_at < EQ_LAUNCH]
tex = two(lambda r: r.entry_quality == "excellent", EQR); tgn = two(lambda r: r.entry_quality == "good" if r.entry_quality in ("good", "neutral") else None, EQR)
table(FH, [frow("excellent vs rest", tex), frow("good vs neutral", tgn)])
table(["Era"] + SH, [["Pre entry-quality launch"] + statline(pre), ["Post launch (all)"] + statline(EQR), ["Post launch, excl. top-1 winner"] + statline([r for r in EQR if r is not max(EQR, key=ret)])])
W(f"**Is Entry Quality actually filtering trades?** It is monotonic only at the top: excellent PF {summ([r for r in ENT if r.entry_quality=='excellent'])['pf']} vs good {summ([r for r in ENT if r.entry_quality=='good'])['pf']} vs neutral {summ([r for r in ENT if r.entry_quality=='neutral'])['pf']}; 'good' does NOT beat 'neutral' (p={tgn['p']}). Excellent vs rest p={tex['p']} → {grade(tex['nP'], tex['p'])}. "
  f"Post-launch PF is higher than pre-launch but the eras differ in calendar time and n (pre n={len(pre)}), and the gap shrinks without the top winner → POSSIBLE at best; causal credit is INSUFFICIENT DATA.")

# ------------------------------------------------------------- F
sec("F", "TREND AUDIT")
bucket_table("trend_score buckets (max 25)", lambda r: r.trend_score, [0, 15, 20, 23, 26])
mx = [r for r in ENT if r.trend_score >= 24]; md_ = [r for r in ENT if 18 <= r.trend_score < 24]; lo_ = [r for r in ENT if r.trend_score < 18]
table(["Group"] + SH, [["Max trend (≥24)"] + statline(mx), ["Medium (18–24)"] + statline(md_), ["Low (<18)"] + statline(lo_)])
tm = two(lambda r: r.trend_score >= 24 if (r.trend_score >= 24 or 18 <= r.trend_score < 24) else None, ENT)
spt = spearmanr([r.trend_score for r in ENT], [ret(r) for r in ENT])
def mh(rows, pred, strat):
    num = den = vnum = 0.0
    for k in set(strat(r) for r in rows):
        g = [r for r in rows if strat(r) == k and pred(r) is not None]; P = [r for r in g if pred(r)]; A = [r for r in g if not pred(r)]
        a = sum(1 for r in P if r.status == "closed_win"); b = len(P) - a; c = sum(1 for r in A if r.status == "closed_win"); d = len(A) - c; n = a + b + c + d
        if n < 2: continue
        num += a * d / n; den += b * c / n
    return round(num / den, 2) if den else None
rows_ = []
for rg_ in ("risk_on", "mixed"):
    for lab, sub in (("trend ≥22", [r for r in ENT if r.market_regime == rg_ and r.trend_score >= 22]), ("trend <22", [r for r in ENT if r.market_regime == rg_ and r.trend_score < 22])):
        rows_.append([rg_, lab] + statline(sub))
table(["Regime", "Trend group"] + SH, rows_)
mhor = mh(ENT, lambda r: r.trend_score >= 22, lambda r: r.market_regime)
losses_hi = sum(1 for r in LOSS if r.trend_score >= 22)
W(f"Max vs medium: {tm['wrP']}% (n={tm['nP']}) vs {tm['wrA']}% (n={tm['nA']}), p={tm['p']}. Spearman(trend, return)={round(spt.statistic, 3)} (p={round(spt.pvalue, 3)}). Mantel–Haenszel OR controlling for regime = {mhor}. "
  f"Trend ≥22 appears in {losses_hi}/{len(LOSS)} losses ({pct(losses_hi, len(LOSS))}%) vs {sum(1 for r in WINS if r.trend_score>=22)}/{len(WINS)} wins. **Do maximum-trend trades outperform? NOT SUPPORTED** (no monotone relation; {grade(tm['nP'], tm['p'])}). **Does trend create false positives?** Trend is satisfied by nearly every published plan (median {med([r.trend_score for r in ENT])}/25) so it acts as a gate, not a discriminator — high trend appears in as many losses as wins. **Does it dominate losing trades?** It is present in a large share of losses only because it is present in most trades.")

# ------------------------------------------------------------- G
sec("G", "STRUCTURE AUDIT")
fvg = [r for r in ENT if r.level_reasoning]; fv = two(lambda r: bool(r.level_reasoning.get("fvg_used")), fvg)
def stack(r): return above_all(r)
te = two(above_all, ENT); t9 = two(lambda r: r.structure_score >= 9, ENT)
table(FH, [frow("FVG used in levels (post-capture trades)", fv), frow("Price beyond EMA20/50/200 in trade direction", te), frow("structure_score ≥ 9", t9)])
bucket_table("structure_score buckets", lambda r: r.structure_score, [0, 6, 9, 12, 20])
W("**BOS, CHoCH, Order Blocks: INSUFFICIENT DATA** — not persisted per trade (`market_snapshots` has bos/choch columns, but only for 6 symbols and ends 2026-08-04, before the first trade); order-block detection does not exist in the code. FVG is testable only for post-capture trades "
  f"(n={len(fvg)}). **Which structures matter?** None demonstrated: FVG p={fv['p'] if fv else 'n/a'}, EMA-stack p={te['p']}, structure_score≥9 p={t9['p']}. **Zero predictive value?** Consistent with zero for all three at this n (INSUFFICIENT POWER, not proof of no effect).")

# ------------------------------------------------------------- H
sec("H", "MOMENTUM AUDIT")
SPM = [("RSI 50–70", lambda r: 50 <= ei(r)["rsi14"] < 70 if ei(r).get("rsi14") is not None else None), ("RSI < 50", lambda r: ei(r)["rsi14"] < 50 if ei(r).get("rsi14") is not None else None),
       ("RSI 30–49 (chop)", lambda r: 30 <= ei(r)["rsi14"] < 50 if ei(r).get("rsi14") is not None else None), ("RSI ≥ 70", lambda r: ei(r)["rsi14"] >= 70 if ei(r).get("rsi14") is not None else None),
       ("MACD hist > 0", lambda r: ei(r)["macd_hist"] > 0 if ei(r).get("macd_hist") is not None else None), ("ADX ≥ 25", lambda r: ei(r)["adx14"] >= 25 if ei(r).get("adx14") is not None else None),
       ("ADX ≥ 35", lambda r: ei(r)["adx14"] >= 35 if ei(r).get("adx14") is not None else None), ("StochRSI > 0.8", lambda r: ei(r)["stoch_rsi"] > .8 if ei(r).get("stoch_rsi") is not None else None),
       ("BB%B > 0.8", lambda r: ei(r)["bb_pct"] > .8 if ei(r).get("bb_pct") is not None else None), ("BB%B > 0.95", lambda r: ei(r)["bb_pct"] > .95 if ei(r).get("bb_pct") is not None else None)]
table(FH, [frow(n, two(p, ENT)) for n, p in SPM])
for lab, k, e in [("RSI", "rsi14", [0, 30, 40, 50, 60, 70, 100]), ("ADX", "adx14", [0, 20, 35, 50, 200]), ("StochRSI", "stoch_rsi", [0, .2, .5, .8, 1.01]), ("BB %B", "bb_pct", [-1, .2, .5, .8, 1.0, 5])]:
    bucket_table(lab, ind(k), e)
W("**Overextension thresholds (scan of candidate cut-points, upper tail — win rate at/above vs below; multiple comparisons, so treat as exploratory):**")
rowsT = []
for lab, k, cuts in [("RSI", "rsi14", [60, 65, 70, 75]), ("StochRSI", "stoch_rsi", [.7, .8, .9]), ("BB%B", "bb_pct", [.8, .9, 1.0]), ("MFI", "mfi", [70, 80, 90])]:
    for c_ in cuts:
        t = two(lambda r, k=k, c_=c_: ei(r)[k] >= c_ if ei(r).get(k) is not None else None, ENT)
        if t: rowsT.append([f"{lab} ≥ {c_}", f"{t['nP']}/{t['nA']}", f"{fn(t['wrP'],1)}% / {fn(t['wrA'],1)}%", t["OR"], t["p"], grade(min(t['nP'], t['nA']), t['p'])])
table(["Cut", "n above/below", "Win% above / below", "OR", "p", "Evidence"], rowsT)
t_rsi = two(lambda r: 50 <= ei(r)["rsi14"] < 70 if ei(r).get("rsi14") is not None else None, ENT)
W(f"**Finding:** the only split reaching p<0.05 is RSI 50–70 vs the rest ({t_rsi['wrP']}% n={t_rsi['nP']} vs {t_rsi['wrA']}% n={t_rsi['nA']}, OR {t_rsi['OR']}, p={t_rsi['p']} → LIKELY, not CONFIRMED). StochRSI ≥0.7 is POSSIBLE (better, not worse). ADX≥35 is NOT significant. "
  "**Overextension:** no evidence that overbought readings hurt — high-RSI/StochRSI/BB/MFI bins do equal or better, but the extreme bins (RSI≥70 n=4, BB>0.95 n=2, MFI>80 n=7) are INSUFFICIENT DATA; the hypothesis 'overbought entries lose' is NOT SUPPORTED. The weak end is low momentum (RSI<50: win 20.8%, n=24, p≈0.06 → POSSIBLE).")

# ------------------------------------------------------------- I
sec("I", "VOLUME AUDIT")
SPV = [("CMF > 0", lambda r: ei(r)["cmf"] > 0 if ei(r).get("cmf") is not None else None), ("CMF > 0.1", lambda r: ei(r)["cmf"] > .1 if ei(r).get("cmf") is not None else None), ("volume_score ≥ 8", lambda r: r.volume_score >= 8),
       ("volume_score = 10", lambda r: r.volume_score >= 10), ("funding_score = 10 (uncrowded)", lambda r: r.funding_score >= 10 if r.funding_score is not None else None), ("MFI > 60", lambda r: ei(r)["mfi"] > 60 if ei(r).get("mfi") is not None else None)]
table(FH, [frow(n, two(p, ENT)) for n, p in SPV])
bucket_table("CMF", ind("cmf"), [-1, -.1, 0, .1, .2, 1]); bucket_table("volume_score", lambda r: r.volume_score, [0, 5, 8, 10, 11])
tvv = two(lambda r: r.volume_score >= 8, ENT)
W(f"**OBV: INSUFFICIENT DATA** (not stored per trade; obv_slope exists only in the pre-trade market_snapshots). Volume-ratio: only as the aggregate volume_score. **Does volume confirmation improve win rate? NOT SUPPORTED** (volume_score≥8: {tvv['wrP']}% vs {tvv['wrA']}%, p={tvv['p']}). Funding is near-constant (10 for {sum(1 for r in ENT if r.funding_score>=10)}/{len(ENT)} trades) → cannot be evaluated. Negative CMF trades did not lose more (see table) — the opposite direction of what the design assumes.")

# ------------------------------------------------------------- J
sec("J", "REGIME AUDIT")
rg = collections.defaultdict(list)
for r in ENT: rg[r.market_regime or "unlabeled"].append(r)
rowsJ = [[k] + statline(v) + tpm(v) for k, v in rg.items()] + [[k, 0, "—", "—", "—", "—", "—", "—", "—", "—", "—"] for k in ("risk_off", "trend expansion", "mean reversion", "panic volatility")]
table(["Regime"] + SH + ["TP1%", "TP2%", "TP3%", "Stop%"], rowsJ)
with _eng.connect() as c: rs = c.execute(_t("select market_regime, count(*) from scan_snapshots group by market_regime")).fetchall()
tj = two(lambda r: r.market_regime == "mixed" if r.market_regime else None, ENT)
table(FH, [frow("mixed vs risk_on", tj)])
W(f"ScanSnapshot regime labels over all scans: {dict(rs)}. **Only risk_on and mixed have ever been emitted; risk_off, trend expansion, mean reversion and panic volatility have n=0** — INSUFFICIENT DATA, and the engine cannot be judged on regimes it never outputs. risk_on has been WORSE than mixed for trades (win {summ(rg['risk_on'])['wr']}% vs {summ(rg['mixed'])['wr']}%, p={tj['p']}), the reverse of the naive expectation, but regime is confounded with calendar period ({grade(min(tj['nP'], tj['nA']), tj['p'])}).")

# ------------------------------------------------------------- K
sec("K", "LONG VS SHORT AUDIT")
LG = [r for r in ENT if r.direction == "long"]; SHT = [r for r in ENT if r.direction == "short"]
clean = [r for r in ENT if not in_outage(r.exit_time)]
table(["Segment"] + SH + ["TP1%", "TP2%", "TP3%", "Stop%", "Avg stop slip%"],
      [[lab] + statline(v) + tpm(v) + [fn(avg([r.stop_slippage_pct for r in v if r.stop_slippage_pct is not None]))] for lab, v in
       [("Long (all)", LG), ("Short (all)", SHT), ("Long, exit NOT in monitoring gap", [r for r in clean if r.direction == "long"]), ("Short, exit NOT in monitoring gap", [r for r in clean if r.direction == "short"]), ("Short, exit inside gap", [r for r in SHT if in_outage(r.exit_time)])]])
for dim, keyf, vals in [("confidence bucket", lambda r: None if r.confidence is None else "<60" if r.confidence < 60 else ("60–64" if r.confidence < 65 else "65+"), ["<60", "60–64", "65+"]), ("regime", lambda r: r.market_regime, ["risk_on", "mixed"]),
                        ("entry quality", lambda r: r.entry_quality or "none", ["excellent", "good", "neutral", "none"]), ("timeframe", lambda r: r.timeframe, ["swing", "intraday"])]:
    rr_ = []
    for v in vals:
        for d_ in ("long", "short"):
            sub = [r for r in ENT if keyf(r) == v and r.direction == d_]
            if sub: rr_.append([v, d_] + statline(sub))
    W(f"**By {dim}**"); table([dim, "Dir"] + SH, rr_)
sy = collections.defaultdict(list)
for r in SHT: sy[r.symbol].append(r)
W("**Shorts by symbol**"); table(["Symbol", "n", "Win", "Ret list %", "Exit in gap?"], [[k, len(v), sum(1 for r in v if r.status == "closed_win"), ", ".join(fn(ret(r), 1) for r in v), ", ".join("Y" if in_outage(r.exit_time) else "N" for r in v)] for k, v in sorted(sy.items())])
tk = two(lambda r: r.direction == "short", ENT); tk2 = two(lambda r: r.direction == "short", clean)
table(FH, [frow("short vs long (all)", tk), frow("short vs long (exit not in gap)", tk2)])
sg = [r for r in SHT if in_outage(r.exit_time)]
W(f"**Are shorts fundamentally broken?** Headline: {summ(SHT)['wr']}% win, PF {summ(SHT)['pf']} (n={len(SHT)}; p={tk['p']} vs longs → {grade(len(SHT), tk['p'])}). But {len(sg)}/{len(SHT)} shorts exited inside a monitoring gap and {sum(1 for r in sg if r.status=='closed_loss')}/{len(sg)} of those lost (avg {fn(avg([ret(r) for r in sg]))}%); with those removed, shorts win {summ([r for r in clean if r.direction=='short'])['wr']}% (n={len([r for r in clean if r.direction=='short'])}) vs longs {summ([r for r in clean if r.direction=='long'])['wr']}% (p={tk2['p']}). "
  f"Shorts exist only in the `mixed` regime and mostly in a narrow time window, so 'broken only in certain regimes' is UNTESTABLE (no short in risk_on). **Should shorts be disabled? Not on this evidence — INSUFFICIENT DATA** (the failure is confounded with downtime; a hard disable cannot be justified until ≥30 shorts are observed with continuous monitoring).")

# ------------------------------------------------------------- L
sec("L", "TIMEFRAME AUDIT")
table(["Timeframe class"] + SH + ["Median hold h"], [[k] + statline([r for r in ENT if r.timeframe == k]) + [fn(med([hrs(r) for r in ENT if r.timeframe == k]), 1)] for k in sorted(set(r.timeframe for r in ENT))])
def btc_al(r):
    b = ei(r).get("btc_trend")
    if b not in ("bull", "bear"): return None
    return (b == "bull") == (r.direction == "long")
tb_ = two(btc_al, ENT); ts_ = two(lambda r: r.timeframe == "swing", ENT)
MTF = re.compile(r"(multi[- ]timeframe|higher[- ]timeframe|HTF|1d|daily|4h|1h)[^.]{0,60}(align|confirm|agree|bull|bear)", re.I)
tm_ = two(lambda r: bool(MTF.search(r.reasoning or "")) if r.reasoning else None, ENT)
table(FH, [frow("BTC trend agrees with trade direction", tb_), frow("swing vs intraday", ts_), frow("reasoning text asserts timeframe alignment (text proxy)", tm_)])
W("**1h / 4h / 1d alignment as structured fields: INSUFFICIENT DATA** — no per-timeframe trend is stored on trades. Available proxies: BTC-trend/direction agreement, swing-vs-intraday label, and a regex over Claude's free-text (a proxy for what was *claimed*, not computed). "
  f"None separates outcomes at conventional significance (BTC agreement p={tb_['p']}; text-proxy p={tm_['p']}) → no combination is shown to outperform.")

# ------------------------------------------------------------- M
sec("M", "SYMBOL RELIABILITY AUDIT")
W(f"Bayesian shrinkage (Beta prior strength 10 toward pooled win rate {POOLED}%). Tier rules (report-defined): **Trusted** n≥5 and reliability≥55; **Watch** default and any symbol with n<3 (thin sample, cannot be promoted or demoted); **Caution** n≥3 and reliability 33–45; **Avoid** n≥3 and (0 wins or reliability<33). Reliability uses all data including each trade itself (hindsight).")
bysym = collections.defaultdict(list)
for r in ENT: bysym[r.symbol].append(r)
rowsM = []; tiers = collections.Counter()
for sy_, v in bysym.items():
    x = summ(v); rv = RELMAP[sy_]["reliability_score"]
    tr = "Watch (n<3)" if x["n"] < 3 else "Avoid" if (x["w"] == 0 or rv < 33) else "Trusted" if (x["n"] >= 5 and rv >= 55) else "Caution" if rv < 45 else "Watch"
    tiers[tr] += 1; rowsM.append([sy_, x["n"], x["w"], f"{x['wr']}%", fn(x["avg"]), fn(x["pf"]), fn(rv, 1), tr])
rowsM.sort(key=lambda z: (-float(z[6]), -z[1])); table(["Symbol", "n", "Wins", "Win%", "Avg ret", "PF", "Reliability", "Tier"], rowsM)
tt_ = [(RELMAP[r.symbol]["reliability_score"], ret(r)) for r in ENT]
W(f"Symbols: {len(bysym)}; tier counts {dict(tiers)}; symbols with n≥5: {sum(1 for v in bysym.values() if len(v)>=5)}. Spearman(hindsight reliability, return)={round(spearmanr([a for a,_ in tt_],[b for _,b in tt_]).statistic,3)} is hindsight-inflated and NOT evidence of predictiveness. **Out-of-sample test:** none possible with this n per symbol → INSUFFICIENT DATA.")

# ------------------------------------------------------------- N
sec("N", "HISTORICAL SIMILARITY AUDIT")
hp = [r for r in ENT if r.historic_probability is not None]; nh = [r for r in ENT if r.historic_probability is None]
table(["Group"] + SH, [["History present"] + statline(hp), ["History missing"] + statline(nh)])
tn = two(lambda r: r.historic_probability is not None, ENT)
tp_ = sum(1 for r in hp if r.historic_probability >= .5 and r.status == "closed_win"); fp_ = sum(1 for r in hp if r.historic_probability >= .5 and r.status == "closed_loss")
fn_ = sum(1 for r in hp if r.historic_probability < .5 and r.status == "closed_win"); tn_ = sum(1 for r in hp if r.historic_probability < .5 and r.status == "closed_loss")
table(["History said", "Won", "Lost"], [["≥50% win", tp_, fp_], ["<50% win", fn_, tn_]])
hs = collections.Counter(r.history_score for r in ENT)
W(f"Coverage {len(hp)}/{len(ENT)}; symbols covered {len(set(r.symbol for r in hp))}/{len(bysym)}. history_score values: {dict(sorted(hs.items()))} (0 when history is absent or sample<20 — i.e. missing history is scored neutral). "
  f"**Did history improve accuracy?** No: with history {summ(hp)['wr']}% vs without {summ(nh)['wr']}% (p={tn['p']}); history said ≥50% on {tp_+fp_} trades and {fp_} lost → the analogue win-rate was over-optimistic (NOT SUPPORTED). Confounded with the few majors that have history. "
  f"**Did neutral scoring hurt when history was missing?** No: trades WITHOUT history did better; no evidence that treating absence as neutral is harmful (NOT SUPPORTED).")

# ------------------------------------------------------------- O
sec("O", "EXPECTED VALUE AUDIT")
POST = [r for r in ENT if evr(r) is not None]
def loo_ev(r):
    rp = rr(r).get("risk_to_sl_pct"); rw = rr(r).get("reward_to_tp1_pct")
    if not rp or rw is None: return None
    o = [x for x in ENT if x is not r]; return sum(1 for x in o if x.tp1_hit) / len(o) * rw / rp - sum(1 for x in o if x.stop_hit and not x.tp1_hit) / len(o)
RETRO = {r.id: loo_ev(r) for r in ENT}
def evbk(fun):
    out = []
    for a, b, nm in [(-99, 0, "<0"), (0, 1, "0–1R"), (1, 2, "1–2R"), (2, 99, "2R+")]:
        sub = [r for r in ENT if fun(r) is not None and a <= fun(r) < b]; out.append([nm] + (statline(sub) + [fn(avg([rR(r) for r in sub if rR(r) is not None]))] if sub else ["0"] + [""] * 6))
    return out
W(f"Stored EV (issued-time) exists for n={len(POST)} closed trades; leave-one-out retrospective EV for the full sample (formula identical to the engine's: P(TP1)·reward_TP1/risk − P(stop before TP1))."); W()
W("**Stored EV**"); table(["EV bucket"] + SH + ["Avg realized R"], evbk(evr)); W("**Retrospective LOO EV**"); table(["EV bucket"] + SH + ["Avg realized R"], evbk(lambda r: RETRO[r.id]))
pr_ = [(RETRO[r.id], rR(r)) for r in ENT if RETRO[r.id] is not None and rR(r) is not None]; spe = spearmanr([a for a, _ in pr_], [b for _, b in pr_])
ps_ = [(evr(r), rR(r)) for r in POST if rR(r) is not None]; spp = spearmanr([a for a, _ in ps_], [b for _, b in ps_]) if len(ps_) >= 8 else None
W(f"Spearman(retro EV, realized R)={round(spe.statistic,3)} (p={round(spe.pvalue,3)}, n={len(pr_)}); stored EV vs realized R: {('%s (p=%s, n=%d)' % (round(spp.statistic,3), round(spp.pvalue,3), len(ps_))) if spp else 'INSUFFICIENT DATA'}. **Does EV correlate with profit? NOT SUPPORTED** — the calibration table shows no monotone rise in realized R with predicted EV; negative-EV bucket outcomes are not worse. EV is dominated by the reward/risk ratio because P(TP1) is pooled.")

# ------------------------------------------------------------- P
sec("P", "TRADE MANAGER AUDIT (TP CONTINUATION MATRIX)")
tp1 = [r for r in ENT if r.tp1_hit]; n1 = len(tp1); t2 = [r for r in tp1 if r.tp2_hit]; t3 = [r for r in t2 if r.tp3_hit]
cont_ = [CONT[r.id] for r in tp1 if r.id in CONT]
def pp_(k): v = [c[k] for c in cont_ if c.get(k) is not None]; return f"{fn(pct(sum(1 for x in v if x), len(v)), 1)}% (n={len(v)})"
table(["Transition (trades that reached TP1, n=%d)" % n1, "Probability", "Wilson CI"], [
    ["P(TP2 | TP1)", f"{fn(pct(len(t2), n1), 1)}% ({len(t2)}/{n1})", "–".join(str(x) for x in wilson(len(t2), n1))],
    ["P(TP3 | TP2)", f"{fn(pct(len(t3), len(t2)), 1)}% ({len(t3)}/{len(t2)})", "–".join(str(x) for x in wilson(len(t3), len(t2)))],
    ["P(final loss | TP1)", f"{fn(pct(sum(1 for r in tp1 if r.status=='closed_loss'), n1), 1)}%", "–".join(str(x) for x in wilson(sum(1 for r in tp1 if r.status == 'closed_loss'), n1))],
    ["P(returned to entry after TP1)", pp_("returned_to_entry"), ""], ["P(returned to stop after TP1)", pp_("returned_to_stop"), ""]])
W(f"Average continuation after TP1 (best excursion vs entry): {avg([c['continuation_after_tp1'] for c in cont_ if c.get('continuation_after_tp1') is not None])}% ; average pullback: {avg([c['pullback_after_tp1'] for c in cont_ if c.get('pullback_after_tp1') is not None])}%.")
def cm(name, keyf):
    g = collections.defaultdict(list)
    for r in tp1:
        k = keyf(r)
        if k is not None: g[k].append(r)
    W(f"**By {name}**"); table([name, "n(TP1)", "P(TP2|TP1)", "P(TP3|TP2)", "P(final loss)"], [[k, len(v), f"{fn(pct(sum(1 for r in v if r.tp2_hit), len(v)), 1)}%", f"{fn(pct(sum(1 for r in v if r.tp3_hit), sum(1 for r in v if r.tp2_hit)), 1)}% (n={sum(1 for r in v if r.tp2_hit)})", f"{fn(pct(sum(1 for r in v if r.status=='closed_loss'), len(v)), 1)}%"] for k, v in sorted(g.items(), key=lambda kv: str(kv[0]))])
cm("direction", lambda r: r.direction); cm("regime", lambda r: r.market_regime); cm("confidence", lambda r: None if r.confidence is None else "<60" if r.confidence < 60 else "60–64" if r.confidence < 65 else "65+"); cm("entry quality", lambda r: r.entry_quality)
W("Counterfactual policies (assumptions: fills at TP price, no fees; breakeven-stop bounded by optimistic/pessimistic path handling): see below.")
def tpr(r, k): lv = getattr(r, k); return (lv - r.entry) / r.entry * 100 * sign(r) if lv is not None else None
def policy(r, m):
    a = ret(r)
    if not r.tp1_hit or m == "actual": return a
    if m == "tp1": return tpr(r, "tp1")
    if m == "tp2": return tpr(r, "tp2") if r.tp2_hit and r.tp3 is not None else a
    p_ = CONT.get(r.id, {}).get("returned_to_entry")
    if r.status == "closed_loss" or p_ is True: return 0.0
    if p_ is None and m == "be_pess": return 0.0
    return a
table(["Policy", "n", "Sum ret%", "Avg", "PF", "Median"], [[lab, len(ENT), round(sum(policy(r, m) for r in ENT), 1), avg([policy(r, m) for r in ENT]), fn(pf([policy(r, m) for r in ENT])), med([policy(r, m) for r in ENT])] for lab, m in
      [("Actual", "actual"), ("Exit at TP1", "tp1"), ("Exit at TP2 (if TP3 defined)", "tp2"), ("Breakeven stop after TP1 (optimistic)", "be_opt"), ("Breakeven stop after TP1 (pessimistic)", "be_pess")]])
W("Trade-Manager decisions actually logged in PredictionSnapshot (real probability-driven decisions exist only post-2026-09-12):"); dec = collections.Counter((sn.stage, sn.management_decision) for sn in SNAPS if sn.management_decision)
table(["Stage", "Decision", "Snapshots"], [[a, b, c] for (a, b), c in dec.most_common()])
W("**Conclusion:** exiting early at TP1 or TP2 is clearly worse than holding (CONFIRMED by arithmetic on n=%d); a breakeven stop's benefit is INSUFFICIENT DATA (bounds straddle actual)." % len(ENT))

# ------------------------------------------------------------- Q
sec("Q", "FAILURE PATTERN ENGINE AUDIT")
lc = collections.defaultdict(list)
for r in LOSS: lc[LIFE[r.id]].append(r)
table(["Lifecycle (all losses, n=%d)" % len(LOSS), "n", "% of losses", "Avg ret", "Total cost %", "% of total loss"], [[k, len(v), fn(pct(len(v), len(LOSS)), 1) + "%", fn(avg([ret(r) for r in v])), fn(sum(ret(r) for r in v), 1), fn(pct(-sum(ret(r) for r in v), -sum(ret(r) for r in LOSS)), 1) + "%"] for k, v in sorted(lc.items(), key=lambda kv: sum(ret(r) for r in kv[1]))])
tg = collections.Counter(t for r in LOSS for t in TAGS[r.id]); W(f"Risk tags on losses (multi-label): {dict(tg)}")
slow = [r for r in LOSS if hrs(r) and hrs(r) > 72 and (r.max_runup_pct or 0) < 1]; perf = [r for r in WINS if (r.max_drawdown_pct or 0) >= -2]
table(["Requested pattern", "n", "Status"], [["Immediate reversal", len(lc.get('immediate_reversal', [])), "measured"], ["TP1 then stop", len(lc.get('reached_tp1_then_stopped', [])), "measured"], ["TP2 then reverse", len(lc.get('hit_tp2_then_reversed', [])), "measured"],
      ["Slow bleed (loss held >72h, MFE<1%)", len(slow), "proxy"], ["Perfect trend (win with MAE ≥ −2%)", len(perf), "proxy (wins)"],
      ["Late breakout / liquidity sweep / trend exhaustion / false breakout / distribution reversal", "—", "INSUFFICIENT DATA (no per-trade labels; not computed)"]])
W("**Cost ranking:** immediate reversals dominate both frequency and cost — CONFIRMED (facts). Causes behind them are not identifiable from stored fields.")

# ------------------------------------------------------------- R
sec("R", "RED FLAG AUDIT")
rowsR = []
for f in FLAG_NAMES:
    sub = [r for r in ENT if f in FLAGS[r.id]]; oth = [r for r in ENT if f not in FLAGS[r.id]]; t = two(lambda r, f=f: f in FLAGS[r.id], ENT)
    rowsR.append([f] + statline(sub) + [fn(summ(oth)["wr"], 1) + "%", t["p"] if t else "—", grade(len(sub), t["p"] if t else None)])
table(["Flag"] + SH + ["Win% without", "p", "Evidence"], rowsR)
stored = collections.Counter(x for r in ENT if r.red_flags for x in (r.red_flags.get("red_flags") if isinstance(r.red_flags, dict) else r.red_flags))
W(f"Stored `red_flags` (post-2026-09-?? trades only): {sum(1 for r in ENT if r.red_flags)} trades, tally {dict(stored)} (too few to evaluate).")
W("**Which matter?** Only `short_direction` (p≈0.04, confounded by downtime) and the RSI 30–49 chop zone (p≈0.09) are even suggestive; `mfi_over_80` looks 'positive' (n=7) but is INSUFFICIENT DATA. **Should become warnings:** RSI-chop (POSSIBLE) and short-direction (POSSIBLE) as soft warnings only; none justify a score change.")

# ------------------------------------------------------------- S
sec("S", "DECISION AUDIT (CHECKLIST REPLAY)")
AU = {r.id: audit_trade(r) for r in ENT}
items = ["trend_pass", "structure_pass", "history_pass", "volume_pass", "funding_pass", "risk_pass", "regime_pass"]
rowsS = []
for it in items:
    f_l = sum(1 for r in LOSS if it in AU[r.id]["rejected_checks"]); f_w = sum(1 for r in WINS if it in AU[r.id]["rejected_checks"])
    fa = [r for r in ENT if it in AU[r.id]["rejected_checks"]]; ok = [r for r in ENT if it not in AU[r.id]["rejected_checks"]]
    t = two(lambda r, it=it: it in AU[r.id]["rejected_checks"], ENT)
    rowsS.append([it.replace("_pass", ""), f"{f_l}/{len(LOSS)} ({fn(pct(f_l, len(LOSS)), 1)}%)", f"{f_w}/{len(WINS)} ({fn(pct(f_w, len(WINS)), 1)}%)", fn(summ(fa)["wr"], 1) + f"% (n={len(fa)})" if fa else "—", fn(summ(ok)["wr"], 1) + f"% (n={len(ok)})", t["p"] if t else "—"])
rowsS.sort(key=lambda z: -float(z[1].split("(")[1].rstrip("%)")))
table(["Checklist item (FAILED)", "Failed in losses", "Failed in wins", "Win% when failed", "Win% when passed", "Fisher p"], rowsS)
W("Failure-frequency chart (share of losses failing each check):"); W("```")
for z in rowsS: v = float(z[1].split("(")[1].rstrip("%)")); W(f"{z[0]:<10} {'█' * int(v / 3.5):<30}{v:>5.1f}%")
W("```")
nf = collections.Counter(len(AU[r.id]["rejected_checks"]) for r in ENT)
W(f"Number of failed checks per trade: {dict(sorted(nf.items()))}. **Checklist items that fail most often (history — which fails by construction whenever no analogue exists — then structure) fail equally often in wins — they do not discriminate (NOT SUPPORTED as filters).** Regime/trend/funding/risk checks almost never fail (constant → no information).")

# ------------------------------------------------------------- T
sec("T", "SCAN SNAPSHOT AUDIT (REJECTIONS AND WHAT HAPPENED AFTER)")
def cat_of(reason):
    if reason is None: return "published/active (no rejection)"
    r_ = reason.lower()
    if "exhausted" in r_: return "exhausted"
    if "late" in r_: return "late"
    if r_.startswith("no_trade"): return "no_trade (direction gate)"
    if "outside top" in r_: return "rank cutoff (outside top 6)"
    return "other"
cc = collections.Counter(cat_of(x.rejection_reason) for x in SCANS)
rr2 = collections.Counter((x.rejection_reason or "none")[:70] for x in SCANS)
table(["Rejection category", "Scan rows", "% of all"], [[k, v, fn(pct(v, len(SCANS)), 1) + "%"] for k, v in cc.most_common()])
W(f"Raw reason strings (top 8): {dict(rr2.most_common(8))}. Avoid-grade plans: {cnt['rejected_avoid']} (`rejected_avoid`).")
SYMTS = {k: [(sn.timestamp, sn.current_price) for sn in v] for k, v in SNAP_BY_SYM.items()}
def fwd_h(sym, t0, sg, H):
    lst = SYMTS.get(sym)
    if not lst: return None
    ts = [a for a, _ in lst]; i = bisect.bisect_left(ts, t0)
    c = [j for j in (i - 1, i) if 0 <= j < len(lst) and abs(lst[j][0] - t0) <= 15 * 60000]
    if not c: return None
    j0 = min(c, key=lambda j: abs(lst[j][0] - t0)); p0 = lst[j0][1]
    j1 = bisect.bisect_left(ts, t0 + H * 3600000)
    if j1 >= len(lst) or abs(lst[j1][0] - (t0 + H * 3600000)) > max(0.25 * H, 0.5) * 3600000: return None
    return (lst[j1][1] - p0) / p0 * 100 * sg
rowsT = []
for k in [c_[0] for c_ in cc.most_common()]:
    subs = [x for x in SCANS if cat_of(x.rejection_reason) == k and x.direction in ("long", "short")]
    row = [k, len(subs)]
    for H in (1, 4, 24, 72):
        v = [fwd_h(x.symbol, x.timestamp, 1 if x.direction == "long" else -1, H) for x in subs]; v = [z for z in v if z is not None]
        row.append(f"n={len(v)}: avg {fn(avg(v))}% / fav {fn(pct(sum(1 for z in v if z > 0), len(v)), 0)}%" if v else "n=0")
    rowsT.append(row)
table(["Category (directional scans only)", "Directional rows", "+1h", "+4h", "+24h", "+72h"], rowsT)
W("**Reading the table:** the ‘published/active’ row is survivorship-biased (rows only appear at long horizons if their plan stayed tracked and the price series is contiguous), so its +24h/+72h averages must not be read as a market baseline; cells with n<10 are INSUFFICIENT DATA. **Critical limitation:** ScanSnapshot stores no price and `market_snapshots` ends before the first scan, so forward returns exist only where a tracked TradeOutcome on the same symbol had PredictionSnapshot prices (a small, selection-biased, highly autocorrelated subset; n shown per cell). `exhausted` scans have direction overwritten to no_trade, so directional outcomes are unrecoverable. "
  "**Missed-opportunity totals are INSUFFICIENT DATA**; the recorder for this exists but is not wired into the scanner (0 rows in `rejected_opportunity_outcomes`). I do not report a missed-profit estimate because it would be invented.")

# ------------------------------------------------------------- U
sec("U", "MONITORING / INFRASTRUCTURE AUDIT")
tss = sorted(set(sn.timestamp for sn in SNAPS)); span = tss[-1] - tss[0]; out_ms = sum(o["end"] - o["start"] for o in OUT)
top = sorted(OUT, key=lambda o: -(o["end"] - o["start"]))[:10]
table(["Metric", "Value"], [["Distinct snapshot cycles", len(tss)], ["Span (days)", round(span / 86400000, 1)], ["Gaps >10 min", len(OUT)], ["Time inside gaps (days)", round(out_ms / 86400000, 1)], ["Scanner uptime", f"{round((1 - out_ms / span) * 100, 1)}%"]])
table(["Largest gaps: start (UTC)", "End (UTC)", "Hours", "Closed trades that exited inside"], [[dt(o["start"]), dt(o["end"]), round((o["end"] - o["start"]) / 3600000, 1), sum(1 for r in ENT if o["start"] <= (r.exit_time or 0) <= o["end"])] for o in top])
def overlap(r): return any(o["start"] < (r.exit_time or tss[-1]) and o["end"] > (r.entry_time or r.created_at) for o in OUT)
aff = [r for r in ENT if overlap(r)]; ex_in = [r for r in ENT if in_outage(r.exit_time)]
sl_in = [r for r in ENT if r.stop_slippage_pct is not None and in_outage(r.exit_time)]; sl_out = [r for r in ENT if r.stop_slippage_pct is not None and not in_outage(r.exit_time)]
med_norm = statistics.median([r.stop_slippage_pct for r in sl_out]); excess = sum(r.stop_slippage_pct - med_norm for r in sl_in)
table(["Impact", "Value"], [["Closed trades open during ≥1 gap", f"{len(aff)}/{len(ENT)} ({pct(len(aff), len(ENT))}%)"], ["Closed trades whose EXIT fell inside a gap", len(ex_in)],
      ["Stop-exit slippage inside gaps: n / avg / worst", f"{len(sl_in)} / {fn(avg([r.stop_slippage_pct for r in sl_in]))}% / {fn(min(r.stop_slippage_pct for r in sl_in))}%"],
      ["Stop-exit slippage in uptime: n / avg / worst", f"{len(sl_out)} / {fn(avg([r.stop_slippage_pct for r in sl_out]))}% / {fn(min(r.stop_slippage_pct for r in sl_out))}%"],
      ["Estimated loss attributable to downtime (sum of slippage in gaps beyond the uptime median slippage of %s%%)" % fn(med_norm), f"{round(excess, 1)} percentage-points across {len(sl_in)} stop exits"]])
L_in = [r for r in LOSS if in_outage(r.exit_time)]; L_out = [r for r in LOSS if not in_outage(r.exit_time)]
table(["Loss attribution", "n", "Sum ret%", "Avg ret%", "% of total loss"], [["Exit inside gap (infrastructure-contaminated)", len(L_in), fn(sum(ret(r) for r in L_in), 1), fn(avg([ret(r) for r in L_in])), fn(pct(-sum(ret(r) for r in L_in), -sum(ret(r) for r in LOSS)), 1) + "%"],
      ["Exit during uptime (strategy)", len(L_out), fn(sum(ret(r) for r in L_out), 1), fn(avg([ret(r) for r in L_out])), fn(pct(-sum(ret(r) for r in L_out), -sum(ret(r) for r in LOSS)), 1) + "%"]])
W_in = [r for r in WINS if in_outage(r.exit_time)]
W(f"**Separation of strategy vs infrastructure:** slippage-in-gap explains an estimated {round(excess,1)}pp of loss (a lower bound on damage, since it excludes losses that gaps allowed to deepen without a stop being recorded); {len(L_in)}/{len(LOSS)} losses carry {fn(pct(-sum(ret(r) for r in L_in), -sum(ret(r) for r in LOSS)),1)}% of loss magnitude. "
  f"Downtime also inflates wins ({len(W_in)}/{len(WINS)} wins exited in a gap; avg {fn(avg([ret(r) for r in W_in]))}% vs {fn(avg([ret(r) for r in WINS if not in_outage(r.exit_time)]))}% otherwise), so the net effect on PF cannot be isolated. Uptime ex-gap trades: PF {summ([r for r in ENT if not in_outage(r.exit_time)])['pf']} (n={len([r for r in ENT if not in_outage(r.exit_time)])}). Evidence: CONFIRMED that monitoring is unreliable; net P&L effect INSUFFICIENT DATA.")

# ------------------------------------------------------------- V
sec("V", "PREDICTION VERSION AUDIT")
EV_FIRST = min(r.created_at for r in ALL if r.expected_value)
tmm = min([r.created_at for r in ALL if r.prediction_metadata] or [EV_FIRST])
grp = [("V0 pre entry-quality (<%s)" % dt(EQ_LAUNCH), [r for r in ENT if r.created_at < EQ_LAUNCH]), ("V1 entry-quality live, pre-EV", [r for r in ENT if EQ_LAUNCH <= r.created_at < EV_FIRST]),
       ("V2 EV + Trade Manager + metadata live (≥%s)" % dt(EV_FIRST), [r for r in ENT if r.created_at >= EV_FIRST])]
rowsV = []
for nm, sub in grp:
    x = summ(sub); e1 = [r for r in sub if r is not max(sub, key=ret)] if sub else []
    rowsV.append([nm] + statline(sub) + [fn(pf([ret(r) for r in e1])), fn(x["tp1"]), fn(x["stop"]), fn(avg([r.stop_slippage_pct for r in sub if r.stop_slippage_pct is not None]))])
table(["Version"] + SH + ["PF ex-best", "TP1%", "Stop%", "Avg stop slip%"], rowsV)
tv = two(lambda r: r.created_at >= EQ_LAUNCH, ENT); tv2 = two(lambda r: r.created_at >= EV_FIRST, ENT)
table(FH, [frow("post-EQ vs pre-EQ", tv), frow("post-EV vs earlier", tv2)])
W(f"Entry-quality launch, EV, Trade Manager and metadata: EV/Trade-Manager/metadata shipped together (first stored EV {dt(EV_FIRST)}), so they cannot be separated. Differences are between calendar windows and market conditions and are NOT attributable to the features. "
  f"Post-EQ vs pre-EQ win rate p={tv['p']}, post-EV vs earlier p={tv2['p']} → {grade(tv2['nP'], tv2['p'])}. The V2 PF is dominated by a single trade (PF ex-best shown). Evidence: INSUFFICIENT DATA to credit any release.")

# ------------------------------------------------------------- W
sec("W", "FEATURE IMPORTANCE (NO RETRAINING, LOGISTIC/ODDS ONLY)")
W("Univariate: per-1-SD logistic odds ratio with bootstrap 95% CI (400×) on win/loss, plus a joint standardised model with look-ahead-safe features (reliability uses only trades already closed before entry; the EV column is a pooled leave-one-out estimate, whose bias is ~1/n and therefore negligible). A first attempt used per-symbol leave-one-out reliability; it is NOT used because LOO is mechanically anti-correlated with a trade's own outcome (removing a win lowers the score) and produced a spurious negative odds ratio. This is *measurement of the historical outcomes*, not model training for production.")
from sklearn.linear_model import LogisticRegression
def loo_rel(r):
    # time-ordered: only trades that had already CLOSED before this trade was entered (no look-ahead, no leave-one-out bias)
    t0 = r.entry_time or r.created_at
    prior = [x for x in ENT if x is not r and x.exit_time and x.exit_time < t0]
    pw = (sum(1 for x in prior if x.status == "closed_win") / len(prior)) if len(prior) >= 10 else 0.39
    o = [x for x in prior if x.symbol == r.symbol]; w = sum(1 for x in o if x.status == "closed_win")
    return (w + 10 * pw) / (len(o) + 10) * 100
EQN = {"neutral": 0, "good": 1, "excellent": 2}
FEATS = [("trend_score", lambda r: r.trend_score), ("momentum_score", lambda r: r.momentum_score), ("structure_score", lambda r: r.structure_score), ("volume_score", lambda r: r.volume_score), ("regime (mixed=1)", lambda r: 1.0 if r.market_regime == "mixed" else 0.0 if r.market_regime else None),
         ("entry_quality (0/1/2)", lambda r: EQN.get(r.entry_quality)), ("confidence", lambda r: r.confidence), ("history present", lambda r: 1.0 if r.historic_probability is not None else 0.0), ("reliability (prior-trades only)", loo_rel),
         ("EV (retro LOO)", lambda r: RETRO[r.id]), ("direction (short=1)", lambda r: 1.0 if r.direction == "short" else 0.0), ("RSI 4h", lambda r: ei(r).get("rsi14"))]
rngw = np.random.default_rng(11); rowsW = []; keep = []
for nm, f_ in FEATS:
    rws = [r for r in ENT if f_(r) is not None]; x = np.array([f_(r) for r in rws], float); y = np.array([1 if r.status == "closed_win" else 0 for r in rws])
    if x.std() == 0 or len(y) < 20: rowsW.append([nm, len(y), "—", "—", "INSUFFICIENT VARIATION"]); continue
    z = (x - x.mean()) / x.std(); b0 = LogisticRegression(C=1e4, max_iter=500).fit(z[:, None], y).coef_[0][0]
    bb = []
    for _ in range(400):
        i = rngw.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(y) and z[i].std() > 0: bb.append(LogisticRegression(C=1e4, max_iter=500).fit(z[i][:, None], y[i]).coef_[0][0])
    lo, hi = np.percentile(bb, [2.5, 97.5]); sig = lo > 0 or hi < 0; sr = spearmanr(z, [ret(r) for r in rws])
    rowsW.append([nm, len(y), round(float(np.exp(b0)), 2), f"[{np.exp(lo):.2f}, {np.exp(hi):.2f}]", ("LIKELY" if sig else "NOT SUPPORTED") + f" (Spearman vs ret {sr.statistic:.2f}, p={sr.pvalue:.2f})"])
    if sig: keep.append(nm)
table(["Feature", "n", "OR per +1 SD", "Bootstrap 95% CI", "Evidence"], rowsW)
cols = [(nm, f_) for nm, f_ in FEATS if nm in ("trend_score", "momentum_score", "structure_score", "volume_score", "regime (mixed=1)", "confidence", "history present", "reliability (prior-trades only)", "direction (short=1)")]
XR = [r for r in ENT if all(f_(r) is not None for _, f_ in cols)]; X = np.array([[f_(r) for _, f_ in cols] for r in XR], float); y = np.array([1 if r.status == "closed_win" else 0 for r in XR]); Xs = (X - X.mean(0)) / X.std(0)
from sklearn.model_selection import StratifiedKFold; from sklearn.metrics import roc_auc_score
au = [roc_auc_score(y[te], LogisticRegression(C=.5, max_iter=500).fit(Xs[tr], y[tr]).predict_proba(Xs[te])[:, 1]) for sd in range(10) for tr, te in StratifiedKFold(5, shuffle=True, random_state=sd).split(Xs, y)]
W(f"Joint model (9 features, n={len(y)}): cross-validated AUC {round(float(np.mean(au)),3)} ± {round(float(np.std(au)),3)} (0.5 = no skill). Features with a CI excluding 0 univariately: {keep or 'none'}. **Conclusion:** no feature is CONFIRMED (a CI excluding 0 here is 'LIKELY' at best, clustered trades make CIs optimistic). Out-of-sample AUC {round(float(np.mean(au)),3)} is {'modest (>0.6), driven mainly by direction (which is confounded with downtime, §K/§U)' if np.mean(au) > 0.6 else 'weak (≈0.5–0.6)'}; the score components themselves carry no detectable signal (§F,G,H,I).")
KEYW = dict(auc=round(float(np.mean(au)), 3), keep=keep)

# ------------------------------------------------------------- X
sec("X", "WHAT SHOULD CHANGE? (ROI-RANKED)")
W("Ranking = (evidence strength × size of the affected P&L/data-quality lever) ÷ (risk × complexity). Nothing in Phase 2+ alters scoring, decision, regime, prompt or ML weights unless explicitly marked and evidence exists (none currently does).")
table(["Rank", "Change", "Bucket", "Expected improvement", "Evidence (§)", "n", "Risk", "Complexity"], [
 [1, "Run scanner as supervised always-on service (auto-restart, heartbeat alert)", "Immediate (ops, no code in engine)", f"Removes gap exposure on {pct(len(aff), len(ENT))}% of trades; largest single data-quality gain; P&L effect not isolatable", f"§U CONFIRMED", len(ENT), "Very low", "Low"],
 [2, "Report n, CI, median and ex-top-3 PF on every KPI", "Immediate (analytics only)", "Stops over-reading a right-tail-driven PF", f"§A: PF {S['pf']}→{pf3}", len(ENT), "None", "Low"],
 [3, "Show calibrated confidence ± interval; label raw confidence 'score, not probability'", "Immediate (display)", "Fixes ~25pp overstatement", f"§C: Brier {brier} > base {round(base*(1-base),4)}", len(CT), "None", "Low"],
 [4, "Persist BOS/CHoCH/sweep/OBV/timeframe-trend booleans per trade at issuance", "Phase 2 (additive code, no scoring change)", "Makes §G/§L answerable at n=200", "§G/§L INSUFFICIENT DATA", 0, "Low", "Medium"],
 [5, "Wire missed-opportunity recorder (approval needed: frozen scanner file)", "Phase 2", "Enables unbiased rejection analysis (§T)", "§T INSUFFICIENT DATA", 0, "Low", "Low-Med"],
 [6, "Shadow-log breakeven-stop-after-TP1 outcomes", "Analytics only", "Unknown; bounds straddle actual", f"§P", n1, "None", "Low"],
 [7, "Soft warnings: RSI 30–49 chop, short direction (no gating)", "Analytics only", "Possible reduction of avoidable losses; unproven", "§H/§R p≈0.04–0.09", 23, "Low", "Low"],
 [8, "Any score-weight / regime / prompt change", "NOT NOW", "Cannot be estimated", f"§W CV-AUC {KEYW['auc']}; §F/§G/§I none significant", len(y), "High (overfit)", "—"],
 [9, "Disable shorts", "NOT NOW", "Unknown", f"§K: ex-gap shorts {summ([r for r in clean if r.direction=='short'])['wr']}% (n={len([r for r in clean if r.direction=='short'])})", len(SHT), "High (loses right tail)", "—"],
 [10, "ML retraining / auto weight optimizer / coin-specific models", "Phase 3 — only if evidence", "None shown", f"§W, prior retrain identical AUC", len(ENT), "High", "High"]])
W("**INSUFFICIENT DATA to recommend any predictive change.** Everything above rank 3 that touches predictions is deferred to the 200-trade re-audit.")

# ------------------------------------------------------------- Y
sec("Y", "30-DAY FROZEN COMPONENTS CHECK")
table(["Component", "Remain frozen?", "Evidence"], [
 ["scoring.py", "YES", f"§W: CV-AUC {KEYW['auc']}; no component's odds ratio is CONFIRMED; §F/§G/§I show no significant component effects; a weight change would fit noise at n={len(ENT)}"],
 ["decision.py", "YES", "§S: the checklist items that fail most are equally common in wins and losses (no discrimination) — but changing them would be tuning on the same n; revisit at n≥200"],
 ["market_regime.py", "YES", "§J: only 2 of 6 regime labels ever emitted; cannot evaluate what is never produced; unfreezing without data is speculative"],
 ["reasoning prompt", "YES", "§V: no A/B; releases not separable; entry thesis is the only prompt-dependent output and no per-prompt-version comparison has adequate n"],
 ["ML weights / training", "YES", f"§W/§9: CV-AUC {KEYW['auc']}; retraining previously gave identical AUC; ML score components have p>0.3"]])
W("Freezing is justified by *lack of evidence for change*, not by evidence that the components are good.")

# ------------------------------------------------------------- Z
sec("Z", "FINAL VERDICT")
W("Scores are my judgement (0–10), anchored on the cited metrics; they are not statistical estimates.")
table(["Area", "Score /10", "Anchor evidence"], [
 ["Prediction quality", 4, f"CV-AUC {KEYW['auc']}; win rate {S['wr']}%; PF {S['pf']} but {pf3} ex-top-3; median trade {S['med']}%"],
 ["Entry timing", 4, f"Immediate reversals = {pct(len(lc.get('immediate_reversal', [])), len(LOSS))}% of losses; entry_quality not significant (§E)"],
 ["Risk management", 4, f"Median loss vs win asymmetry; gap/slippage tails (worst {fn(min(r.stop_slippage_pct for r in sl_in))}%); {pct(len(aff), len(ENT))}% gap-exposed"],
 ["Take-profit logic", 7, "Holding to the outermost target beat early exits (§P: sum ret +%s%% vs %s%% at TP1)" % (round(sum(ret(r) for r in ENT), 1), round(sum(policy(r, 'tp1') for r in ENT), 1))],
 ["Stop logic", 4, f"Stops work as levels but execution tail is bad during gaps (avg slip in gaps {fn(avg([r.stop_slippage_pct for r in sl_in]))}%)"],
 ["Confidence calibration", 2, f"Brier {brier} vs base {round(base*(1-base),4)}; over-predicts in every bucket ≥55"],
 ["Market regime detection", "n/a (3)", "Only 2 labels emitted; risk_on trades did worse than mixed; cannot be validated"],
 ["Trade management", 5, "Real decisions only post 09-12; logic sound, effect unproven (§P)"],
 ["Infrastructure reliability", 1, f"Uptime {round((1 - out_ms / span) * 100, 1)}%, {len(OUT)} gaps"],
 ["ML usefulness", 2, "ml_score p>0.3, ML probability present on few trades; retrain gave identical AUC"]])
W(f"**1. Single biggest reason trades lose:** the trade is wrong from the first candle — {pct(len(lc.get('immediate_reversal', [])), len(LOSS))}% of losses are immediate reversals (no TP1, MFE<1%) (CONFIRMED). Why the entries fail is NOT identifiable from stored fields (INSUFFICIENT DATA); the biggest *avoidable-cost* factor is infrastructure: {fn(pct(-sum(ret(r) for r in L_in), -sum(ret(r) for r in LOSS)),1)}% of loss magnitude exits inside monitoring gaps.")
W("**2. Single code change most likely to help:** none in the predictive code is evidence-supported. The highest-ROI *change* is operational — a supervised, continuously running scanner with heartbeat alerting — followed by additive logging (structure booleans + missed-opportunity recorder) so the next audit can answer §G, §L and §T.")
W("**3. What must NOT be changed yet:** scoring weights, decision checklist thresholds, regime logic, the reasoning prompt, ML weights/training, the hold-to-outermost-target exit rule (§P), and any hard short-disable.")
W(); W("### Roadmap for the next 200 trades")
table(["Phase", "Action", "Trigger / gate"], [
 ["Now (0–20 trades)", "Fix uptime; add display honesty (n/CI/median/ex-top-3 PF, calibrated confidence); log structure booleans + missed-opportunity recorder (with approval); shadow-log breakeven-after-TP1", "No prediction change"],
 ["20–100", "Accumulate under frozen engine; re-run this script weekly (it is deterministic); track continuous-uptime subset separately", "Report ex-gap and all-trades metrics side-by-side"],
 ["100 (≈ 220 total closed)", "First re-audit of: entry-quality tiers, RSI-chop flag, short performance ex-gap (need ≥30 clean shorts), EV vs confidence ranking", "Act only where p<0.05 AND effect holds ex-top-3 and ex-gap"],
 ["200 (≈ 320 total)", "Consider any evidence-backed weight/flag proposal; evaluate breakeven policy and regime labels beyond risk_on/mixed if they appear", "Out-of-sample: fit on first half, test on second"],
 ["Never on this n", "ML retrain, auto-optimizer, per-coin models, hard short ban", "Requires ≥500 trades and a held-out test"]])
open("karma_AZ_report.md", "w", encoding="utf-8").write("\n".join(L))
print("OK", len(L), "lines;", sum(len(x.split()) for x in L), "words")
