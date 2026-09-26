"""Karma V3.0 implementation-plan report (Parts 1-12). READ ONLY: no code/DB/prompt/weight/model change.
Reuses all loaders/helpers/simulators by executing analysis_karma_engineering.py (which itself reuses the earlier scripts)."""
import io, contextlib
_e = open("analysis_karma_engineering.py", encoding="utf-8").read()
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(_e, "eng", "exec"))
L.clear()
from scipy.stats import beta as _b2

NOWS = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
N = len(ENT); base = len(WINS) / N
half_t = (ALL_SORTED[len(ALL_SORTED) // 2].entry_time or ALL_SORTED[len(ALL_SORTED) // 2].created_at)
def first_half(r): return (r.entry_time or r.created_at) < half_t
def sharpe(rs): return round(statistics.mean(rs) / statistics.pstdev(rs), 3) if len(rs) > 2 and statistics.pstdev(rs) > 0 else None
def ddx(rows, vals):
    o = sorted(zip([r.exit_time or 0 for r in rows], vals)); c = p = m = 0
    for _, v in o: c += v; p = max(p, c); m = min(m, c - p)
    return round(m, 1)

W("# Karma V3.0 — Implementation Plan from Evidence (Parts 1–12)")
W()
W(f"Generated {NOWS} from `crypto_terminal.db`, read-only. Live: {len(ALL)} plans, **{N} closed ({len(WINS)}W/{len(LOSS)}L)**, win rate {round(base*100,1)}%, PF {summ(ENT)['pf']}, avg {summ(ENT)['avg']}%, median {summ(ENT)['med']}%. "
  "**No code, DB row, prompt, weight or model was changed, and no commit was made.** Part 12 contains *proposed* code only for files that are not frozen; nothing touching scoring.py / decision.py / market_regime.py / prompt / ML is proposed, because the evidence below does not support it. "
  f"Labels: CONFIRMED (p<.01, n≥30) · LIKELY (p<.05) · POSSIBLE (p<.15) · NOT SUPPORTED (adequate n, p≥.15) · INSUFFICIENT DATA. Chronological validation = fit on the earlier half of trades (by entry time, n≈{N // 2}), test on the later half; all p-values are optimistic because trades cluster in time.")

# ================================================================= 0. verify pasted claims
sec("0", "VERIFICATION OF THE RECOMMENDATION YOU PASTED (against the DB)")
tp1r = [r for r in ENT if r.tp1_hit]; n1 = len(tp1r); t2 = [r for r in tp1r if r.tp2_hit]; t3 = [r for r in tp1r if r.tp3_hit]
l_after = [r for r in tp1r if r.status == "closed_loss"]
b7074 = [r for r in ENT if r.confidence is not None and 70 <= r.confidence < 75]; b6064 = [r for r in ENT if r.confidence is not None and 60 <= r.confidence < 65]; b5559 = [r for r in ENT if r.confidence is not None and 55 <= r.confidence < 60]
SHT = [r for r in ENT if r.direction == "short"]; LG = [r for r in ENT if r.direction == "long"]
gate_ex = [r for r in SHT if r.entry_quality == "excellent"]; gate_rel = [r for r in SHT if RELP[r.id] >= 60]
rel_ge60 = sum(1 for r in ENT if RELP[r.id] >= 60)
cal_max = max(summ([r for r in ENT if r.confidence is not None and a <= r.confidence < b])["wr"] or 0 for a, b in [(50, 55), (55, 60), (60, 65), (65, 70), (70, 75)])
table(["Claim in the pasted text", "What the DB says", "Verdict"], [
 ["118 closed, 45W/71L, PF 1.70, avg +2.58%, median −1.59%", f"{N} closed, {len(WINS)}W/{len(LOSS)}L, PF {summ(ENT)['pf']}, avg {summ(ENT)['avg']}%, median {summ(ENT)['med']}% (moves as new trades close)", "Consistent (slightly older snapshot)"],
 ["After TP1: reached TP2 46/52 (88%)", f"{len(t2)}/{n1} ({fn(pct(len(t2), n1),1)}%) reached TP2", "TRUE"],
 ["After TP1: reached TP3 14/52 (27%)", f"{len(t3)}/{n1} ({fn(pct(len(t3), n1),1)}%) reached TP3 (= {fn(pct(len(t3), len(t2)),1)}% of TP2 reachers)", "TRUE"],
 ["'Returned to stop: 5 trades'", f"{len(l_after)} of {n1} TP1-reachers ended as losses ({fn(pct(len(l_after), n1),1)}%)", f"Understated ({len(l_after)}, not 5)"],
 ["Calibration example: 71% → 56% ± 8%; 64% → 44% ± 9%; 58% → 28% ± 10%",
  f"Observed win rate: 70–74 bucket = {fn(summ(b7074)['wr'],1)}% (n={len(b7074)}); 60–64 = {fn(summ(b6064)['wr'],1)}% (n={len(b6064)}); 55–59 = {fn(summ(b5559)['wr'],1)}% (n={len(b5559)}). Higher confidence does NOT map to higher win rate: 58→~32%, 64→~46%, 71→~33%", "FALSE — the example mapping is monotone and invented; the data is flat/non-monotone"],
 ["Expected Outcome card: TP1 68%, TP2 49%, TP3 17%, Stop 32%", f"Unconditional (all {N} entered trades): TP1 {fn(pct(n1, N),1)}%, TP2 {fn(pct(sum(1 for r in ENT if r.tp2_hit), N),1)}%, TP3 {fn(pct(sum(1 for r in ENT if r.tp3_hit), N),1)}%, Stop {fn(pct(sum(1 for r in ENT if r.stop_hit), N),1)}%", f"FALSE — TP1 is ~{fn(pct(n1, N),0)}%, not 68%; stops are ~{fn(pct(sum(1 for r in ENT if r.stop_hit), N),0)}%, not 32%"],
 ["Short gates: Excellent entry + reliability ≥60 + calibrated p ≥55%", f"Shorts that are 'excellent': {len(gate_ex)} of {len(SHT)}; shorts with prior-trades reliability ≥60: {len(gate_rel)}; trades (any direction) with reliability ≥60: {rel_ge60} of {N}; highest observed win rate in ANY confidence bucket ≥50: {cal_max}% → calibrated p ≥55% is met by essentially nothing", "As written, the gates = disable shorts (no evidence that is warranted, see Part 4)"],
 ["Trend dominates bad trades", f"Trend ≥22 is present in {fn(pct(sum(1 for r in LOSS if r.trend_score>=22), len(LOSS)),1)}% of losses AND {fn(pct(sum(1 for r in WINS if r.trend_score>=22), len(WINS)),1)}% of wins; trend has no relation to outcome (OR {F2['Trend ≥ 22']['OR']}, p={F2['Trend ≥ 22']['p']}). It is a near-universal gate, so it cannot 'dominate' losers more than winners", "Not supported (trend is uninformative, not harmful)"],
 ["Short strategy is fundamentally underperforming — Very High", f"Headline {fn(summ(SHT)['wr'],1)}% win (n={len(SHT)}), but {sum(1 for r in SHT if in_outage(r.exit_time))}/{len(SHT)} shorts exited inside scanner downtime and all lost; uptime-only shorts win {fn(summ([r for r in SHT if not in_outage(r.exit_time)])['wr'],1)}% (n={len([r for r in SHT if not in_outage(r.exit_time)])}) vs longs {fn(summ([r for r in LG if not in_outage(r.exit_time)])['wr'],1)}%", "Overstated — confounded with downtime; POSSIBLE at most"],
 ["Trade management is better than entry prediction — Very High", "Holding to the outermost target beats exiting at TP1/TP2 (Part 11: CONFIRMED arithmetic). But every proposed *new* management rule is unproven (Part 5/11); the path-replay gains are largely fill-idealisation (previous report §9)", "Half-true: 'hold' is validated, 'smarter management' is not"]])
W("Bottom line of this check: the *direction* of two priorities is right (calibration display; do not exit at TP1), but three numbers in the pasted text (the calibration mapping, the Expected-Outcome card, the short gates) are not supported by — and in places contradicted by — the database.")

# ================================================================= PART 1
sec("PART 1", "ROOT CAUSE ANALYSIS — ONE PRIMARY VERDICT PER CLOSED TRADE")
def near_miss(r): return TRUTH[r.id] == "near_miss_early_stop"
def momentum_exh(r): return (ei(r).get("rsi14") or 0) >= 70 or (ei(r).get("mfi") or 0) > 80 or (ei(r).get("stoch_rsi") or 0) > .9 or abs(ei(r).get("atr_distance_to_ema20") or 0) > 2.5
def liq_vol(r): return (r.liquidity_score or 0) < 0 or (atr_pct(r) is not None and atr_pct(r) >= float(atr_t[1]) and r.status == "closed_loss" and (r.stop_slippage_pct or 0) <= -2)
def trend_fail(r): return (r.trend_score or 99) < 18 or btc_al(r) is False
def verdict2(r):
    if r.status == "closed_win":
        if (r.max_drawdown_pct or 0) >= -2: return "Perfect Trade"
        if TRUTH[r.id] == "good_entry_bad_exit": return "Good Entry Bad Exit"
        return "Unknown"
    if r.stop_slippage_pct is not None and r.stop_slippage_pct <= -5: return "Infrastructure Failure"
    if in_outage(r.exit_time): return "Scanner Gap"
    if r.tp1_hit: return "TP Management Failure"
    if near_miss(r): return "Good Entry Early Stop"
    if liq_vol(r): return "Liquidity / Volatility Failure"
    if momentum_exh(r): return "Momentum Exhaustion"
    if (r.structure_score or 99) < 9: return "Structure Failure"
    if trend_fail(r): return "Trend Failure"
    if LIFE[r.id] == "immediate_reversal": return "Bad Entry"
    return "Unknown"
V2 = {r.id: verdict2(r) for r in ENT}
vg = collections.defaultdict(list)
for r in ENT: vg[V2[r.id]].append(r)
rows = []
for k, v in sorted(vg.items(), key=lambda kv: sum(ret(r) for r in kv[1])):
    x = summ(v); top = ", ".join(f"{s}×{c}" for s, c in collections.Counter(r.symbol for r in v).most_common(5))
    rows.append([k, len(v), f"{x['wr']}%", fn(x["avg"]), fn(x["med"]), fn(sum(ret(r) for r in v), 1), top])
table(["Verdict", "n", "Win rate", "Avg ret%", "Median ret%", "Total PnL contribution pp", "Top 5 symbols"], rows)
W("**Assignment rules (first match wins; rules are mine and listed so they can be audited):** wins: Perfect Trade = MAE ≥ −2%; Good Entry Bad Exit = Trade-Truth verdict; else Unknown. Losses, in this priority: Infrastructure Failure (stop slippage ≤ −5%) → Scanner Gap (exit inside a monitoring gap) → TP Management Failure (TP1 had been reached) → Good Entry Early Stop (MFE ≥80% of TP1 distance, then stopped) → Liquidity/Volatility (thin book, or top-tercile ATR% with ≥2% slippage) → Momentum Exhaustion (RSI≥70 / MFI>80 / StochRSI>0.9 / >2.5 ATR from EMA20) → Structure Failure (structure_score<9) → Trend Failure (trend_score<18 or against BTC trend) → Bad Entry (immediate reversal not otherwise explained) → Unknown. "
  "**Important caveat:** because the priority order decides who gets the label, and 'structure<9' is true of ~62% of ALL trades, the *Structure Failure* count reflects that base rate as much as causation — see the base-rate column below. Verdict = classification of what the stored fields show, not proof of cause.")
cause_base = {"Structure Failure": lambda r: (r.structure_score or 99) < 9, "Trend Failure": trend_fail, "Momentum Exhaustion": momentum_exh, "Liquidity / Volatility Failure": liq_vol}
table(["Trait behind the label", "Share of ALL closed trades with it", "Share of LOSSES with it", "Share of WINS with it", "Lift (loss share ÷ win share)"], [[k, f"{fn(pct(sum(1 for r in ENT if f(r)), N),1)}%", f"{fn(pct(sum(1 for r in LOSS if f(r)), len(LOSS)),1)}%", f"{fn(pct(sum(1 for r in WINS if f(r)), len(WINS)),1)}%", ("inf (0 wins have it)" if sum(1 for r in WINS if f(r)) == 0 else fn((sum(1 for r in LOSS if f(r)) / len(LOSS)) / (sum(1 for r in WINS if f(r)) / len(WINS)), 2))] for k, f in cause_base.items()])
W("**Read the lift column:** Trend Failure and Momentum Exhaustion traits are MORE common among winners than losers (lift < 1), so labelling a loss with them is descriptive, not causal; only Liquidity/Volatility (n=3 wins-free) leans toward losses and its n is tiny.")
W(f"Open trades ({sum(1 for r in ALL if r.status=='open')} open, {sum(1 for r in ALL if r.status=='pending')} pending) are excluded from every statistic above and are analysed separately in Part 9. **Evidence:** the counts are facts (CONFIRMED); causal interpretation of any label is POSSIBLE at best. Infrastructure Failure + Scanner Gap together carry {fn(pct(-sum(ret(r) for k in ('Infrastructure Failure','Scanner Gap') for r in vg.get(k,[])), -sum(ret(r) for r in LOSS)),1)}% of total loss magnitude.")

# ================================================================= PART 2
sec("PART 2", "SCORING MODEL FROM EVIDENCE (MEASUREMENT; scoring.py UNTOUCHED)")
from app.engine.red_flags import compute_red_flags
RFS = {r.id: compute_red_flags(r.entry_indicators, r.structure_score, r.historic_probability)["red_flag_score"] for r in ENT}
CF = [("Trend", lambda r: r.trend_score >= 22, "0–25"), ("Momentum", lambda r: r.momentum_score >= 15, "0–15"), ("Volume", lambda r: r.volume_score >= 8, "0–10"), ("Structure", lambda r: r.structure_score >= 9, "0–15"),
      ("Funding", lambda r: r.funding_score >= 10, "0–10"), ("History", lambda r: r.historic_probability is not None and r.history_score > 0, "−15..+15"), ("Regime (mixed)", lambda r: r.market_regime == "mixed", "−5..+5"),
      ("Risk penalty absent", lambda r: (r.risk_score or 0) > -3, "−20..0"), ("Entry Quality excellent", lambda r: r.entry_quality == "excellent" if r.entry_quality else None, "n/a (not in score)"),
      ("EV > 0 (retro)", lambda r: EVR[r.id] > 0 if EVR[r.id] is not None else None, "n/a (not in score)"), ("Reliability ≥ median (prior-trades)", lambda r: RELP[r.id] >= relmed, "n/a (not in score)"), ("Red flags = 0", lambda r: RFS[r.id] == 0, "n/a (not in score)")]
rows = []
for nm, pr, cur in CF:
    P = [r for r in ENT if pr(r) is True]; A = [r for r in ENT if pr(r) is False]; t = two(pr, ENT)
    if not t: rows.append([nm, cur, "—", "—", "—", "—", "—", "—", "—", "INSUFFICIENT DATA", "Wait"]); continue
    # permutation importance in a one-feature logistic = AUC drop; here use AUC of the binary flag
    y = [1 if r.status == "closed_win" else 0 for r in ENT if pr(r) is not None]; xf = [1 if pr(r) else 0 for r in ENT if pr(r) is not None]
    auc = roc_auc_score(y, xf)
    rows.append([nm, cur, f"{t['nP']}/{t['nA']}", f"{fn(t['wrP'],1)}% / {fn(t['wrA'],1)}%", t["OR"], f"[{t['lo']}, {t['hi']}]", t["p"], t["ig"], round(auc, 3), gate(min(t['nP'], t['nA']), t['p']),
                 "Wait — no evidence to change" if t["p"] >= .05 else "Wait — hypothesis; re-test at n≥200 (multiple-testing)"])
table(["Component", "Current weight range", "n pass/fail", "Win% pass / fail", "OR", "95% CI", "Fisher p", "Info gain (bits)", "AUC of pass-flag", "Evidence", "Ship now?"], rows)
Xc = [("trend_score", "Trend"), ("momentum_score", "Momentum"), ("volume_score", "Volume"), ("structure_score", "Structure"), ("regime_score", "Regime"), ("risk_score", "Risk penalty"), ("liquidity_score", "Liquidity")]
def auc_of(vals): return roc_auc_score([1 if r.status == "closed_win" else 0 for r in ENT], vals)
rgx = np.random.default_rng(4); ys = np.array([1 if r.status == "closed_win" else 0 for r in ENT])
def boot_auc(v):
    v = np.array(v, float); out = []
    for _ in range(400):
        i = rgx.integers(0, N, N)
        if 0 < ys[i].sum() < N: out.append(roc_auc_score(ys[i], v[i]))
    return np.percentile(out, [2.5, 97.5])
tot = [r.score for r in ENT]; a_tot = auc_of(tot); ci_tot = boot_auc(tot)
W(f"Discrimination of the *current total score* on win/loss: AUC {round(a_tot,3)} (bootstrap 95% CI [{round(float(ci_tot[0]),3)}, {round(float(ci_tot[1]),3)}]); 0.5 = no skill. Note range restriction: only trades that already passed the score/gate are observed, which attenuates every feature's apparent value.")
W(f"**Interpretation:** the total score has AUC {round(a_tot,3)} against win/loss (CI includes 0.5; later-half AUC is below 0.5), i.e. it does not separate winners from losers in this sample (LIKELY no skill; range-restricted). That is a statement about the score as a *win/loss* ranker; it may still order *magnitudes* (Spearman above is also ~0).")
W("**Proposed NEW weight table:**"); W()
table(["Component", "Current", "Proposed", "Evidence", "Confidence", "Ship now or wait"], [[c[0], c[2], "unchanged", f"OR {r[4]} p={r[6]} n={r[2]}", r[9], "WAIT"] for c, r in zip(CF, rows) if c[2] != "n/a (not in score)"] +
      [["EV / Reliability / Entry Quality / Red flags", "not in score", "keep OUT of score", "EV is anti-predictive of TP2/stop (rho −0.25, p≈0.02); reliability & EQ not significant", "LIKELY (EV); NOT SUPPORTED (others)", "WAIT (display-only)"]])
W("**Proposed weights: none change.** No component meets 'significant AND adequately sampled'. I will not fabricate a weight table (the earlier V2.1 attempt at invented weights was reverted for exactly this reason).")
# experiments requested: trend variants
def rescored(r, tw): return r.score - r.trend_score + r.trend_score * tw / 25.0
rows = []
for nm, f in [("Current score", lambda r: r.score), ("Trend weight 25→18", lambda r: rescored(r, 18)), ("Trend weight 25→15", lambda r: rescored(r, 15)), ("Trend removed from score (gate only)", lambda r: r.score - r.trend_score),
              ("Structure only", lambda r: r.structure_score), ("Score − trend + 2×structure (trend as gate, structure emphasised)", lambda r: r.score - r.trend_score + 2 * r.structure_score)]:
    v = [f(r) for r in ENT]; a = auc_of(v); ci = boot_auc(v); sp = spearmanr(v, [ret(r) for r in ENT])
    v1 = [f(r) for r in ALL_SORTED if first_half(r)]; y1 = [1 if r.status == "closed_win" else 0 for r in ALL_SORTED if first_half(r)]; v2 = [f(r) for r in ALL_SORTED if not first_half(r)]; y2 = [1 if r.status == "closed_win" else 0 for r in ALL_SORTED if not first_half(r)]
    rows.append([nm, round(a, 3), f"[{ci[0]:.3f}, {ci[1]:.3f}]", f"{roc_auc_score(y1, v1):.3f} / {roc_auc_score(y2, v2):.3f}", round(sp.statistic, 3), round(sp.pvalue, 3)])
table(["Experiment (analytics only; NOT implemented)", "AUC vs win/loss (n=%d)" % N, "Bootstrap 95% CI", "AUC 1st half / 2nd half", "Spearman vs return", "p"], rows)
gts = []
for th in (0, 18, 20, 22):
    S_ = [r for r in ENT if r.trend_score >= th]; gts.append([f"Trend gate: trend_score ≥ {th}"] + statline(S_) + [f"{fn(summ([r for r in S_ if first_half(r)])['pf'])} / {fn(summ([r for r in S_ if not first_half(r)])['pf'])}"])
table(["Is trend mandatory? (gate)"] + SH + ["PF 1st / 2nd half"], gts)
W("**Answers:** *Trend mandatory?* Every published plan already has trend ≥12.8 (median 20.1); tightening the gate to ≥22 removes ~64% of trades with no PF gain in the later half → NOT SUPPORTED. *Trend weight 25→18 / 25→15?* the AUC differences are within the bootstrap CI (indistinguishable) → NOT SUPPORTED; *Trend gate + Structure?* structure adds nothing detectable (AUC CI spans 0.5). **Do not ship any trend/weight change**; all rows are in-sample and range-restricted.")

# ================================================================= PART 3
sec("PART 3", "CONFIDENCE CALIBRATION V2")
CT = [r for r in ENT if r.confidence is not None]
bk = [(0, 45, "<45"), (45, 50, "45–49"), (50, 55, "50–54"), (55, 60, "55–59"), (60, 65, "60–64"), (65, 70, "65–69"), (70, 75, "70–74"), (75, 200, "75+")]
rows = []
for a, b, lb in bk:
    sub = [r for r in CT if a <= r.confidence < b]
    if not sub: rows.append([lb, 0] + [""] * 9); continue
    x = summ(sub); lo, hi = _b2.ppf(.025, 1 + x["w"], 1 + x["l"]) * 100, _b2.ppf(.975, 1 + x["w"], 1 + x["l"]) * 100
    rows.append([lb, x["n"], fn(avg([r.confidence for r in sub]), 1), f"{x['wr']}%", *tpm(sub), fn(x["avg"]), fn(x["pf"]), f"{lo:.0f}–{hi:.0f}", fn(avg([r.confidence for r in sub]) - x["wr"], 1)])
table(["Bucket", "n", "Mean raw conf", "Observed win%", "TP1%", "TP2%", "TP3%", "Stop%", "Expected return %", "PF", "95% credible interval", "Overconfidence pp"], rows)
W("The requested 40–45 / 45–50 buckets contain only %d and %d trades, and there are none above 75 except one at 76 — those cells are INSUFFICIENT DATA." % (sum(1 for r in CT if r.confidence < 45), sum(1 for r in CT if 45 <= r.confidence < 50)))
CTs = sorted(CT, key=lambda r: r.entry_time or r.created_at); h = len(CTs) // 2; trn, tst = CTs[:h], CTs[h:]
def fit_pav(rows_):
    grp = collections.defaultdict(lambda: [0, 0])
    for r in rows_: k = int(min(max(r.confidence, 50), 70) // 5 * 5); grp[k][0] += r.status == "closed_win"; grp[k][1] += 1
    ks = sorted(grp); blocks = [[k, grp[k][0], grp[k][1]] for k in ks]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][1] / blocks[i][2] > blocks[i + 1][1] / blocks[i + 1][2]:
            blocks[i] = [blocks[i][0], blocks[i][1] + blocks[i + 1][1], blocks[i][2] + blocks[i + 1][2]]; del blocks[i + 1]; i = max(i - 1, 0)
        else: i += 1
    return blocks
def apply_pav(blocks, prior, conf, k=10):
    c = int(min(max(conf, 50), 70) // 5 * 5); best = blocks[0]
    for b in blocks:
        if b[0] <= c: best = b
    return (best[1] + k * prior) / (best[2] + k)
prior_tr = sum(1 for r in trn if r.status == "closed_win") / len(trn); blocks = fit_pav(trn)
def brier(rows_, f): return round(sum((f(r) - (r.status == "closed_win")) ** 2 for r in rows_) / len(rows_), 4)
lg_ = LogisticRegression(C=1e4, max_iter=500).fit(np.array([[r.confidence] for r in trn], float), [1 if r.status == "closed_win" else 0 for r in trn])
table([f"Chronological test on the later {len(tst)} trades (fit on earlier {len(trn)})", "Brier (lower=better)"], [["Raw confidence ÷ 100 (current)", brier(tst, lambda r: r.confidence / 100)], [f"Pasted example (monotone 'conf−15pp' style mapping)", brier(tst, lambda r: max(0.05, min(0.95, (r.confidence - 15) / 100)))],
      [f"Constant = earlier-half win rate ({round(prior_tr*100,1)}%)", brier(tst, lambda r: prior_tr)], ["Monotone bucket map (pool-adjacent-violators) + shrinkage k=10", brier(tst, lambda r: apply_pav(blocks, prior_tr, r.confidence))], ["1-variable logistic on confidence", brier(tst, lambda r: float(lg_.predict_proba([[r.confidence]])[0][1]))]])
allblocks = fit_pav(CTs); prior_all = base
W("**Fitted monotone map on ALL trades (for display, shrinkage k=10 toward the pooled win rate):**"); W()
table(["Raw confidence range", "Trades pooled", "Calibrated P(win)", "95% credible interval"], [[f"≥{b[0]}" if i == len(allblocks) - 1 else f"{b[0]}–{allblocks[i+1][0]-1}", b[2], f"{apply_pav(allblocks, prior_all, b[0])*100:.0f}%", f"{_b2.ppf(.025, 1+b[1], 1+b[2]-b[1])*100:.0f}–{_b2.ppf(.975, 1+b[1], 1+b[2]-b[1])*100:.0f}%"] for i, b in enumerate(allblocks)])
slope = float(lg_.coef_[0][0])
W(f"Because the data is non-monotone, pool-adjacent-violators pools most buckets into one block — i.e. the honest calibration function is **almost flat at ≈{round(prior_all*100)}%**. Logistic slope on the earlier half: {round(slope,4)} per point. Chronological Brier: every mapping that simply lowers the level beats raw confidence (the pasted 'conf−15pp' example, the monotone map and the logistic all score ~0.25–0.26 vs raw 0.318), **but all of them lose to a constant at the base rate (0.235)** — i.e. the rank structure of confidence adds no calibrated information; only the level correction helps (CONFIRMED level error, LIKELY no rank information). **Calibration function to return:** `p = shrunk_monotone_map(raw)` as coded in Part 12, Commit A, with a hard floor/ceiling (0.20–0.60) until n≥200 per used bucket. Evidence: CONFIRMED that raw confidence overstates (mean {fn(avg([r.confidence for r in CT]),1)}% vs {fn(base*100,1)}% observed); LIKELY that there is no usable rank information in the 50–74 range.")

# ================================================================= PART 4
sec("PART 4", "LONG VS SHORT ENGINE")
clean = [r for r in ENT if not in_outage(r.exit_time)]; SL_ = [r for r in clean if r.direction == "short"]; LL_ = [r for r in clean if r.direction == "long"]
table(["Segment"] + SH + ["TP1%", "TP2%", "Stop%", "Avg MFE", "Avg MAE", "Avg stop dist %", "Avg stop dist (ATR)"], [[nm] + statline(v) + [summ(v)["tp1"], summ(v)["tp2"], summ(v)["stop"], summ(v)["mfe"], summ(v)["mae"], fn(avg([rr(r).get("risk_to_sl_pct") for r in v]), 2), fn(avg([rr(r).get("entry_to_sl_atr") for r in v]), 2)] for nm, v in
      [("Long — all", LG), ("Short — all", SHT), ("Long — exit in uptime", LL_), ("Short — exit in uptime", SL_), ("Short — exit in gap", [r for r in SHT if in_outage(r.exit_time)])]])
tsc = two(lambda r: r.direction == "short", clean); tsa = two(lambda r: r.direction == "short", ENT)
table(FH, [frow("short vs long — all", tsa), frow("short vs long — exit in uptime only", tsc)])
W(f"**Is short alpha real after removing outage trades?** Uptime-only shorts: {fn(summ(SL_)['wr'],1)}% win, PF {fn(summ(SL_)['pf'])}, avg {fn(summ(SL_)['avg'])}% (n={len(SL_)}) vs uptime longs {fn(summ(LL_)['wr'],1)}%, PF {fn(summ(LL_)['pf'])} (n={len(LL_)}); difference p={tsc['p']}. With n={len(SL_)} the sample cannot show either alpha or its absence → **INSUFFICIENT DATA**. Note uptime longs are also weak (PF {fn(summ(LL_)['pf'])}); the engine's headline PF comes from gap-exit winners and a few huge longs.")
rows = []
for nm, get in [("RSI", lambda r: ei(r).get("rsi14")), ("ADX", lambda r: ei(r).get("adx14")), ("CMF", lambda r: ei(r).get("cmf")), ("MFI", lambda r: ei(r).get("mfi")), ("StochRSI", lambda r: ei(r).get("stoch_rsi")), ("BB %B", lambda r: ei(r).get("bb_pct")), ("Structure score", lambda r: r.structure_score), ("Volume score", lambda r: r.volume_score), ("Stop distance ATR", lambda r: rr(r).get("entry_to_sl_atr")), ("ATR%", atr_pct)]:
    sw_ = [get(r) for r in SHT if r.status == "closed_win" and get(r) is not None]; sl_ = [get(r) for r in SHT if r.status == "closed_loss" and get(r) is not None]; lw = [get(r) for r in LG if r.status == "closed_win" and get(r) is not None]; ll = [get(r) for r in LG if r.status == "closed_loss" and get(r) is not None]
    rows.append([nm, f"{fn(avg(sw_),2)} (n={len(sw_)}) / {fn(avg(sl_),2)} (n={len(sl_)})", f"{fn(avg(lw),2)} (n={len(lw)}) / {fn(avg(ll),2)} (n={len(ll)})"])
table(["Indicator (mean)", "SHORT winners / losers", "LONG winners / losers"], rows)
W("**Which indicators behave differently for shorts?** With 3 short winners (or 3 uptime winners) no per-indicator winner/loser difference among shorts is testable → INSUFFICIENT DATA; the table is descriptive only.")
sd_rows = []
for nm, rows_ in [("Short winners", [r for r in SHT if r.status == "closed_win"]), ("Short losers", [r for r in SHT if r.status == "closed_loss"]), ("Long winners", [r for r in LG if r.status == "closed_win"]), ("Long losers", [r for r in LG if r.status == "closed_loss"])]:
    sd_rows.append([nm, len(rows_), fn(med([rr(r).get("risk_to_sl_pct") for r in rows_]), 2), fn(med([rr(r).get("entry_to_sl_atr") for r in rows_]), 2), fn(med([(r.stop_slippage_pct) for r in rows_ if r.stop_slippage_pct is not None]), 2)])
table(["Stop distance by group (median)", "n", "% from entry", "In ATR", "Stop slippage %"], sd_rows)
eqr = []
for q in ("excellent", "good", "neutral"):
    for d_, rows_ in (("short", SHT), ("long", LG)):
        sub = [r for r in rows_ if r.entry_quality == q]; eqr.append([q, d_] + statline(sub))
table(["Entry quality", "Dir"] + SH, eqr)
g1 = [r for r in SHT if r.entry_quality == "excellent"]; g2 = [r for r in SHT if RELP[r.id] >= 60]; g3 = [r for r in SHT if r.entry_quality == "excellent" and RELP[r.id] >= 60]
W(f"**The pasted 3-gate short policy:** shorts that are excellent = {len(g1)}/{len(SHT)}; with reliability ≥60 = {len(g2)}/{len(SHT)}; all gates incl. calibrated ≥55% = 0 (no bucket reaches it) → the policy is a **disable** in practice, on evidence of {len(SHT)} shorts of which {sum(1 for r in SHT if in_outage(r.exit_time))} died inside downtime. Not supported.")
_st = [r for r in SHT if r.tp1_hit]
W(f"Shorts that reached TP1: {len(_st)} of {len(SHT)}; {sum(1 for r in _st if r.status=='closed_loss')} of those later ended as losses ({sum(1 for r in _st if r.status=='closed_loss' and in_outage(r.exit_time))} of them with the exit inside a monitoring gap) — a management/monitoring issue rather than an entry issue (n too small to be more than POSSIBLE). Stop distance: shorts' stops are tighter in % (median {fn(med([rr(r).get('risk_to_sl_pct') for r in SHT]),2)}% vs {fn(med([rr(r).get('risk_to_sl_pct') for r in LG]),2)}%) but similar in ATR terms ({fn(med([rr(r).get('entry_to_sl_atr') for r in SHT]),2)} vs {fn(med([rr(r).get('entry_to_sl_atr') for r in LG]),2)} ATR), so 'stops too tight' is NOT supported as the short failure mode.")
W("**Recommendation: KEEP shorts, PENALISE visibly (display only), do not restrict or disable.** Concretely: label every short 'High risk — monitoring-sensitive', keep the existing soft flag, and require a healthy heartbeat for a short to be marked *actionable*. Evidence for a hard rule: INSUFFICIENT DATA (uptime shorts n=%d). Re-decide at ≥30 uptime-exited shorts; hard restriction only if they then underperform uptime longs at p<0.05." % len(SL_))

# ================================================================= PART 5
sec("PART 5", "TRADE MANAGEMENT REWRITE")
tp1r_s = sorted(tp1r, key=lambda r: r.tp1_hit_at or 0)
def cont_stats(sub):
    t2_ = [r for r in sub if r.tp2_hit]; return [len(sub), f"{fn(pct(len(t2_), len(sub)),1)}% ({'–'.join(str(x) for x in wilson(len(t2_), len(sub)))})", f"{fn(pct(sum(1 for r in t2_ if r.tp3_hit), len(t2_)),1)}% (n={len(t2_)})", f"{fn(pct(sum(1 for r in sub if r.status=='closed_loss'), len(sub)),1)}%"]
table(["After TP1 (n=%d)" % n1, "n", "P(TP2|TP1) (Wilson)", "P(TP3|TP2)", "P(final loss)"], [["All"] + cont_stats(tp1r)] + [[nm] + cont_stats([r for r in tp1r if f(r)]) for nm, f in [("conf <60", lambda r: (r.confidence or 0) < 60), ("conf 60–64", lambda r: r.confidence is not None and 60 <= r.confidence < 65), ("conf ≥65", lambda r: (r.confidence or 0) >= 65), ("long", lambda r: r.direction == "long"), ("short", lambda r: r.direction == "short"), ("EQ excellent", lambda r: r.entry_quality == "excellent"), ("EQ neutral", lambda r: r.entry_quality == "neutral"), ("reliability ≥ median", lambda r: RELP[r.id] >= relmed), ("reliability < median", lambda r: RELP[r.id] < relmed)]])
c_ = [CONT[r.id] for r in tp1r if r.id in CONT]
re_ = [x["returned_to_entry"] for x in c_ if x.get("returned_to_entry") is not None]; rs_ = [x["returned_to_stop"] for x in c_ if x.get("returned_to_stop") is not None]
W(f"P(return to entry after TP1) = {fn(pct(sum(re_), len(re_)),1)}% (n={len(re_)} with a determinable path); P(return to stop) = {fn(pct(sum(rs_), len(rs_)),1)}% (n={len(rs_)}); maximum continuation after TP1 (best excursion): avg {fn(avg([x['continuation_after_tp1'] for x in c_ if x.get('continuation_after_tp1') is not None]),2)}%, median {fn(med([x['continuation_after_tp1'] for x in c_ if x.get('continuation_after_tp1') is not None]),2)}%.")
W("**Can the pasted rule ('recalibrated probability ≥80% → continue; 60–80% → half & trail; <60% → exit at TP1') be built?** The quantity it needs is the *conditional* probability of reaching TP2 given TP1. Using only information available at the time (expanding window of earlier TP1-reachers), I tested it:")
def prior_p(r, keyf=None):
    t0 = r.tp1_hit_at or (r.entry_time or 0)
    pr = [x for x in tp1r if x is not r and (x.exit_time or 10 ** 15) < t0 and (keyf is None or keyf(x) == keyf(r))]
    return (sum(1 for x in pr if x.tp2_hit) / len(pr), len(pr)) if len(pr) >= 10 else (None, len(pr))
def cbk(r): return None if r.confidence is None else ("<60" if r.confidence < 60 else "60–64" if r.confidence < 65 else "65+")
def tp1_ret(r): return (r.tp1 - r.entry) / r.entry * 100 * sign(r)
def mgr(r, mode):
    if not r.tp1_hit: return ret(r)
    if mode == "tp1": return tp1_ret(r)
    p, n_ = prior_p(r, cbk if mode == "bucket" else None)
    if mode in ("pooled", "bucket"): return ret(r) if (p is None or p >= .8) else tp1_ret(r)
    if mode == "rel": return ret(r) if RELP[r.id] >= relmed else tp1_ret(r)
    if mode == "mid":  # 60-80%: take half at TP1, rest as actual; <60: exit; >=80: continue
        if p is None or p >= .8: return ret(r)
        if p >= .6: return .5 * tp1_ret(r) + .5 * ret(r)
        return tp1_ret(r)
    return ret(r)
dec = collections.Counter()
for r in tp1r:
    p, n_ = prior_p(r); dec["insufficient prior data → default hold" if p is None else "≥80% → continue" if p >= .8 else "60–80% → half" if p >= .6 else "<60% → exit"] += 1
W(f"Decisions the ≥80/60–80/<60 rule would have made on the {n1} TP1-reachers (probability from earlier trades only): {dict(dec)}. The *pooled* version never leaves the 'continue' branch (P(TP2|TP1) ≈{fn(pct(len(t2), n1),0)}%). Sliced versions would trigger for confidence <60 (76.5%, n=17) and reliability ≥ median (77.8%, n=27), but their Wilson intervals (53–90% and 59–89%) include 80%, so those slices are statistically indistinguishable from the 80% line — the extra branches are NOT supported (POSSIBLE at most), and the simulation below shows the sliced rules change nothing or hurt.")
W("**Trailing-stop recommendation:** from the earlier path replay, trailing 50% of MFE after TP1 raised summed return on covered trades, but ~half of the gain sat in gap-exit trades (an idealised-fill effect) and winners-cut is a lower bound (snapshot cadence) → POSSIBLE, shadow-log only. **Break-even after TP1:** same status. **Partial exits:** cannot be tested (each trade has one recorded exit) → INSUFFICIENT DATA.")
W("**Rules I can defend from the data:** (1) After TP1, default = HOLD toward the outermost defined target (CONFIRMED: exiting at TP1 lowers summed return from %s%% to %s%% — Part 11). (2) Show P(TP2|TP1)≈%s%% (Wilson interval above) as information. (3) Do not add a <60%% exit branch — no slice supports it. (4) Shadow-log break-even and trail outcomes for every TP1 trade." % (round(sum(ret(r) for r in ENT), 1), round(sum(mgr(r, 'tp1') for r in ENT), 1), fn(pct(len(t2), n1), 0)))

# ================================================================= PART 6
sec("PART 6", "ENTRY QUALITY REWRITE")
rows = []
for q in ("excellent", "good", "neutral", "late", "exhausted"):
    sub = [r for r in ENT if r.entry_quality == q]
    rows.append([q] + (statline(sub) + [fn(med([hrs(r) for r in sub]), 1), dict(collections.Counter(LIFE[r.id] for r in sub if r.status == "closed_loss"))] if sub else ["0"] + [""] * 7))
table(["EQ"] + SH + ["Median hold h", "Loss patterns"], rows)
W(f"Excellent vs rest p={F2['Entry quality = excellent']['p']} → {gate(F2['Entry quality = excellent']['nP'], F2['Entry quality = excellent']['p'])}. `late`/`exhausted` never become trades (n=0 by construction); at scan level: {dict(qs)}. The pasted text says 'Excellent is finally outperforming' — its point estimate is better (PF {fn(summ([r for r in ENT if r.entry_quality=='excellent'])['pf'])}) but it is NOT statistically distinguishable at n={len([r for r in ENT if r.entry_quality=='excellent'])}.")
W("**New categories.** Only categories that can be computed from *pre-entry* stored fields are eligible (labels defined from what happened after entry — 'Fake Breakout', 'Liquidity Sweep' — are circular or need per-candle data that is not stored → INSUFFICIENT DATA). Tested rules, with chronological halves:")
def has(f): return lambda r: bool(f(r))
NC = [("Momentum Chase: RSI≥65 or StochRSI>0.85 or >1.5 ATR above EMA20", lambda r: (ei(r).get("rsi14") or 0) >= 65 or (ei(r).get("stoch_rsi") or 0) > .85 or (ei(r).get("atr_distance_to_ema20") or 0) * sign(r) > 1.5),
      ("Pullback Continuation: trend≥20, within 1.5% of EMA20, RSI 40–60", lambda r: r.trend_score >= 20 and abs(ei(r).get("distance_to_ema20_pct") or 99) <= 1.5 and 40 <= (ei(r).get("rsi14") or 0) <= 60),
      ("Mean-Reversion Entry: against BTC trend (dip-buy / rally-short)", lambda r: btc_al(r) is False),
      ("Late Breakout: BB%B>0.9 and >1.0 ATR above EMA20", lambda r: (ei(r).get("bb_pct") or 0) > .9 and (ei(r).get("atr_distance_to_ema20") or 0) * sign(r) > 1.0),
      ("Fake Breakout / Liquidity Sweep", None)]
rows = []
for nm, f in NC:
    if f is None: rows.append([nm, "—", "—", "—", "—", "INSUFFICIENT DATA (needs candle-level / post-entry data)"]); continue
    a = [r for r in ALL_SORTED if first_half(r) and f(r)]; b = [r for r in ALL_SORTED if not first_half(r) and f(r)]; t = two(f, ENT)
    rows.append([nm, f"{len(a)} / {fn(summ(a)['wr'],1) if a else '—'}%", f"{len(b)} / {fn(summ(b)['wr'],1) if b else '—'}%", t["OR"] if t else "—", t["p"] if t else "—", gate(t["nP"], t["p"]) if t else "INSUFFICIENT DATA"])
table(["Candidate category (pre-entry rule)", "1st half n / win%", "2nd half n / win%", "OR", "p", "Evidence"], rows)
W("Base win rate: 1st half %s%%, 2nd half %s%%. **Classification rules to keep (analytics-only labels, no gating):** the four rules above as tags; none is confirmed. The one with a notable signal ('against BTC trend' = better outcomes) is the *opposite* of what a 'Mean Reversion = risky' label would imply, so it should not be presented to users as a risk warning." % (fn(summ([r for r in ALL_SORTED if first_half(r)])['wr'], 1), fn(summ([r for r in ALL_SORTED if not first_half(r)])['wr'], 1)))

# ================================================================= PART 7
sec("PART 7", "COIN RELIABILITY ENGINE")
bysym = collections.defaultdict(list)
for r in ENT: bysym[r.symbol].append(r)
rows = []; tiers = collections.Counter()
for s_, v in sorted(bysym.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    x = summ(v); pa = 1 - _b2.cdf(base, 1 + x["w"], 1 + x["l"]); pb = 1 - pa
    tier = "Trusted" if pa >= .9 else "Avoid" if pb >= .95 else "Watch"; tiers[tier] += 1
    lo, hi = _b2.ppf(.025, 1 + x["w"], 1 + x["l"]) * 100, _b2.ppf(.975, 1 + x["w"], 1 + x["l"]) * 100
    rows.append([s_, len(v), f"{x['wr']}%", f"{(x['w'] + 10 * base) / (len(v) + 10) * 100:.1f}%", f"{lo:.0f}–{hi:.0f}", fn(x["pf"]), fn(x["avg"]), fn(x["med"]), f"{x['tp1']}%", f"{x['stop']}%", fn(RELMAP[s_]["reliability_score"], 1), tier])
table(["Symbol", "n", "Raw win%", "Bayesian win% (k=10)", "95% credible", "PF", "Avg ret", "Median ret", "TP1 freq", "Stop freq", "Reliability score", "Label"], rows)
W(f"Label rule (statistical, not arbitrary): **Trusted** if P(true win rate > pooled {round(base*100,1)}%) ≥ 0.90 under a uniform-prior Beta posterior; **Avoid** if P(below pooled) ≥ 0.95; else **Watch**. Counts: {dict(tiers)}; symbols with n≥5: {sum(1 for v in bysym.values() if len(v)>=5)}/{len(bysym)}. Chronological check: prior-trades reliability ≥ median vs outcome OR {F2['Reliability (prior-trades) ≥ median']['OR']}, p={F2['Reliability (prior-trades) ≥ median']['p']} → {gate(F2['Reliability (prior-trades) ≥ median']['nP'], F2['Reliability (prior-trades) ≥ median']['p'])}: **reliability does not yet predict later outcomes**, so present it as descriptive history with n, not as a gate.")

# ================================================================= PART 8
sec("PART 8", "MARKET REGIME INTELLIGENCE (OBSERVATIONAL; market_regime.py UNTOUCHED)")
def reg8(r):
    adx = ei(r).get("adx14"); bt = ei(r).get("btc_trend"); a = atr_pct(r); fg = r.fear_greed
    if adx is None or a is None: return None
    if fg is not None and fg <= 20 and bt == "bear": return "Panic"
    if adx >= 25 and a >= float(atr_t[1]): return "Expansion"
    if adx >= 25: return "Trending Bull" if bt == "bull" else "Trending Bear" if bt == "bear" else "Trending (BTC neutral)"
    if adx < 20 and a <= float(atr_t[0]): return "Compression"
    if adx < 20: return "Range"
    return "Mean Reversion" if (btc_al(r) is False) else "Range"
W("Rule-based labels from pre-entry stored fields (ADX, ATR% terciles, BTC trend, Fear&Greed) — not learned clusters (a k-means attempt on the score components gave silhouette 0.195, i.e. no real structure). Labels: Panic = F&G≤20 & BTC bear; Expansion = ADX≥25 & top-tercile ATR%; Trending Bull/Bear = ADX≥25 by BTC trend; Compression = ADX<20 & bottom-tercile ATR%; Range = ADX<20; Mean Reversion = ADX 20–25 and against BTC trend.")
RG8 = collections.defaultdict(list)
for r in ENT:
    k = reg8(r)
    if k: RG8[k].append(r)
table(["Regime"] + SH + ["TP1%", "Stop%"], [[k] + statline(v) + [summ(v)["tp1"], summ(v)["stop"]] for k, v in sorted(RG8.items(), key=lambda kv: -len(kv[1]))] + [[k, 0] + ["—"] * 7 for k in ("Trending Bull", "Trending Bear", "Range", "Mean Reversion", "Panic", "Expansion", "Compression") if k not in RG8])
rows = []
for k, v in RG8.items():
    for st in sorted(set(STRAT[r.id] for r in v)):
        sub = [r for r in v if STRAT[r.id] == st]
        if len(sub) >= 5: rows.append([k, st] + statline(sub))
table(["Regime", "Strategy family (n≥5 only)"] + SH, rows if rows else [["—", "no regime×strategy cell reaches n≥5", "", "", "", "", "", ""]])
rows = []
_ntest = len(RG8)
for k, v in sorted(RG8.items(), key=lambda kv: -len(kv[1])):
    t = two(lambda r, k=k: reg8(r) == k if reg8(r) else None, ENT)
    a = [r for r in ALL_SORTED if first_half(r) and reg8(r) == k]; b = [r for r in ALL_SORTED if not first_half(r) and reg8(r) == k]
    rows.append([k, len(v), t["OR"] if t else "—", t["p"] if t else "—", fn(min(1, t["p"] * _ntest), 3) if t else "—", f"{len(a)} / {fn(summ(a)['wr'],1) if a else '—'}%", f"{len(b)} / {fn(summ(b)['wr'],1) if b else '—'}%", gate(t["nP"], min(1, t["p"] * _ntest)) if t else "INSUFFICIENT DATA"])
table(["Regime (vs all other trades)", "n", "OR", "Fisher p", "Bonferroni p (x%d tests)" % _ntest, "1st half n / win%", "2nd half n / win%", "Evidence after correction"], rows)
tk = collections.Counter(r.market_regime for r in ENT)
W(f"The named regimes have workable n (12–25 each) but the labels were defined once, a priori, from the names you listed, and 6 regimes with trades are tested, so Bonferroni-corrected p is shown. **Time confound:** all 13 Trending-Bull trades fall in the later half (0 in the earlier half), so that cell cannot be chronologically validated — it may reflect one market episode rather than a regime effect. The striking cells — Trending Bull (ADX≥25 with BTC bullish) winning far LESS and Trending Bear far MORE — are consistent with the 'against-BTC-trend entries do better' finding in Part 6, which makes them a coherent hypothesis (POSSIBLE/LIKELY after correction as shown) but not a rule: they are in-sample, longs dominate the sample so 'Trending Bear' is mostly countertrend longs, and the regime×strategy cells have n<10 → INSUFFICIENT DATA for 'which strategies work inside each regime'. No change to market_regime.py is proposed. Regime labels the production engine actually emitted: {dict(tk)}.")

# ================================================================= PART 9
sec("PART 9", "OPEN TRADES HEALTH CHECK (evaluated separately; never used for optimisation)")
oa = pc.open_trade_management_analytics()["trades"]; OB = {r.id: r for r in ALL}; nowms = datetime.now(timezone.utc).timestamp() * 1000
pst = sum(1 for r in ENT if r.stop_hit and not r.tp1_hit) / N
rows = []; stale_n = 0
for t in oa:
    r = OB[t["trade_outcome_id"]]; sn = SNAP_BY_TRADE.get(r.id, []); last = sn[-1] if sn else None; age = (nowms - last.timestamp) / 86400000 if last else None
    stale = age is None or age > 1; stale_n += stale
    rows.append([r.symbol, r.direction, t["status"], last.stage if last else "—", fn(evr(r)) if evr(r) is not None else "—", fn(RELMAP.get(r.symbol, {}).get("reliability_score"), 1) if r.symbol in RELMAP else "—",
                 fn(r.historic_probability, 2) if r.historic_probability is not None else "none", fn(last.tp1_probability, 2) if last and last.tp1_probability is not None else "—", fn(last.tp2_probability, 2) if last and last.tp2_probability is not None else "—",
                 f"{pst:.2f} (pooled)", (last.management_decision if last and last.management_decision else "—"), t["recommendation"] if not stale else "STALE — do not act", fn(age, 1) if age is not None else "never"])
table(["Symbol", "Dir", "Status", "Stage", "EV(R)", "Reliability", "Historical analogue P(win)", "P(TP1)", "P(TP2)", "P(stop before TP1)", "Manager decision", "Recommendation", "Days since snapshot"], rows)
W(f"**{stale_n} of {len(oa)} open/pending trades are stale (no snapshot >1 day; median age {round(statistics.median([(nowms - SNAP_BY_TRADE[t['trade_outcome_id']][-1].timestamp)/86400000 for t in oa if SNAP_BY_TRADE.get(t['trade_outcome_id'])]),1)} days).** For those, stage/probabilities/recommendations are last-known values, not a live assessment, so I withhold Reduce/Exit/Take-TP1 calls. 'P(stop)' is the pooled historical rate (no per-trade stop-probability model exists). Immediate action: restart the scanner so every open trade is re-snapshotted, then re-run this table.")

# ================================================================= PART 10
sec("PART 10", "MISSED OPPORTUNITY ANALYSIS")
cc = collections.Counter(cat_of(x.rejection_reason) for x in SCANS)
table(["Rejection reason", "Scan rows"], [[k, v] for k, v in cc.most_common()])
W(f"Rejected scans carry no entry/stop/TP levels and no price, and the {sum(1 for r in ALL if r.status=='rejected_avoid')} avoid-grade plans have zero PredictionSnapshots. Therefore *'would TP1/TP2/stop have hit'* and **rejection accuracy cannot be computed → INSUFFICIENT DATA.** The only forward-return numbers derivable (Engineering report §14) rely on a tiny, selection-biased subset (n<15 per cell at 24–72h). I will not publish an accuracy figure; doing so would be invention. Fix = Part 12, Commit F (recorder wiring; needs approval because it touches `background_scanner.py`).")

# ================================================================= PART 11
sec("PART 11", "SIMULATION LAB (ALL %d TRADES, CHRONOLOGICAL SPLIT)" % N)
W("Every row replays the same historical trades under a rule. Rules that need a learned quantity (P(TP2|TP1), reliability) use **only trades that had already closed** at decision time (no future information). Path-based rules use recorded snapshot paths (no intra-bar wicks; fills at the rule level; fees ignored) and apply only to trades with ≥4 path points — others keep their actual result. **All rules were chosen after seeing this data → in-sample**; the half-split columns show stability, not out-of-sample proof.")
first = lambda r: first_half(r)
strategies = [
 ("Current engine", lambda r: True, lambda r: ret(r)),
 ("Tight ATR stop (1.0×)", lambda r: True, lambda r: (walk(r, stop_d=atr_pct(r)) if atr_pct(r) and atr_pct(r) < (rr(r).get("risk_to_sl_pct") or 0) else ret(r)) if covered(r) and atr_pct(r) else ret(r)),
 ("Swing stop (nearest support/resistance)", lambda r: True, lambda r: (walk(r, stop_d=stop_dist_swing(r)) if stop_dist_swing(r) and stop_dist_swing(r) < (rr(r).get("risk_to_sl_pct") or 1e9) else ret(r)) if covered(r) and stop_dist_swing(r) else ret(r)),
 ("Break-even after TP1", lambda r: True, lambda r: walk(r, be_after_tp1=True) if covered(r) else ret(r)),
 ("Trail 50% of MFE after TP1", lambda r: True, lambda r: walk(r, trail=.5) if covered(r) else ret(r)),
 ("Exit TP1 always", lambda r: True, lambda r: mgr(r, "tp1")),
 ("Continue to TP2 only if P(TP2|TP1) ≥ 80% (pooled, prior trades)", lambda r: True, lambda r: mgr(r, "pooled")),
 ("Same, conditioned on confidence bucket", lambda r: True, lambda r: mgr(r, "bucket")),
 ("Reliability-adjusted TP manager (continue only if reliability ≥ median)", lambda r: True, lambda r: mgr(r, "rel")),
 ("No shorts", lambda r: r.direction == "long", lambda r: ret(r)),
 ("Only Excellent entry quality", lambda r: r.entry_quality == "excellent", lambda r: ret(r)),
 ("Raw confidence ≥ 60", lambda r: (r.confidence or 0) >= 60, lambda r: ret(r)),
 ("Raw confidence ≥ 65", lambda r: (r.confidence or 0) >= 65, lambda r: ret(r)),
 ("Calibrated p ≥ 55% (pasted rule)", lambda r: apply_pav(allblocks, prior_all, r.confidence or 0) >= .55, lambda r: ret(r))]
rows = []; SIM = {}
for nm, sel, val in strategies:
    S_ = [r for r in ENT if sel(r)]
    if not S_: rows.append([nm, 0, "—", "—", "—", "—", "—", "—", "—", "—"]); continue
    v = [val(r) for r in S_]; ex1 = sorted(v, reverse=True)[1:]
    a_ = [val(r) for r in S_ if first(r)]; b_ = [val(r) for r in S_ if not first(r)]
    SIM[nm] = v
    rows.append([nm, len(S_), fn(pct(sum(1 for x in v if x > 0), len(v)), 1) + "%", fn(pf(v)), fn(pf(ex1)), fn(avg(v)), fn(med(v)), ddx(S_, v), fn(sharpe(v)), f"{fn(pf(a_))} / {fn(pf(b_))}"])
rank = sorted(rows, key=lambda z: -(float(z[3]) if z[3] not in ("—", None) else -1))
table(["Strategy (ranked by PF)", "n trades", "Win rate", "PF", "PF ex-best", "Avg ret%", "Median ret%", "Max DD (summed)", "Sharpe (per-trade)", "PF 1st half / 2nd half"], rank)
W("**Reading (no over-claiming):** (1) 'Exit TP1 always' is by far the worst — CONFIRMED that early exit destroys the right tail. (2) The 80%-probability TP manager is identical to the current engine in practice (its condition is almost always true) — it adds nothing measurable. (3) The reliability-adjusted manager exits many good trades early and underperforms. (4) Stop-style and break-even/trailing rows improve PF, but roughly half of that gain is gap-exit idealisation (previous report §9); treat as POSSIBLE, shadow-log. (5) 'Only Excellent' and 'No shorts' rank high on PF but rest on n=19 / 98 trades chosen post hoc; check the ex-best PF and the half-split before believing them. (6) A raw-confidence ≥65 filter shows PF 1.93 vs 1.62 and better PF in both halves, but its WIN RATE is lower (35.7% vs 39.0%) — the PF gain comes from larger winners in the 65–69 bucket (PF 2.97), while 70–74 is weak (PF 1.23, win 33%); with n=42 and no monotone bucket pattern that is POSSIBLE at best and has no calibrated-probability meaning. The pasted 'calibrated ≥55%' rule selects nothing (0 trades). **No strategy is CONFIRMED better than the current engine on out-of-sample evidence.**")

# ================================================================= PART 12
sec("PART 12", "EXACT CODE CHANGES (PROPOSED — NOT APPLIED)")
W("Only additive / non-frozen files. Frozen files (scoring.py, decision.py, market_regime.py, reasoning prompt, ML) get **no** change: the evidence in Parts 2–4 does not justify one. Each commit is small, individually revertable, and requires your explicit go-ahead. Code below is a draft to be implemented *with tests* on approval; I have not run it.")
table(["Commit", "Files", "Why (evidence)", "Expected improvement", "Risk", "Frozen files changed?"], [
 ["A — calibrated probability display", "`app/engine/calibration.py`, `app/routes/outcomes.py` serializer (display fields only)", f"Part 3: mean conf {fn(avg([r.confidence for r in CT]),1)}% vs {fn(base*100,1)}% observed; only flat/shrunk mappings beat raw on the chronological test", "Removes ~24pp overstatement from what users see; no change to trades", "Very low — display only", "No"],
 ["B — Trade Truth taxonomy V2 + KPI honesty", "`app/analytics/trade_truth.py`, `app/engine/performance_center.py`, `app/routes/performance.py`", "Part 1 verdict set; every KPI shows n, Wilson CI, median, ex-top-3 PF, gap-exposed %", "Debug/analytics quality", "Very low", "No"],
 ["C — Trade manager: 'HOLD to outermost target' default + shadow logging of BE/trail", "`app/engine/trade_manager.py` (probability display + shadow fields only), `app/analytics/stop_styles.py` (new)", "Part 5/11: exit-at-TP1 is CONFIRMED harmful; BE/trail unproven", "Evidence collection; no behaviour change", "Low", "No"],
 ["D — Reliability & Expected-Outcome card fields", "`app/analytics/reliability.py`, serializer", "Part 7; replaces EV number with observed TP1/TP2/TP3/stop rates (unconditional: TP1 %s%%, TP2 %s%%, TP3 %s%%, stop %s%%)" % (fn(pct(n1, N), 0), fn(pct(sum(1 for r in ENT if r.tp2_hit), N), 0), fn(pct(sum(1 for r in ENT if r.tp3_hit), N), 0), fn(pct(sum(1 for r in ENT if r.stop_hit), N), 0)), "Removes anti-predictive EV from the UI", "Low", "No"],
 ["E — Short 'High risk / monitoring-sensitive' badge", "`app/analytics/trade_quality.py`, serializer", "Part 4", "Honest labelling; no gating", "Low", "No"],
 ["F — Wire missed-opportunity recorder + 72h post-close price capture (**needs approval**)", "`app/engine/background_scanner.py`, `app/analytics/missed_opportunity.py`, `db_models.py` (additive)", "Part 10: rejection accuracy INSUFFICIENT DATA", "Unblocks Part 10 and 'should have continued' verdicts", "Low–Medium (touches scanner)", "**Yes — background_scanner.py**"],
 ["G — Ops: supervised always-on scanner + heartbeat alert", "deployment config only", f"Uptime ≈16%; {fn(pct(-sum(ret(r) for k in ('Infrastructure Failure','Scanner Gap') for r in vg.get(k,[])), -sum(ret(r) for r in LOSS)),0)}% of loss magnitude in gap/infra verdicts; {stale_n} stale open trades", "Largest data-quality lever", "Very low", "No"],
 ["NOT PROPOSED — C/D of the pasted plan (scoring weights, decision gates)", "scoring.py, decision.py", "Parts 2–4: no component significant; 0/12 components support a weight change; trend variants indistinguishable", "None demonstrable", "High (overfit)", "Would change frozen files — **rejected on evidence**"]])
W("**Commit A — draft code (calibration.py addition):**")
W("```python")
W('''def _pav_blocks(rows):
    """rows: [(raw_confidence, won_bool)] -> monotone non-decreasing blocks [[lo_bucket, wins, n], ...]"""
    grp = {}
    for c, won in rows:
        k = int(min(max(c, 50), 70) // 5 * 5)
        w, n = grp.get(k, (0, 0)); grp[k] = (w + bool(won), n + 1)
    blocks = [[k, w, n] for k, (w, n) in sorted(grp.items())]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][1] / blocks[i][2] > blocks[i + 1][1] / blocks[i + 1][2]:
            blocks[i] = [blocks[i][0], blocks[i][1] + blocks[i + 1][1], blocks[i][2] + blocks[i + 1][2]]
            del blocks[i + 1]; i = max(i - 1, 0)
        else:
            i += 1
    return blocks

def calibrated_probability(raw_confidence, rows, shrink_k=10, lo=0.20, hi=0.60):
    """Display-only calibrated P(win) with credible interval. NEVER feeds scoring/decision."""
    if not rows:
        return {"p": None, "interval": None, "n": 0, "evidence": "INSUFFICIENT DATA"}
    prior = sum(1 for _, w in rows if w) / len(rows)
    blocks = _pav_blocks(rows)
    c = int(min(max(raw_confidence, 50), 70) // 5 * 5)
    b = max([x for x in blocks if x[0] <= c], key=lambda x: x[0], default=blocks[0])
    p = (b[1] + shrink_k * prior) / (b[2] + shrink_k)
    p = min(max(p, lo), hi)
    a, bb = 1 + b[1], 1 + b[2] - b[1]          # Beta posterior for the interval
    from scipy.stats import beta
    return {"p": round(p, 3), "interval": [round(beta.ppf(.025, a, bb), 3), round(beta.ppf(.975, a, bb), 3)],
            "n": b[2], "evidence": "LIKELY" if b[2] >= 30 else "INSUFFICIENT DATA"}''')
W("```")
W("*Tests to write:* monotonicity of the map; empty/one-class input; interval contains p; never returns outside [0.20, 0.60]; does not import or alter scoring/decision modules; serializer adds `calibrated_probability` without changing existing fields.")
W("**Commit C — trade_manager.py behaviour:** *no change to decisions.* Add fields `p_tp2_given_tp1` (+Wilson interval, n) to the snapshot payload and log (not act on) the hypothetical BE/trail exit for every TP1 trade so the ≥200-trade re-audit can settle Part 5 with clean data.")
W("**Expected combined effect of A–E and G:** no change to trade selection or exits; what changes is honesty of displayed numbers and quality of the data collected. I am deliberately not promising a profit-factor improvement — none is demonstrated by the evidence.")
W()
W("### Sequencing")
W("1. **G** (uptime) — highest leverage, no code. 2. **A, B, D, E** — display/analytics, one at a time. 3. **C** — shadow logging. 4. **F** — only with your explicit approval (frozen scanner file). 5. Re-run this script at ≥200 closed trades; only then consider weights, decision gates, or exit-rule changes, using the chronological split shown above (fit on the first half, confirm on the second).")
open("karma_v3_plan.md", "w", encoding="utf-8").write("\n".join(L))
print("OK", len(L), "lines;", sum(len(x.split()) for x in L), "words")
