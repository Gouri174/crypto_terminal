"""Karma engineering forensic report (Sections 1-23). READ ONLY.
Reuses loaders/helpers from analysis_karma_v3_audit.py + analysis_karma_AZ.py (header part)."""
import re, itertools, json
_a = open("analysis_karma_AZ.py", encoding="utf-8").read()
exec(compile(_a[:_a.index('W(f"# Karma Archive')], "az_prefix", "exec"))
from scipy.stats import beta as _beta, binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

def cat_of(reason):
    if reason is None: return "published/active"
    r_ = reason.lower()
    if "exhausted" in r_: return "exhausted"
    if "late" in r_: return "late"
    if r_.startswith("no_trade"): return "no_trade (direction gate)"
    if "outside top" in r_: return "rank cutoff"
    return "other"
def gate(n, p):  # recommendation-grade evidence label
    if n < 10: return "INSUFFICIENT DATA"
    if p is None: return "POSSIBLE"
    return "CONFIRMED" if (p < .01 and n >= 30) else "LIKELY" if p < .05 else "POSSIBLE" if p < .15 else "NOT SUPPORTED"
NOWS = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
ENT.sort(key=lambda r: r.exit_time or 0)
ALL_SORTED = sorted(ENT, key=lambda r: r.entry_time or r.created_at)
def atr_pct(r):
    q = rr(r); e = q.get("entry_to_sl_atr"); rp = q.get("risk_to_sl_pct")
    if e and rp: return rp / e
    a = (r.level_reasoning or {}).get("atr_at_entry")
    return a / r.entry * 100 if a and r.entry else None
def path(r):
    """[(t, pnl% in trade direction)] from entry to exit, from PredictionSnapshots (+ recorded exit)."""
    t0 = r.entry_time or r.created_at; t1 = r.exit_time or 10 ** 15
    pts = [(sn.timestamp, (sn.current_price - r.entry) / r.entry * 100 * sign(r)) for sn in SNAP_BY_TRADE.get(r.id, []) if t0 <= sn.timestamp <= t1 and sn.current_price]
    if r.exit_price and r.exit_time: pts.append((r.exit_time, (r.exit_price - r.entry) / r.entry * 100 * sign(r)))
    return sorted(pts)
def gap_free(r):
    t0 = r.entry_time or r.created_at; t1 = r.exit_time
    return not any(o["start"] < t1 and o["end"] > t0 for o in OUT)
PATHS = {r.id: path(r) for r in ENT}
def covered(r): return len(PATHS[r.id]) >= 4

W("# Karma Engineering Forensic Report — Sections 1–23")
W()
W(f"Generated {NOWS} from `crypto_terminal.db`, read-only. Live counts: {len(ALL)} plans, {len(ENT)} closed ({len(WINS)}W/{len(LOSS)}L), {sum(1 for r in ALL if r.status=='open')} open, {sum(1 for r in ALL if r.status=='pending')} pending, {sum(1 for r in ALL if r.status=='invalidated')} invalidated, {sum(1 for r in ALL if r.status=='rejected_avoid')} avoided, {len(SNAPS)} PredictionSnapshots, {len(SCANS)} ScanSnapshots. (The DB grows while the scanner runs; the counts in your brief are a few days old.)")
W()
W("**Rules followed:** no code, prompt, weight, model, or DB change was made; scoring.py / decision.py / prompt / ML stay frozen. Section 23 is a *plan*; no diffs or commits were produced, because — as the evidence below shows — almost nothing predictive is proven strongly enough to justify a code change yet. "
  "Labels: CONFIRMED (p<.01, n≥30) · LIKELY (p<.05) · POSSIBLE (p<.15) · NOT SUPPORTED (adequate n, p≥.15) · INSUFFICIENT DATA (n<10 or field not stored). Fisher exact / bootstrap; p-values optimistic because trades cluster in time and by symbol.")
W()
W("**Read this first — what the archive can and cannot support:** (1) Only 118-ish resolved trades, ~46 wins, with profit concentrated in a few large longs. (2) The scanner was up only ≈16% of the calendar span, so any exit-timing / stop analysis is contaminated by monitoring gaps. (3) Rejected scans have no prices and avoided plans have no forward tracking, so 'missed opportunity' cannot be measured. (4) BOS/CHoCH/OBV/market-cap were never stored per trade. Where a requested item hinges on those, I say INSUFFICIENT DATA rather than invent it.")

# ========================================================================= 1
sec(1, "COMPLETE TRADE FORENSICS")
def verdict(r):
    L_ = r.status == "closed_loss"
    if L_ and r.stop_slippage_pct is not None and r.stop_slippage_pct <= -5: return "Infrastructure Failure"
    if L_ and in_outage(r.exit_time): return "Scanner Outage"
    if L_ and r.liquidity_score is not None and r.liquidity_score < 0: return "Low Liquidity Failure"
    if L_ and r.tp1_hit: return "TP1 Hit — Should Have Exited"
    if L_ and LIFE[r.id] == "immediate_reversal": return "Immediate Reversal"
    if L_ and ei(r).get("btc_trend") in ("bull", "bear") and ((ei(r)["btc_trend"] == "bull") != (r.direction == "long")): return "Counter Trend Entry"
    if L_ and r.structure_score is not None and r.structure_score < 9: return "Weak Structure Entry"
    if L_ and r.confidence is not None and r.confidence >= 65: return "Bad Confidence Calibration"
    if L_: return "Unknown"
    if (r.max_drawdown_pct or 0) >= -2: return "Perfect Trade"
    if TRUTH[r.id] == "good_entry_bad_exit": return "Good Entry, Bad Exit"
    return "Good Entry, Good Exit"
VD = {r.id: verdict(r) for r in ENT}
W("**Verdict rules (first match wins; losses only unless noted):** Infrastructure Failure = stop slippage ≤ −5% (price gapped through the stop); Scanner Outage = exit inside a monitoring gap; Low Liquidity = liquidity_score<0; TP1 Hit — Should Have Exited = loss after TP1 had already been reached (hindsight); Immediate Reversal = no TP1 and MFE<1%; Counter Trend = BTC trend disagrees with direction; Weak Structure = structure_score<9; Bad Confidence = confidence ≥65 on a loss; wins: Perfect = MAE ≥ −2%, otherwise Good Entry Good Exit (Good Entry Bad Exit only if Trade-Truth says so). "
  "**'TP2 Hit — Should Have Continued' cannot be assigned: no prices are recorded after a trade closes → INSUFFICIENT DATA.** 'News Event' likewise. Full per-trade rows (all stored fields, incl. snapshot counts) are in `karma_eng_ledger.csv`; the table below is the compact form.")
head = ["Symbol", "Dir", "Created", "Entered", "Exited", "Hold h", "Entry", "Stop", "TP1", "TP2", "TP3", "Conf", "Grade", "EV(R)", "Rel*", "EQ", "Regime", "Trend", "Mom", "Vol", "Struct", "Fund", "Hist", "ML prob", "Risk flags", "Red flags", "Failure pattern", "Ret%", "MFE%", "MAE%", "Slip%", "TP stage", "Snaps", "Verdict"]
led = []
for r in sorted(ENT, key=lambda r: -r.created_at):
    led.append([r.symbol, r.direction, dt(r.created_at), dt(r.entry_time), dt(r.exit_time), fn(hrs(r), 1), g6(r.entry), g6(r.stop_loss), g6(r.tp1), g6(r.tp2), g6(r.tp3), r.confidence, r.grade or "—", fn(evr(r)), fn((RELMAP.get(r.symbol) or {}).get("reliability_score"), 1),
                r.entry_quality or "—", r.market_regime or "—", fn(r.trend_score, 1), fn(r.momentum_score, 1), fn(r.volume_score, 1), fn(r.structure_score, 1), fn(r.funding_score, 1), fn(r.history_score, 1), fn(r.ml_probability, 2),
                ",".join(sorted((r.diagnostic_flags or {}).keys())) if isinstance(r.diagnostic_flags, dict) else (",".join(map(str, r.diagnostic_flags)) if r.diagnostic_flags else "—"),
                ",".join(f for f in FLAGS[r.id] if f not in ("short_direction", "outage_exit")) or "—", LIFE[r.id], fn(ret(r)), fn(r.max_runup_pct), fn(r.max_drawdown_pct), fn(r.stop_slippage_pct), tp_reached(r) if 'tp_reached' in globals() else ("TP3" if r.tp3_hit else "TP2" if r.tp2_hit else "TP1" if r.tp1_hit else "none"), len(SNAP_BY_TRADE.get(r.id, [])), VD[r.id]])
table(head, led)
with open("karma_eng_ledger.csv", "w", newline="", encoding="utf-8") as f:
    cw = csv.writer(f); cw.writerow(head); cw.writerows(led)
vc = collections.defaultdict(list)
for r in ENT: vc[VD[r.id]].append(r)
W("**Verdict leaderboard**"); table(["Verdict", "n", "% of all"] + ["Avg ret%", "Sum ret%", "Avg conf"], [[k, len(v), fn(pct(len(v), len(ENT)), 1) + "%", fn(avg([ret(r) for r in v])), fn(sum(ret(r) for r in v), 1), fn(avg([r.confidence for r in v]), 1)] for k, v in sorted(vc.items(), key=lambda kv: sum(ret(r) for r in kv[1]))])
W(f"Note: 'Perfect Trade' (MAE >= -2%) is my threshold; {len(vc.get('Perfect Trade',[]))} of {len(WINS)} wins qualify, so the label separates almost nothing among wins, and 'Good Entry, Bad Exit' requires post-exit prices that do not exist (only what Trade-Truth can infer). The informative part of this leaderboard is the loss side.")
ir = vc.get("Immediate Reversal", [])
W(f"Secondary tags among the {len(ir)} Immediate Reversals: weak structure (<9) {sum(1 for r in ir if r.structure_score<9)}, counter-BTC-trend {sum(1 for r in ir if ei(r).get('btc_trend') in ('bull','bear') and ((ei(r)['btc_trend']=='bull')!=(r.direction=='long')))}, confidence ≥65 {sum(1 for r in ir if (r.confidence or 0)>=65)}, RSI<50 {sum(1 for r in ir if (ei(r).get('rsi14') or 99)<50)}, short {sum(1 for r in ir if r.direction=='short')}. "
  f"**Finding:** the dominant verdict is Immediate Reversal (CONFIRMED as the largest bucket); infrastructure verdicts (Infrastructure Failure + Scanner Outage) carry {fn(pct(-sum(ret(r) for k in ('Infrastructure Failure','Scanner Outage') for r in vc.get(k,[])), -sum(ret(r) for r in LOSS)),1)}% of total loss magnitude.")

# ========================================================================= 2
sec(2, "FEATURE IMPORTANCE (FISHER + ODDS RATIO + CI)")
fg = [r.fear_greed for r in ENT if r.fear_greed is not None]; fgm = statistics.median(fg) if fg else None
atrs = [atr_pct(r) for r in ENT if atr_pct(r)]; atr_med = statistics.median(atrs); atr_t = np.percentile(atrs, [33.3, 66.7])
FS = [("Trend ≥ 22", lambda r: r.trend_score >= 22), ("Momentum = 15 (max)", lambda r: r.momentum_score >= 15), ("Volume ≥ 8", lambda r: r.volume_score >= 8), ("Structure ≥ 9", lambda r: r.structure_score >= 9),
      ("Funding = 10 (uncrowded)", lambda r: r.funding_score >= 10 if r.funding_score is not None else None), ("History present", lambda r: r.historic_probability is not None),
      ("Regime = mixed", lambda r: r.market_regime == "mixed" if r.market_regime else None), ("Entry quality = excellent", lambda r: r.entry_quality == "excellent" if r.entry_quality else None),
      ("Reliability (prior-trades) ≥ median", None), ("EV (retro LOO) > 0", None),
      ("Fear&Greed ≥ median (greedier)", lambda r: r.fear_greed >= fgm if r.fear_greed is not None else None),
      ("ATR% ≥ median (volatile)", lambda r: bool(atr_pct(r) >= float(atr_med)) if atr_pct(r) else None), ("Volatility percentile top tercile (ATR%)", lambda r: bool(atr_pct(r) >= float(atr_t[1])) if atr_pct(r) else None),
      ("ADX ≥ 25", lambda r: ei(r)["adx14"] >= 25 if ei(r).get("adx14") is not None else None), ("RSI 50–70", lambda r: 50 <= ei(r)["rsi14"] < 70 if ei(r).get("rsi14") is not None else None),
      ("CMF > 0", lambda r: ei(r)["cmf"] > 0 if ei(r).get("cmf") is not None else None), ("MFI > 60", lambda r: ei(r)["mfi"] > 60 if ei(r).get("mfi") is not None else None),
      ("FVG used (post-capture)", lambda r: bool(r.level_reasoning.get("fvg_used")) if r.level_reasoning else None), ("EMA20/50/200 alignment", above_all),
      ("Liquidity component < 0 (thin book)", lambda r: r.liquidity_score < 0 if r.liquidity_score is not None else None), ("Long direction", lambda r: r.direction == "long"),
      ("BTC trend agrees with direction", lambda r: ((ei(r)["btc_trend"] == "bull") == (r.direction == "long")) if ei(r).get("btc_trend") in ("bull", "bear") else None)]
def _rel_prior(r):
    t0 = r.entry_time or r.created_at; pr = [x for x in ENT if x is not r and x.exit_time and x.exit_time < t0]
    pw = sum(1 for x in pr if x.status == "closed_win") / len(pr) if len(pr) >= 10 else .39
    o = [x for x in pr if x.symbol == r.symbol]; return (sum(1 for x in o if x.status == "closed_win") + 10 * pw) / (len(o) + 10) * 100
RELP = {r.id: _rel_prior(r) for r in ENT}; relmed = statistics.median(RELP.values())
def _loo_ev(r):
    rp = rr(r).get("risk_to_sl_pct"); rw = rr(r).get("reward_to_tp1_pct")
    if not rp or rw is None: return None
    o = [x for x in ENT if x is not r]; return sum(1 for x in o if x.tp1_hit) / len(o) * rw / rp - sum(1 for x in o if x.stop_hit and not x.tp1_hit) / len(o)
EVR = {r.id: _loo_ev(r) for r in ENT}
FS[8] = (FS[8][0], lambda r: RELP[r.id] >= relmed); FS[9] = (FS[9][0], lambda r: EVR[r.id] > 0 if EVR[r.id] is not None else None)
rows2 = []; F2 = {}
for nm, pr in FS:
    t = two(pr, ENT); F2[nm] = t
    if not t: rows2.append([nm, "—", "—", "—", "—", "—", "—", "Needs more data"]); continue
    rec = "Needs more data" if min(t["nP"], t["nA"]) < 10 else ("Increase" if t["OR"] > 1 else "Reduce") if t["p"] < .05 else "Needs more data" if t["p"] < .15 else "Ignore (no detectable effect); keep as-is"
    rows2.append([nm, f"{t['nP']}/{t['nA']}", f"{fn(t['wrP'],1)}% / {fn(t['wrA'],1)}%", t["OR"], f"[{t['lo']}, {t['hi']}]", t["p"], gate(min(t['nP'], t['nA']), t['p']), rec])
table(["Feature", "n present/absent", "Win% present / absent", "OR", "95% CI", "Fisher p", "Evidence", "Recommendation"], rows2)
W("Reading the 'Increase/Reduce' labels: they are mechanical outputs of the p<.05 rule, not advice. 'Long direction: Increase' just restates that longs beat shorts, which section 4 shows is largely a downtime artefact; 'RSI 50-70: Increase' means 'the 50-70 zone did better', which is a hypothesis to shadow-test (one of ~21 tests, so ~1 false positive is expected).")
W("**Not stored, cannot be tested (INSUFFICIENT DATA):** OBV, BOS, CHoCH (per trade), market-cap bucket. Reliability here is computed only from trades that closed before entry (no look-ahead); EV is the pooled leave-one-out estimate. With ~21 features tested, expect ~1 false positive at p<.05 — treat 'Increase/Reduce' as hypotheses. "
  f"Features with p<.05: {[r[0] for r in rows2 if r[5] != '—' and float(r[5]) < .05]}.")

# ========================================================================= 3
sec(3, "SCORE CALIBRATION AUDIT AND MAPPING")
CT = [r for r in ENT if r.confidence is not None]; edges = [0, 50, 55, 60, 65, 70, 75, 200]; labs = ["<50", "50–54", "55–59", "60–64", "65–69", "70–74", "75+"]
base = sum(1 for r in CT if r.status == "closed_win") / len(CT); rowsC = []; bk = []
for (a, b), lb in zip(zip(edges[:-1], edges[1:]), labs):
    sub = [r for r in CT if a <= r.confidence < b]
    if not sub: continue
    x = summ(sub); pred = avg([r.confidence for r in sub]); bk.append((lb, len(sub), pred, x["wr"], sub))
    rowsC.append([lb, x["n"], fn(pred, 1), f"{x['wr']}%", f"{x['ci'][0]}–{x['ci'][1]}", fn(pred - x["wr"], 1), *tpm(sub), fn(x["avg"]), fn(x["pf"])])
table(["Bucket", "n", "Mean predicted %", "Observed win%", "Wilson (reliability) interval", "Calibration error pp", "TP1%", "TP2%", "TP3%", "Stop%", "Avg ret", "PF"], rowsC)
# logistic calibration
xc = np.array([r.confidence for r in CT], float); yc = np.array([1 if r.status == "closed_win" else 0 for r in CT])
mu, sd = xc.mean(), xc.std(); z = (xc - mu) / sd
m = LogisticRegression(C=1e4, max_iter=500).fit(z[:, None], yc); a0, b0 = float(m.intercept_[0]), float(m.coef_[0][0])
rg_ = np.random.default_rng(5); bs = []
for _ in range(500):
    i = rg_.integers(0, len(yc), len(yc))
    if 0 < yc[i].sum() < len(yc): bs.append(LogisticRegression(C=1e4, max_iter=500).fit(z[i][:, None], yc[i]).coef_[0][0])
blo, bhi = np.percentile(bs, [2.5, 97.5])
W(f"Logistic calibration of win on confidence (standardised): slope per +1 SD ({round(float(sd),1)} pts) = {round(b0,3)} (bootstrap 95% CI [{round(float(blo),3)}, {round(float(bhi),3)}]), intercept implies base rate {round(base*100,1)}%. **The slope's CI {'includes' if blo<0<bhi else 'excludes'} zero.**")
# time-split evaluation of candidate mappings
half = len(CT) // 2; CTs = sorted(CT, key=lambda r: r.entry_time or r.created_at); tr_, te_ = CTs[:half], CTs[half:]
def brier(rows, f): return round(sum((f(r) - (r.status == "closed_win")) ** 2 for r in rows) / len(rows), 4)
btr = sum(1 for r in tr_ if r.status == "closed_win") / len(tr_)
def pav_map(rows):
    grp = collections.defaultdict(list)
    for r in rows: grp[min(r.confidence // 5 * 5, 75)].append(1 if r.status == "closed_win" else 0)
    keys = sorted(grp); vals = [[sum(grp[k]), len(grp[k])] for k in keys]
    i = 0
    while i < len(vals) - 1:                     # pool-adjacent-violators (monotone non-decreasing)
        if vals[i][0] / vals[i][1] > vals[i + 1][0] / vals[i + 1][1]:
            vals[i] = [vals[i][0] + vals[i + 1][0], vals[i][1] + vals[i + 1][1]]; del vals[i + 1]; keys_ = keys;
            # merge key ranges
            keys = keys[:i + 1] + keys[i + 2:]; i = max(i - 1, 0)
        else: i += 1
    return keys, vals
ks, vs = pav_map(tr_)
def pav_pred(r):
    k = min(r.confidence // 5 * 5, 75); j = max([i for i, kk in enumerate(ks) if kk <= k] or [0]); return (vs[j][0] + 10 * btr) / (vs[j][1] + 10)
table(["Mapping (fit on first half chronologically, scored on second half, n_test=%d)" % len(te_), "Test Brier"], [["Raw confidence/100 (current)", brier(te_, lambda r: r.confidence / 100)], ["Constant base rate from first half (%.1f%%)" % (btr * 100), brier(te_, lambda r: btr)], ["Monotone (PAV) bucket map + shrinkage k=10", brier(te_, pav_pred)]])
W("**Proposed confidence display formula (NOT applied to scoring.py):** `display_p = clip( base_rate + slope × (confidence − mean_conf), 0.20, 0.60 )` with the constants fit on resolved trades — currently base_rate≈%.1f%%, mean_conf≈%.1f, slope≈%.4f per point (95%% CI spans zero: %s). Because the slope is statistically indistinguishable from zero, the evidence-supported version today is simply **display_p ≈ %.0f%% ± %.0f pp (Wilson) for every published trade**, with the raw confidence shown as an uncalibrated ranking score. Uses ≥200 trades to re-fit; a monotone bucket map (table above) is the fallback once buckets have n≥30." % (base * 100, mu, b0 / sd, "yes" if blo < 0 < bhi else "no", base * 100, (summ(CT)['ci'][1] - summ(CT)['ci'][0]) / 2))

# ========================================================================= 4
sec(4, "LONG VS SHORT FORENSICS")
LG = [r for r in ENT if r.direction == "long"]; SHT = [r for r in ENT if r.direction == "short"]; clean = [r for r in ENT if not in_outage(r.exit_time)]
def dl(nm, rows):
    x = summ(rows); return [nm] + statline(rows) + [x["mfe"], x["mae"], fn(avg([r.stop_slippage_pct for r in rows if r.stop_slippage_pct is not None])), *tpm(rows), fn(avg([r.structure_score for r in rows]), 1), fn(avg([r.volume_score for r in rows]), 1), fn(avg([ei(r).get("rsi14") for r in rows]), 1), fn(avg([r.funding_score for r in rows]), 1), fn(avg([atr_pct(r) for r in rows]), 2)]
DH = ["Segment"] + SH + ["MFE", "MAE", "Slip%", "TP1%", "TP2%", "TP3%", "Stop%", "Avg struct", "Avg vol", "Avg RSI", "Avg funding", "Avg ATR%"]
table(DH, [dl("Long", LG), dl("Short", SHT), dl("Long, exit in uptime", [r for r in clean if r.direction == "long"]), dl("Short, exit in uptime", [r for r in clean if r.direction == "short"]), dl("Short, exit in gap", [r for r in SHT if in_outage(r.exit_time)])])
table(["Distribution", "Long", "Short"], [["Regime", dict(collections.Counter(r.market_regime for r in LG)), dict(collections.Counter(r.market_regime for r in SHT))], ["Entry quality", dict(collections.Counter(r.entry_quality or 'none' for r in LG)), dict(collections.Counter(r.entry_quality or 'none' for r in SHT))],
      ["Timeframe", dict(collections.Counter(r.timeframe for r in LG)), dict(collections.Counter(r.timeframe for r in SHT))], ["BTC-trend agrees with direction", f"{sum(1 for r in LG if btc_al(r) is True) if 'btc_al' in globals() else '?'}", "—"]])
def btc_al(r):
    b = ei(r).get("btc_trend")
    return None if b not in ("bull", "bear") else (b == "bull") == (r.direction == "long")
table(["BTC-trend alignment", "Long n / win%", "Short n / win%"], [[lab, f"{len(a)} / {fn(summ(a)['wr'],1)}%" if a else "0", f"{len(b)} / {fn(summ(b)['wr'],1)}%" if b else "0"] for lab, a, b in [("aligned", [r for r in LG if btc_al(r) is True], [r for r in SHT if btc_al(r) is True]), ("counter-BTC", [r for r in LG if btc_al(r) is False], [r for r in SHT if btc_al(r) is False])]])
ts_all = two(lambda r: r.direction == "short", ENT); ts_cl = two(lambda r: r.direction == "short", clean)
table(["Test", "n short/long", "Win% short / long", "OR", "p"], [["All", f"{ts_all['nP']}/{ts_all['nA']}", f"{ts_all['wrP']}% / {ts_all['wrA']}%", ts_all["OR"], ts_all["p"]], ["Exit in uptime only", f"{ts_cl['nP']}/{ts_cl['nA']}", f"{ts_cl['wrP']}% / {ts_cl['wrA']}%", ts_cl["OR"], ts_cl["p"]]])
sg = [r for r in SHT if in_outage(r.exit_time)]; shd = sorted(SHT, key=lambda r: r.entry_time or r.created_at)
W(f"**Why do shorts fail?** Causal attribution by candidate: **Scanner cadence/infrastructure — LIKELY dominant**: {len(sg)}/{len(SHT)} shorts exited in a monitoring gap and {sum(1 for r in sg if r.status=='closed_loss')}/{len(sg)} lost (avg {fn(avg([ret(r) for r in sg]))}%, worst slippage {fn(min((r.stop_slippage_pct for r in sg if r.stop_slippage_pct is not None), default=None))}%); shorts that exited in uptime win {fn(summ([r for r in clean if r.direction=='short'])['wr'],1)}% (n={len([r for r in clean if r.direction=='short'])}) vs longs {fn(summ([r for r in clean if r.direction=='long'])['wr'],1)}% (p={ts_cl['p']}). "
  f"**Trend / structure / entry timing / liquidity — NOT SUPPORTED as the cause:** average structure ({fn(avg([r.structure_score for r in SHT]),1)} vs {fn(avg([r.structure_score for r in LG]),1)}), volume ({fn(avg([r.volume_score for r in SHT]),1)} vs {fn(avg([r.volume_score for r in LG]),1)}) and funding are similar to longs and the entry-quality mix is similar; RSI is lower simply because shorts are bearish setups. **Volatility differs:** shorts sit on lower-ATR% assets ({fn(avg([atr_pct(r) for r in SHT]),2)}% vs {fn(avg([atr_pct(r) for r in LG]),2)}%) and are mostly intraday ({sum(1 for r in SHT if r.timeframe=='intraday')}/{len(SHT)} vs {sum(1 for r in LG if r.timeframe=='intraday')}/{len(LG)}), so stops are tight in % terms, which makes them more gap-sensitive (POSSIBLE contributor, untested). Note the asymmetry: a short's loss is uncapped upside, so gaps hurt shorts most, and all shorts are concentrated in a short calendar window (first short {dt(shd[0].entry_time)}, last {dt(shd[-1].entry_time)}), i.e. one market episode. Regime: shorts exist only in `mixed`, so 'regime-dependent' is UNTESTABLE.")
_tb = two(lambda r: btc_al(r) is False if btc_al(r) is not None else None, LG)
W(f"**Side finding (longs):** entering long *against* the BTC trend won {_tb['wrP']}% (n={_tb['nP']}) vs {_tb['wrA']}% when aligned (n={_tb['nA']}), OR {_tb['OR']}, p={_tb['p']} -> {gate(min(_tb['nP'],_tb['nA']), _tb['p'])} (contrarian/dip-buy entries did better; hypothesis only, no code implication yet).")
W("**Short-specific decision policy (evidence-supported, no scoring change):** (1) Do NOT disable shorts (uptime-only shorts show no deficit, n small). (2) Keep the existing soft `SHORT_TIGHT_STOP`-style flag and label every short 'monitoring-sensitive'. (3) Require live heartbeat health at issuance/while open — if the scanner is not confirmed healthy the short's plan is shown as *unmonitored* (additive UI/analytics flag, not a trading rule). (4) Re-decide at ≥30 uptime-exited shorts; hard rules only if uptime-only shorts still underperform longs at p<.05. Evidence for a harder rule today: INSUFFICIENT DATA.")

# ========================================================================= 5
sec(5, "ENTRY QUALITY V2")
rows5 = []
for q in ("excellent", "good", "neutral", "late", "exhausted"):
    sub = [r for r in ENT if r.entry_quality == q]
    rows5.append([q] + (statline(sub) + [fn(med([hrs(r) for r in sub]), 1)] + tpm(sub) + [dict(collections.Counter(LIFE[r.id] for r in sub if r.status == "closed_loss"))] if sub else ["0"] + [""] * 12))
table(["EQ"] + SH + ["Median hold h", "TP1%", "TP2%", "TP3%", "Stop%", "Loss patterns"], rows5)
W("`late`/`exhausted` never appear among trades by construction (they block issuance). Their *scan-level* counts: " + str(dict(collections.Counter(x.entry_quality for x in [] ))) if False else "")
with __import__("app.db", fromlist=["engine"]).engine.connect() as c:
    from sqlalchemy import text as _t
    qs = dict(c.execute(_t("select entry_quality, count(*) from scan_snapshots group by entry_quality")).fetchall())
W(f"Scan-level entry_quality across all {len(SCANS)} scans: {qs}. **Should thresholds move?** Excellent vs rest p={F2['Entry quality = excellent']['p']} → {gate(F2['Entry quality = excellent']['nP'], F2['Entry quality = excellent']['p'])}; no evidence supports moving thresholds, and 'good' does not beat 'neutral'.")
W("**Candidate new categories** must be defined from *pre-entry* fields (defining them from the outcome would be circular). Exploratory candidates, tested with a chronological hold-out (first half = discovery, second half = confirmation):")
cand = [("trap: RSI 30–49 AND structure<9", lambda r: ei(r).get("rsi14") is not None and 30 <= ei(r)["rsi14"] < 50 and r.structure_score < 9),
        ("trap: RSI<50 AND direction short", lambda r: ei(r).get("rsi14") is not None and ei(r)["rsi14"] < 50 and r.direction == "short"),
        ("recovery: price below EMA20 but above EMA50 (pullback in trend)", lambda r: ei(r).get("distance_to_ema20_pct") is not None and ei(r).get("distance_to_ema50_pct") is not None and ((ei(r)["distance_to_ema20_pct"] < 0 < ei(r)["distance_to_ema50_pct"]) if r.direction == "long" else (ei(r)["distance_to_ema20_pct"] > 0 > ei(r)["distance_to_ema50_pct"]))),
        ("recovery: RSI 40–50 AND MACD hist > 0", lambda r: ei(r).get("rsi14") is not None and 40 <= ei(r)["rsi14"] < 50 and (ei(r).get("macd_hist") or 0) > 0)]
h1 = ALL_SORTED[:len(ALL_SORTED) // 2]; h2 = ALL_SORTED[len(ALL_SORTED) // 2:]; rows_ = []
for nm, pr in cand:
    a = [r for r in h1 if pr(r)]; b = [r for r in h2 if pr(r)]; t = two(pr, ENT)
    rows_.append([nm, f"{len(a)} / {fn(summ(a)['wr'],1) if a else '—'}%", f"{len(b)} / {fn(summ(b)['wr'],1) if b else '—'}%", t["OR"] if t else "—", t["p"] if t else "—", gate(t["nP"], t["p"]) if t else "INSUFFICIENT DATA"])
table(["Candidate", "1st half n / win%", "2nd half n / win%", "OR (all)", "p", "Evidence"], rows_)
W("Base win rate for reference: 1st half %s%%, 2nd half %s%%. **Verdict:** a candidate is only worth adding if it is bad/good in BOTH halves with adequate n; none is confirmed — Entry-Quality V2 categories are INSUFFICIENT DATA. The RSI 30-49 + weak-structure 'trap' was weak in both halves (0%% then 22%%) but with n=5 and 9, so it is POSSIBLE at best and belongs in warnings, not a new tier. The 'RSI<50 AND short' candidate reaches p=0.04 but is confounded with the outage-hit shorts (section 4) - do not treat it as an independent trap." % (fn(summ(h1)['wr'], 1), fn(summ(h2)['wr'], 1)))

# ========================================================================= 6
sec(6, "FAILURE PATTERN ENGINE V2")
FP = [("Immediate reversal", lambda r: LIFE[r.id] == "immediate_reversal"), ("Reached TP1 then stopped", lambda r: r.tp1_hit), ("Reached TP2 then reversed", lambda r: r.tp2_hit), ("Weak structure (<9)", lambda r: r.structure_score < 9),
      ("Negative CMF", lambda r: (ei(r).get("cmf") or 0) < 0), ("Overbought MFI (>80)", lambda r: (ei(r).get("mfi") or 0) > 80), ("RSI chop 30–49", lambda r: "rsi_chop_30_49" in FLAGS[r.id]), ("High ATR extension (>2.5 ATR from EMA20)", lambda r: "high_atr_extension" in FLAGS[r.id]),
      ("No historical analogue", lambda r: r.historic_probability is None), ("Scanner outage (exit in gap)", lambda r: in_outage(r.exit_time)), ("Low liquidity (component<0)", lambda r: (r.liquidity_score or 0) < 0),
      ("Counter-trend (BTC disagrees)", lambda r: btc_al(r) is False), ("Short direction", lambda r: r.direction == "short"), ("Confidence ≥65", lambda r: (r.confidence or 0) >= 65)]
rows6 = []
for nm, pr in FP:
    sub = [r for r in LOSS if pr(r)]
    if not sub: rows6.append([nm, 0, "", "", "", "", ""]); continue
    top = collections.Counter(r.symbol for r in sub).most_common(3)
    rows6.append([nm, len(sub), fn(pct(len(sub), len(LOSS)), 1) + "%", fn(avg([ret(r) for r in sub])), fn(avg([r.confidence for r in sub]), 1), dict(collections.Counter(r.entry_quality or 'none' for r in sub)), ", ".join(f"{s}×{c}" for s, c in top)])
rows6.sort(key=lambda z: -z[1]); table(["Cause (multi-label)", "n losses", "% of losses", "Avg loss%", "Avg conf", "Entry quality mix", "Most-affected coins"], rows6)
W("**News event: INSUFFICIENT DATA** (news_sentiment is stored but has no event flag; not evaluated). Frequencies overlap; ranking by frequency, the top causes are the same structural facts as before — no single stored feature explains losses beyond 'immediate reversal'.")

# ========================================================================= 7
sec(7, "WINNER PATTERN ENGINE")
BF = [("trend≥22", lambda r: r.trend_score >= 22), ("EQ excellent", lambda r: r.entry_quality == "excellent"), ("volume≥8", lambda r: r.volume_score >= 8), ("reliability≥median", lambda r: RELP[r.id] >= relmed), ("structure≥9", lambda r: r.structure_score >= 9),
      ("regime mixed", lambda r: r.market_regime == "mixed"), ("RSI 50–70", lambda r: 50 <= (ei(r).get("rsi14") or -1) < 70), ("long", lambda r: r.direction == "long"), ("CMF>0", lambda r: (ei(r).get("cmf") or -1) > 0), ("swing", lambda r: r.timeframe == "swing"), ("uptime-exit", lambda r: not in_outage(r.exit_time)), ("BTC aligned", lambda r: btc_al(r) is True)]
combos = []
for k in (1, 2, 3):
    for cs in itertools.combinations(range(len(BF)), k):
        sub = [r for r in ENT if all(BF[i][1](r) for i in cs)]
        if len(sub) >= 8 and pf([ret(r) for r in sub]): combos.append((cs, sub))
def score_combo(sub): return pf([ret(r) for r in sub]) or 0
combos.sort(key=lambda c: -score_combo(c[1]))
rows7 = [[i + 1, " + ".join(BF[j][0] for j in cs), len(sub), fn(summ(sub)["wr"], 1) + "%", fn(pf([ret(r) for r in sub])), fn(avg([ret(r) for r in sub])), fn(pf([ret(r) for r in sub if r is not max(sub, key=ret)]))] for i, (cs, sub) in enumerate(combos[:25])]
table(["#", "Combination (all must hold)", "n", "Win%", "PF", "Avg ret", "PF ex-best"], rows7)
rgp = np.random.default_rng(9); rets_ = np.array([ret(r) for r in ENT]); best_null = []
mask = {cs: np.array([all(BF[i][1](r) for i in cs) for r in ENT]) for cs, _ in combos}
for _ in range(200):
    pr_ = rgp.permutation(rets_); mx_ = 0
    for cs, mk in mask.items():
        v = pr_[mk]; g = v[v > 0].sum(); l_ = -v[v < 0].sum()
        if l_ > 0: mx_ = max(mx_, g / l_)
    best_null.append(mx_)
obs_best = score_combo(combos[0][1]); pnull = (sum(1 for x in best_null if x >= obs_best) + 1) / 201
W(f"**Multiple-comparison check:** {len(combos)} eligible combinations (n≥8). The best observed PF is {obs_best}; in 200 outcome-shuffles the best-of-{len(combos)} PF was ≥ that in {pct(sum(1 for x in best_null if x>=obs_best),200)}% of shuffles (permutation p≈{round(pnull,3)}; median null-best PF {round(float(np.median(best_null)),2)}). "
  f"**Verdict:** {'the top combination is beyond what data-mining alone would give' if pnull < .05 else 'the leaderboard is NOT distinguishable from data-mined noise — do not treat any combination as a rule'} (evidence: {'LIKELY' if pnull<.05 else 'NOT SUPPORTED'}). Note the requested 'Trend + X' combinations are all included among the 1–3-way sets.")

# ========================================================================= 8
sec(8, "TP CONTINUATION MODEL")
tp1 = [r for r in ENT if r.tp1_hit]; n1 = len(tp1)
def cont_tab(nm, keyf):
    g = collections.defaultdict(list)
    for r in tp1:
        k = keyf(r)
        if k is not None: g[k].append(r)
    rows_ = []
    for k, v in sorted(g.items(), key=lambda kv: str(kv[0])):
        t2 = [r for r in v if r.tp2_hit]; t3 = [r for r in t2 if r.tp3_hit]; c_ = [CONT[r.id] for r in v if r.id in CONT]
        re_ = [x["returned_to_entry"] for x in c_ if x.get("returned_to_entry") is not None]; rs_ = [x["returned_to_stop"] for x in c_ if x.get("returned_to_stop") is not None]
        nb = [1 for r in v if r.tp2_hit and (CONT.get(r.id, {}).get("pullback_after_tp1") or 0) > -1.0]
        rows_.append([k, len(v), f"{fn(pct(len(t2), len(v)), 1)}% ({'–'.join(str(x) for x in wilson(len(t2), len(v)))})", f"{fn(pct(len(t3), len(t2)), 1)}% (n={len(t2)})", f"{fn(pct(sum(re_), len(re_)), 1)}% (n={len(re_)})", f"{fn(pct(sum(rs_), len(rs_)), 1)}% (n={len(rs_)})", f"{fn(pct(sum(1 for r in v if r.status=='closed_loss'), len(v)), 1)}%"])
    W(f"**By {nm}**"); table([nm, "n(TP1)", "P(TP2|TP1) (Wilson)", "P(TP3|TP2)", "P(back to entry)", "P(back to stop)", "P(final loss)"], rows_)
cont_tab("overall", lambda r: "all")
cont_tab("confidence", lambda r: None if r.confidence is None else "<60" if r.confidence < 60 else "60–64" if r.confidence < 65 else "65+"); cont_tab("entry quality", lambda r: r.entry_quality)
cont_tab("trend score", lambda r: "≥22" if r.trend_score >= 22 else "<22"); cont_tab("structure", lambda r: "≥9" if r.structure_score >= 9 else "<9"); cont_tab("regime", lambda r: r.market_regime)
cont_tab("volatility (ATR% tercile)", lambda r: None if not atr_pct(r) else "low" if atr_pct(r) < atr_t[0] else "mid" if atr_pct(r) < atr_t[1] else "high"); cont_tab("direction", lambda r: r.direction)
W("**Rules (derived from the arithmetic in §9 and the tables above, all requiring caution because n(TP1)=%d):** **Exit at TP1:** NOT supported — exiting everything at TP1 lowers summed return massively (§9). **Hold to TP2:** supported as the default (P(TP2|TP1) is high in every slice with n≥10). **Trail stop:** possible (POSSIBLE; see §9 path simulation). **Move stop to entry:** inconclusive. **Partial exit:** untestable with recorded single-exit outcomes (INSUFFICIENT DATA). No slice shows a difference large enough to justify conditional rules (confidence/EQ/trend/structure/regime tables overlap within Wilson intervals)." % n1)

# ========================================================================= 9
sec(9, "DYNAMIC STOP LOSS ANALYSIS (PATH BACKTEST)")
def walk(r, stop_d=None, be_after_tp1=False, trail=None, trail_atr=None):
    """returns simulated return% or None if not simulatable. stop_d: stop distance % from entry (positive)."""
    P = PATHS[r.id]
    if not covered(r): return None
    t_tp1 = r.tp1_hit_at; mx = 0.0; tp1_on = False
    for t, p_ in P[:-1] if len(P) > 1 else P:
        if t_tp1 and t >= t_tp1: tp1_on = True
        mx = max(mx, p_)
        if stop_d is not None and p_ <= -stop_d: return -stop_d
        if be_after_tp1 and tp1_on and p_ <= 0: return 0.0
        if trail is not None and tp1_on and p_ <= mx * (1 - trail): return mx * (1 - trail)
        if trail_atr is not None and tp1_on and mx - p_ >= trail_atr: return mx - trail_atr
    return ret(r)
def stop_dist_ema20(r):
    d = ei(r).get("distance_to_ema20_pct")
    if d is None: return None
    s_ = d if r.direction == "long" else -d
    return s_ if s_ > 0.3 else None
def stop_dist_swing(r):
    lv = (r.level_reasoning or {}).get("nearest_support" if r.direction == "long" else "nearest_resistance")
    if not lv or not r.entry: return None
    d = (r.entry - lv) / r.entry * 100 * sign(r); return d if d > 0.3 else None
COV = [r for r in ENT if covered(r)]; GF = [r for r in COV if gap_free(r)]
W(f"Method: for every closed trade with ≥4 snapshots between entry and exit (covered n={len(COV)} of {len(ENT)}), replay the recorded price path under each alternative stop rule; if the rule triggers before the actual exit, the trade exits at the rule's level, else the actual result stands. Limits: snapshot path only (5-min cadence during uptime, **no intra-bar wicks, hours-long holes during outages**), exits at the stop level (no extra slippage), fees ignored. "
  f"A stop **wider than the original** cannot be replayed to a conclusion (the trade record ends at the original stop) so those are reported as *survivors with unknown outcome*. Gap-free subset (trade lifetime entirely within uptime): n={len(GF)}.")
def evalset(rows, fn_):
    rs = []; ch = 0
    for r in rows:
        v = fn_(r)
        if v is None: continue
        rs.append(v)
        if abs(v - ret(r)) > 1e-9: ch += 1
    return rs, ch
pols = [("Baseline (actual)", lambda r: ret(r) if covered(r) else None),
        ("ATR stop 1.0×", lambda r: walk(r, stop_d=1.0 * atr_pct(r)) if atr_pct(r) and 1.0 * atr_pct(r) < (rr(r).get("risk_to_sl_pct") or 0) else (ret(r) if atr_pct(r) and covered(r) else None)),
        ("ATR stop 1.5×", lambda r: walk(r, stop_d=1.5 * atr_pct(r)) if atr_pct(r) and 1.5 * atr_pct(r) < (rr(r).get("risk_to_sl_pct") or 0) else (ret(r) if atr_pct(r) and covered(r) else None)),
        ("ATR stop 2.0×", lambda r: walk(r, stop_d=2.0 * atr_pct(r)) if atr_pct(r) and 2.0 * atr_pct(r) < (rr(r).get("risk_to_sl_pct") or 0) else (ret(r) if atr_pct(r) and covered(r) else None)),
        ("EMA20 stop", lambda r: (walk(r, stop_d=stop_dist_ema20(r)) if stop_dist_ema20(r) and stop_dist_ema20(r) < (rr(r).get("risk_to_sl_pct") or 1e9) else ret(r)) if stop_dist_ema20(r) and covered(r) else None),
        ("Swing (nearest support/resistance) stop", lambda r: (walk(r, stop_d=stop_dist_swing(r)) if stop_dist_swing(r) and stop_dist_swing(r) < (rr(r).get("risk_to_sl_pct") or 1e9) else ret(r)) if stop_dist_swing(r) and covered(r) else None),
        ("Break-even after TP1", lambda r: walk(r, be_after_tp1=True)), ("Trail 50% of MFE after TP1", lambda r: walk(r, trail=0.5)), ("Trail 1×ATR after TP1", lambda r: walk(r, trail_atr=atr_pct(r)) if atr_pct(r) else None),
        ("Break-even after TP1 + Trail 50%", lambda r: walk(r, be_after_tp1=True, trail=0.5))]
def polrows(rows):
    out = []
    for nm, f_ in pols:
        rs, ch = evalset(rows, f_); base_ = [ret(r) for r in rows if f_(r) is not None]
        out.append([nm, len(rs), round(sum(rs), 1), fn(avg(rs)), fn(pf(rs)), fn(med(rs)), fn(pct(sum(1 for x in rs if x > 0), len(rs)), 1) + "%", ch, round(sum(base_), 1)])
    return out
W("**All covered trades**"); table(["Style", "n simulated", "Sum ret%", "Avg", "PF", "Median", "Win%", "Trades changed", "Baseline sum on same trades"], polrows(COV))
W("**Gap-free subset (most trustworthy paths)**"); table(["Style", "n simulated", "Sum ret%", "Avg", "PF", "Median", "Win%", "Trades changed", "Baseline sum on same trades"], polrows(GF))
sv = []
for r in LOSS:
    if not covered(r): continue
    sd0 = rr(r).get("risk_to_sl_pct")
    for nm, d in [("ATR 1.5×", 1.5 * atr_pct(r) if atr_pct(r) else None), ("ATR 2×", 2 * atr_pct(r) if atr_pct(r) else None), ("EMA20", stop_dist_ema20(r)), ("Swing", stop_dist_swing(r))]:
        if d and sd0 and d > sd0: sv.append((nm, r.id))
W("**Wider-stop survivors (loss trades that a wider stop would not have stopped at the original level; outcome after that point is unrecorded):** " + str(dict(collections.Counter(n for n, _ in sv))) + f" out of {len([r for r in LOSS if covered(r)])} covered losses. **INSUFFICIENT DATA** to say whether widening would have been better or worse.")
def decomp(rows, f_):
    d_all = d_gap = d_up = 0.0
    cut = resc = 0
    for r in rows:
        v = f_(r)
        if v is None:
            continue
        dv = v - ret(r)
        d_all += dv
        if in_outage(r.exit_time):
            d_gap += dv
        else:
            d_up += dv
        if dv < -1e-9 and r.status == "closed_win":
            cut += 1
        if dv > 1e-9 and r.status == "closed_loss":
            resc += 1
    return [round(d_all, 1), round(d_gap, 1), round(d_up, 1), cut, resc]
W("**Where does each policy's gain come from?** Delta = simulated - actual, summed over covered trades, split by whether the *actual* exit was inside a monitoring gap. A gain in the 'gap-exit' column is mostly an idealised-fill effect (a resting exchange stop would have filled at the stop level while the scanner was down) and is an **execution** benefit, not a better stop *style*.")
table(["Policy", "Delta total pp", "Delta from gap-exit trades", "Delta from uptime-exit trades", "Winners cut", "Losers rescued"], [[nm] + decomp(COV, f_) for nm, f_ in pols[1:]])
_dd = {nm: decomp(COV, f_) for nm, f_ in pols[1:]}
W(f"**Reading the table:** uptime-exit gains range from {min(v[2] for v in _dd.values())} to {max(v[2] for v in _dd.values())} pp across styles (vs a covered baseline of {round(sum(ret(r) for r in COV),1)} pp), and gap-exit gains from {min(v[1] for v in _dd.values())} to {max(v[1] for v in _dd.values())} pp. 'Winners cut' is a LOWER BOUND: the replay uses discrete snapshots, so wicks between snapshots that would have stopped a winner are invisible, which flatters tight stops. Every number is in-sample on the same trades that suggested the rule.")
W("**Answers:** Would ATR/EMA20/swing stops survive? see 'Trades changed' — tighter stops knock out trades that later won, wider ones are untestable. Trailing improves PF? and break-even after TP1 improves PF? — compare each row's PF/Sum to the baseline on the same trades. These are in-sample replays on paths with holes; **no style is CONFIRMED superior**: the gap-exit column shows how much of each headline gain is just replacing gap slippage with an idealised fill (execution, fixable by a resting exchange stop or continuous monitoring), and on the gap-free subset (see its n above) the differences are tiny. Any style with a positive uptime-only Delta is worth shadow-logging; that is POSSIBLE, not proven. The actual system's stop is Claude-chosen free text (no formula).")

# ========================================================================= 10
sec(10, "EXPECTED VALUE ENGINE VALIDATION")
POST = [r for r in ENT if evr(r) is not None]
rows10 = []
for lab, getter, S_ in [("Stored EV (post-2026-09-12)", evr, POST), ("Retro leave-one-out EV (all)", lambda r: EVR[r.id], [r for r in ENT if EVR[r.id] is not None])]:
    for tgt, fnc in [("realized return", ret), ("realized R", rR), ("TP2 reached (0/1)", lambda r: 1 if r.tp2_hit else 0), ("Stop hit (0/1)", lambda r: 1 if r.stop_hit else 0)]:
        pr_ = [(getter(r), fnc(r)) for r in S_ if fnc(r) is not None]
        if len(pr_) >= 8: sp_ = spearmanr([a for a, _ in pr_], [b for _, b in pr_]); rows10.append([lab, tgt, len(pr_), round(sp_.statistic, 3), round(sp_.pvalue, 3), gate(len(pr_), sp_.pvalue)])
        else: rows10.append([lab, tgt, len(pr_), "—", "—", "INSUFFICIENT DATA"])
table(["EV series", "Correlated with", "n", "Spearman", "p", "Evidence"], rows10)
def evb(getter, S_):
    out = []
    for a, b, nm in [(-99, 0, "EV<0"), (0, 0.5, "0–0.5R"), (0.5, 1, "0.5–1R"), (1, 99, "≥1R")]:
        sub = [r for r in S_ if getter(r) is not None and a <= getter(r) < b]
        out.append([nm] + (statline(sub) + [fn(pct(sum(1 for r in sub if r.tp2_hit), len(sub)), 1) + "%", fn(pct(sum(1 for r in sub if r.stop_hit), len(sub)), 1) + "%"] if sub else ["0"] + [""] * 7))
    return out
W("**Stored-EV buckets**"); table(["Bucket"] + SH + ["TP2%", "Stop%"], evb(evr, POST)); W("**Retro-EV buckets**"); table(["Bucket"] + SH + ["TP2%", "Stop%"], evb(lambda r: EVR[r.id], ENT))
ths = []
for t_ in (-0.5, -0.25, 0, 0.25, 0.5):
    sub = [r for r in ENT if EVR[r.id] is not None and EVR[r.id] >= t_]; ths.append([f"retro EV ≥ {t_}R", len(sub)] + statline(sub)[1:])
table(["Threshold", "n kept"] + SH[1:], ths)
_pe = [(EVR[r.id], rr(r).get("entry_to_sl_atr")) for r in ENT if EVR[r.id] is not None and rr(r).get("entry_to_sl_atr")]
_sr = spearmanr([a for a, _ in _pe], [b for _, b in _pe])
_pr = [(EVR[r.id], rr(r).get("risk_to_sl_pct")) for r in ENT if EVR[r.id] is not None and rr(r).get("risk_to_sl_pct")]
_sq = spearmanr([a for a, _ in _pr], [b for _, b in _pr])
W(f"**EV is anti-predictive of TP2/stop, not merely uncorrelated:** retro-EV vs TP2 rho=-0.25 (p=0.017) and vs stop rho=+0.24 (p=0.024): higher EV means *fewer* TP2s and *more* stop-outs (LIKELY, n=93; clustered p is optimistic). Mechanism: EV = P(TP1)*reward/risk - P(stop); P(TP1) is pooled, so EV mostly measures reward/risk, which is largest when the stop is tight. Check: Spearman(EV, stop distance in ATR) = {round(_sr.statistic,2)} (p={round(_sr.pvalue,3)}, n={len(_pe)}); vs stop distance % = {round(_sq.statistic,2)} (p={round(_sq.pvalue,3)}). **EV as currently defined should not be used to rank or size trades.**")
W("**Recommended EV thresholds: none.** No correlation with return or realized R reaches p<.05; TP2/stop correlations are significant but in the WRONG direction; and PF falls as the retro-EV threshold rises -> the EV engine is NOT validated as a selector (evidence that it is counter-productive: LIKELY); keep as displayed metadata. Stored-EV n=%d is too small (INSUFFICIENT DATA)." % len(POST))

# ========================================================================= 11
sec(11, "RELIABILITY ENGINE VALIDATION")
W("**Threshold derivation (statistical, not arbitrary):** for each symbol the posterior of its true win rate is Beta(1+wins, 1+losses) (uniform prior). Tier = the *posterior probability* that the symbol's win rate is below/above the pooled rate (%.1f%%): **Trusted** if P(above pooled) ≥ 0.90; **Caution** if P(below pooled) ≥ 0.80; **Avoid** if P(below pooled) ≥ 0.95; otherwise **Watch**. The 0.80/0.90/0.95 posterior levels are the usual decision-theory conventions (unavoidable, but they are on probability, not on raw counts), and they automatically demand more trades for stronger labels." % (base * 100))
bysym = collections.defaultdict(list)
for r in ENT: bysym[r.symbol].append(r)
rows11 = []; tiers = collections.Counter()
for s_, v in bysym.items():
    x = summ(v); w_ = x["w"]; l_ = x["l"]; pa = 1 - _beta.cdf(base, 1 + w_, 1 + l_); pb = 1 - pa
    tier = "Trusted" if pa >= .9 else "Avoid" if pb >= .95 else "Caution" if pb >= .8 else "Watch"; tiers[tier] += 1
    bayes = (w_ + 10 * base) / (len(v) + 10) * 100; lo_, hi_ = _beta.ppf(.025, 1 + w_, 1 + l_) * 100, _beta.ppf(.975, 1 + w_, 1 + l_) * 100
    rows11.append([s_, len(v), f"{x['wr']}%", fn(bayes, 1) + "%", f"{lo_:.0f}–{hi_:.0f}", fn(x["avg"]), fn(x["pf"]), fn(pa, 2), tier])
rows11.sort(key=lambda z: (-z[1], z[0])); table(["Symbol", "n", "Raw win%", "Bayesian win% (k=10)", "95% credible interval", "Avg ret", "PF", "P(above pooled)", "Tier"], rows11)
W(f"Tier counts: {dict(tiers)}; symbols with n≥5: {sum(1 for v in bysym.values() if len(v)>=5)} of {len(bysym)}. **Validation:** because per-symbol n is 1–4 for almost all coins, the derived thresholds can fire only for the few multi-trade symbols; the engine is a *shrinkage display* and is NOT validated as predictive (a within-sample rank correlation is hindsight-inflated; the look-ahead-safe version has Spearman p={round(spearmanr([RELP[r.id] for r in ENT],[ret(r) for r in ENT]).pvalue,2)} vs return, see §2: {gate(len(ENT), F2['Reliability (prior-trades) ≥ median']['p'])}).")

# ========================================================================= 12
sec(12, "COIN PERSONALITY REPORT")
W("Classification uses only what is stored (hold time, MFE/MAE, TP progression, immediate-reversal share). **Mean Reverter, News Driven, Low Liquidity, Volatile Breakout as distinct types cannot be identified from these fields** (no return-autocorrelation series, no event flags, no order-book depth) → INSUFFICIENT DATA; symbols with n<4 are not classified at all. Timeframe/strategy recommendations require ≥8 trades per timeframe per symbol — none qualifies.")
rows12 = []
for s_, v in sorted(bysym.items(), key=lambda kv: -len(kv[1])):
    x = summ(v)
    if len(v) < 4: continue
    imm = sum(1 for r in v if LIFE[r.id] == "immediate_reversal") / len(v)
    cls = "Trend Runner" if (x["tp3"] or 0) >= 25 else "Fakeout Coin" if imm >= .6 else "Slow Swing" if (x["hold"] or 0) > 72 else "Unclassified"
    rows12.append([s_, len(v), f"{x['wr']}%", x["tp3"], fn(imm * 100, 0) + "%", x["mfe"], x["mae"], x["hold"], cls, "INSUFFICIENT DATA (n per timeframe <8)"])
table(["Symbol (n≥4)", "n", "Win%", "TP3%", "Immediate-reversal share", "Avg MFE", "Avg MAE", "Median hold h", "Heuristic class", "Best timeframe/strategy"], rows12)
W(f"Only {len(rows12)} of {len(bysym)} symbols have n≥4. The classes above are descriptive labels, not validated personalities (a coin-personality model was previously rejected as unsupportable at this n, and the data still agrees).")

# ========================================================================= 13
sec(13, "MARKET REGIME INTELLIGENCE (CLUSTERING)")
comps = ["trend", "momentum", "volume", "funding", "structure", "history", "regime", "risk", "liquidity"]
Xsc = [[(x.score_breakdown or {}).get(c, 0) or 0 for c in comps] for x in SCANS if x.score_breakdown]
Xsc = np.array(Xsc, float); rgs = np.random.default_rng(1); samp = Xsc[rgs.choice(len(Xsc), min(15000, len(Xsc)), replace=False)]
mu_, sd_ = samp.mean(0), samp.std(0); sd_[sd_ == 0] = 1; Z = (samp - mu_) / sd_
best = None
for k in (3, 4, 5, 6):
    km = KMeans(k, n_init=5, random_state=0).fit(Z); sil = silhouette_score(Z[:4000], km.labels_[:4000])
    if best is None or sil > best[0]: best = (sil, k, km)
sil, K_, km = best
W(f"K-means on standardised scan score-breakdown vectors ({len(Xsc)} scans, 15k sample; k chosen by silhouette among 3–6 → k={K_}, silhouette={round(sil,3)}). **A silhouette below ~0.25 means clusters are weakly separated — these are descriptive groupings of scan states, NOT validated market regimes.**")
cent = km.cluster_centers_ * sd_ + mu_
def trade_vec(r): return np.array([r.trend_score, r.momentum_score, r.volume_score, r.funding_score, r.structure_score, r.history_score, r.regime_score, r.risk_score, r.liquidity_score], float)
lab = km.predict((np.array([trade_vec(r) for r in ENT]) - mu_) / sd_); CL = collections.defaultdict(list)
for r, l_ in zip(ENT, lab): CL[int(l_)].append(r)
rows13 = []
for k_ in range(K_):
    c_ = cent[k_]; top = sorted(zip(comps, (c_ - mu_) / sd_), key=lambda t: -abs(t[1]))[:3]
    v = CL.get(k_, []); rows13.append([k_, int((km.labels_ == k_).sum()), ", ".join(f"{n} {('↑' if z_>0 else '↓')}{abs(z_):.1f}σ" for n, z_ in top)] + (statline(v) if v else ["0"] + [""] * 5))
table(["Cluster", "Scan-sample size", "Signature (top deviations)"] + SH, rows13)
if len(CL) >= 2:
    tb = [[sum(1 for r in CL.get(k_, []) if r.status == "closed_win"), sum(1 for r in CL.get(k_, []) if r.status == "closed_loss")] for k_ in range(K_) if CL.get(k_)]
    from scipy.stats import chi2_contingency
    chi = chi2_contingency(tb); W(f"Outcome differs across clusters? chi-square p={round(chi[1],3)} (dof={chi[2]}). Result: {gate(len(ENT), chi[1])}.")
W("Named regimes you listed (Trend Expansion, Exhaustion, Panic Volatility, Mean Reversion, Distribution, Accumulation) cannot be *discovered* here: the clustering uses the score components only (no price-path, volatility or volume-profile features in ScanSnapshot). Existing labels: risk_on / mixed only. **INSUFFICIENT DATA** to add regimes.")

# ========================================================================= 14
sec(14, "MISSED OPPORTUNITY ANALYSIS")
cc = collections.Counter(cat_of(x.rejection_reason) for x in SCANS)
table(["Rejection reason", "Scan rows", "%"], [[k, v, fn(pct(v, len(SCANS)), 1)] for k, v in cc.most_common()])
AV = [r for r in ALL if r.status == "rejected_avoid"]
SYMTS = {k: [(sn.timestamp, sn.current_price) for sn in v] for k, v in SNAP_BY_SYM.items()}
def fwd_h(sym, t0, sg, H):
    lst = SYMTS.get(sym)
    if not lst: return None
    ts = [a for a, _ in lst]; i = bisect.bisect_left(ts, t0); c = [j for j in (i - 1, i) if 0 <= j < len(lst) and abs(lst[j][0] - t0) <= 15 * 60000]
    if not c: return None
    p0 = lst[min(c, key=lambda j: abs(lst[j][0] - t0))][1]; j1 = bisect.bisect_left(ts, t0 + H * 3600000)
    if j1 >= len(lst) or abs(lst[j1][0] - (t0 + H * 3600000)) > max(.25 * H, .5) * 3600000: return None
    return (lst[j1][1] - p0) / p0 * 100 * sg
rows14 = []
for k in [c_[0] for c_ in cc.most_common() if c_[0] != "published/active"]:
    subs = [x for x in SCANS if cat_of(x.rejection_reason) == k and x.direction in ("long", "short")]; row = [k, len(subs)]
    for H in (1, 4, 24, 72):
        v = [z for z in (fwd_h(x.symbol, x.timestamp, 1 if x.direction == "long" else -1, H) for x in subs) if z is not None]; row.append(f"n={len(v)}" + (f", avg {fn(avg(v))}%, fav {fn(pct(sum(1 for z in v if z>0), len(v)),0)}%" if len(v) >= 10 else " (INSUFFICIENT)"))
    rows14.append(row)
table(["Category (directional rows)", "Directional scans", "+1h", "+4h", "+24h", "+72h"], rows14)
W(f"Avoid-grade plans: {len(AV)} with price levels but **0 PredictionSnapshots** (never tracked) → whether they later hit TP1/TP2/TP3 is unknowable. Rejected scans carry no TP levels at all. `rejected_opportunity_outcomes` has {len(REJ)} rows. "
  "**'Would Have Won' and 'False Reject' leaderboards: INSUFFICIENT DATA — cannot be produced without inventing outcomes.** Which rules are too strict: no evidence (the two rules with data are `late` and `exhausted`, which by design have no realised-outcome record). What to build: wire the existing recorder (needs approval to touch the scanner) — planned in §23.")

# ========================================================================= 15
sec(15, "INVALIDATED TRADE ANALYSIS")
INV = [r for r in ALL if r.status == "invalidated"]; inv_e = [r for r in INV if r.entry_hit]
byS = collections.defaultdict(list)
for r in ALL: byS[r.symbol].append(r)
why = collections.Counter()
for r in INV:
    sn = SNAP_BY_TRADE.get(r.id, [])
    if sn: why[(sn[-1].decision_reason or sn[-1].reason or "n/a")[:90]] += 1
W(f"Invalidated: n={len(INV)} ({len(inv_e)} had entered). The system does not store an invalidation reason; the invalidation rule is supersession by a newer plan on the same symbol. The final-snapshot text (top 6, which is the trade's status message, not a cause): {dict(why.most_common(6))}.")
def last_pnl(r):
    s_ = [x for x in SNAP_BY_TRADE.get(r.id, []) if x.status == "open"]; return s_[-1].current_pnl_pct if s_ else None
lp = [last_pnl(r) for r in inv_e if last_pnl(r) is not None]
rep = []; flips = 0; dconf = []; res_w = res_n = 0
for r in INV:
    nxt = sorted([x for x in byS[r.symbol] if x.created_at > r.created_at], key=lambda x: x.created_at)
    if not nxt: continue
    x = nxt[0]; rep.append(x); flips += x.direction != r.direction
    if x.confidence is not None and r.confidence is not None: dconf.append(x.confidence - r.confidence)
    if x.status in ("closed_win", "closed_loss"): res_n += 1; res_w += x.status == "closed_win"
table(["Metric", "Value"], [["Invalidated & entered: unrealized P&L at last snapshot (n / avg / % positive)", f"{len(lp)} / {fn(avg(lp))}% / {fn(pct(sum(1 for x in lp if x>0), len(lp)),1)}%"], ["…of which had already hit TP1", sum(1 for r in inv_e if r.tp1_hit)],
      ["Replacement exists (same symbol, next plan)", f"{len(rep)}/{len(INV)}"], ["Replacement flips direction", f"{flips} ({fn(pct(flips, len(rep)),1)}%)"], ["Replacement confidence − original (avg)", fn(avg(dconf), 2)],
      ["Replacements that resolved: n / win rate", f"{res_n} / {fn(pct(res_w, res_n),1)}% (vs {fn(summ(ENT)['wr'],1)}% for all resolved trades)"]])
W("**Was invalidation good or bad?** Roughly 73% of entered-then-invalidated trades were in profit at their last snapshot — invalidation closed positions that were mostly fine, but no realised outcome exists to say whether holding would have beaten the replacement (INSUFFICIENT DATA). Replacement win rate is in line with the overall resolved win rate, so there is no evidence replacements are *worse*. Most invalidations are re-issues while pending (churn), which inflates the '727 invalidated' figure without any economic meaning.")

# ========================================================================= 16
sec(16, "OPEN TRADE ANALYSIS")
oa = pc.open_trade_management_analytics()["trades"]; OB = {r.id: r for r in ALL}
rows16 = []
for t in oa:
    r = OB.get(t["trade_outcome_id"]); sn = SNAP_BY_TRADE.get(r.id, []) if r else []; last = sn[-1] if sn else None
    rows16.append([r.symbol, r.direction, t["status"], last.stage if last else "—", fn(last.current_pnl_pct if last and t["status"] == "open" else None), fn((t.get("distances") or {}).get("to_tp1_pct")), fn((t.get("distances") or {}).get("to_stop_pct")),
                   fn(last.tp1_probability, 2) if last and last.tp1_probability is not None else "—", fn(last.tp2_probability, 2) if last and last.tp2_probability is not None else "—", fn(evr(r)) if evr(r) is not None else "—", fn(RELMAP.get(r.symbol, {}).get("reliability_score"), 1) if r.symbol in RELMAP else "—",
                   last.management_decision if last and last.management_decision else "—", t["recommendation"], dt(last.timestamp) if last else "—", fn((datetime.now(timezone.utc).timestamp() * 1000 - last.timestamp) / 86400000, 1) if last else "never"])
table(["Symbol", "Dir", "Status", "Stage", "PnL%", "To TP1%", "To stop%", "P(TP1)", "P(TP2)", "EV(R)", "Reliability", "Manager decision", "Recommendation", "Last snapshot", "Days stale"], rows16)
_now_ms = datetime.now(timezone.utc).timestamp() * 1000
_lastts = {}
for t in oa:
    _sn = SNAP_BY_TRADE.get(t["trade_outcome_id"], [])
    _lastts[t["trade_outcome_id"]] = _sn[-1].timestamp if _sn else None
_stale = [(_now_ms - v) / 86400000 for v in _lastts.values() if v]
W(f"**DATA-STALENESS WARNING:** of {len(oa)} open/pending trades, {sum(1 for d in _stale if d > 1)} have had no snapshot for more than 1 day (median {round(statistics.median(_stale),1)} days, oldest {round(max(_stale),1)} days) and {sum(1 for t in oa if not _lastts[t['trade_outcome_id']])} have never been snapshotted. Their 'Hold' recommendations are the default output on stale data, NOT a live assessment - several are near their stops (see 'To stop%'). I therefore do not issue Reduce/Exit/Take-TP1 recommendations: the data cannot support them. Action: bring the scanner up and let it re-snapshot before acting on any of these.")
stale = [r for r in rows16 if r[-1] != "—" and (datetime.now(timezone.utc).timestamp() * 1000 - (max(sn.timestamp for sn in SNAP_BY_TRADE[[k for k, v in OB.items() if v.symbol == r[0] and v.status in ('open','pending')][0]]) )) > 3600000] if False else []
W("**Recommendations are the existing deterministic Trade-Manager output** (Hold / Move stop / etc.); I did not invent new ones. 'Updated stop probability' and 'updated EV' are not recomputed per open trade by the system — only TP probabilities are stored on snapshots; EV is fixed at issuance (blank for pre-09-12 plans). Several open trades have not been snapshotted recently (scanner downtime), so 'current' values may be stale — check 'Last snapshot'.")

# ========================================================================= 17
sec(17, "DECISION ENGINE AUDIT")
AU = {r.id: audit_trade(r) for r in ENT}; items = ["trend_pass", "structure_pass", "history_pass", "volume_pass", "funding_pass", "risk_pass", "regime_pass"]
def npass(r): return sum(1 for it in items if it in AU[r.id]["accepted_because"])
rows17 = []
for it in items:
    P = [r for r in ENT if it in AU[r.id]["accepted_because"]]; A = [r for r in ENT if it not in AU[r.id]["accepted_because"]]; t = two(lambda r, it=it: it in AU[r.id]["accepted_because"], ENT)
    rows17.append([it.replace("_pass", ""), f"{sum(1 for r in P if r.status=='closed_win')}W/{sum(1 for r in P if r.status=='closed_loss')}L", f"{sum(1 for r in A if r.status=='closed_win')}W/{sum(1 for r in A if r.status=='closed_loss')}L", f"{fn(summ(P)['wr'],1) if P else '-'}% / {fn(summ(A)['wr'],1) if A else '-'}%", t["p"] if t else "-", gate(min(len(P), len(A)), t["p"] if t else None)])
table(["Gate", "Passed (W/L)", "Failed (W/L)", "Win% passed / failed", "Fisher p", "Evidence the gate discriminates"], rows17)
cm_rows = []
for k in (7, 6, 5, 4):
    P = [r for r in ENT if npass(r) >= k]; A = [r for r in ENT if npass(r) < k]
    cm_rows.append([f"≥{k} of 7 checks pass = 'take'", sum(1 for r in P if r.status == "closed_win"), sum(1 for r in P if r.status == "closed_loss"), sum(1 for r in A if r.status == "closed_win"), sum(1 for r in A if r.status == "closed_loss"), fn(summ(P)["pf"]) if P else "—", fn(summ(A)["pf"]) if A else "—"])
table(["Decision rule", "Take & won (TP)", "Take & lost (FP)", "Skip & won (FN)", "Skip & lost (TN)", "PF taken", "PF skipped"], cm_rows)
W("**Would today's decision still be made?** The live engine has no separate 'accept' step beyond the deterministic direction gate — every trade here was published under current logic; the checklist is diagnostic. **Which gate allowed bad trades / filtered winners:** history and structure fail on most trades regardless of outcome (they fail in ~94%/59% of wins vs ~86%/64% of losses); trend, risk, regime, funding and volume almost never fail (no information). No checklist gate is shown to discriminate (all p>0.15) — NOT SUPPORTED; changing decision.py on this evidence would be tuning on noise.")

# ========================================================================= 18
sec(18, "WEIGHT RECALIBRATION (MEASUREMENT ONLY)")
COMP = [("trend", "trend_score", "0–25"), ("momentum", "momentum_score", "0–15"), ("volume", "volume_score", "0–10"), ("funding", "funding_score", "0–10"), ("structure", "structure_score", "0–15"), ("history", "history_score", "−15..+15"), ("regime", "regime_score", "−5..+5"), ("risk", "risk_score", "−20..0"), ("liquidity", "liquidity_score", "−5..0"), ("ML", "ml_score", "−10..+8")]
rows18 = []; rgb = np.random.default_rng(2); sigs = 0
for nm, at, rngtxt in COMP:
    v = np.array([getattr(r, at) for r in ENT], float); y = np.array([1 if r.status == "closed_win" else 0 for r in ENT])
    if v.std() == 0: rows18.append([nm, rngtxt, "—", "—", "—", "—", "—", "no variation"]); continue
    z = (v - v.mean()) / v.std(); b0 = LogisticRegression(C=1e4, max_iter=500).fit(z[:, None], y).coef_[0][0]; bb = []
    for _ in range(400):
        i = rgb.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(y) and z[i].std() > 0: bb.append(LogisticRegression(C=1e4, max_iter=500).fit(z[i][:, None], y[i]).coef_[0][0])
    lo, hi = np.percentile(bb, [2.5, 97.5]); sig = lo > 0 or hi < 0; sigs += sig; sp_ = spearmanr(v, [ret(r) for r in ENT])
    nz = int((v != 0).sum())
    rec_ = ("Change (direction: %s) - evidence LIKELY, magnitude not estimable" % ("up" if b0 > 0 else "down")) if (sig and nz >= 30) else ("Statistically significant BUT only %d non-zero trades (confounded with the few majors that have history) -> NOT recommended" % nz if sig else "No change (current weight retained)")
    rows18.append([nm, rngtxt, round(float(np.exp(b0)), 2), f"[{np.exp(lo):.2f},{np.exp(hi):.2f}]", round(sp_.pvalue, 3), rec_, "n/a (cannot be estimated without a validated model)", ("LIKELY (confounded)" if sig and nz < 30 else "LIKELY" if sig else "NOT SUPPORTED")])
table(["Component", "Current range", "OR per +1 SD", "Bootstrap 95% CI", "Spearman p", "Suggested weight", "Expected PF improvement", "Evidence"], [z[:8] if len(z) >= 8 else z + [""] * (8 - len(z)) for z in rows18])
W(f"**{sigs} of {len(COMP)} components have a bootstrap CI excluding 1 (history is nonzero on only 16 trades, all majors, and its win-rate test is p~0.28, so this is a confounded artefact).** Per instructions only statistically significant, adequately-sampled changes are recommended - none qualifies (so no suggested weights, and any 'expected PF improvement' would be fabricated). A cross-validated logistic model on the components had AUC %s (≈ chance-to-weak)." % round(float(np.mean([roc_auc_score(y[te], LogisticRegression(C=.5, max_iter=500).fit(((lambda M: (M - M.mean(0)) / np.where(M.std(0) == 0, 1, M.std(0)))(np.array([[getattr(r, at) for _, at, _ in COMP] for r in ENT], float)))[tr], y[tr]).predict_proba(((lambda M: (M - M.mean(0)) / np.where(M.std(0) == 0, 1, M.std(0)))(np.array([[getattr(r, at) for _, at, _ in COMP] for r in ENT], float)))[te])[:, 1]) for sd in range(5) for tr, te in StratifiedKFold(5, shuffle=True, random_state=sd).split(np.zeros(len(y)), y)])), 3))

# ========================================================================= 19
sec(19, "SIMULATION BACKTEST (SCENARIO REPLAY)")
W("Scenarios are filters/policies applied to the same historical trades (in-sample; each was defined *after* seeing the data, so all gains are optimistic). Chronological split shows stability: the first half of trades (by entry time) vs the second. TP-manager and dynamic-stop scenarios use the path simulator from §9 on covered trades and actual results elsewhere.")
def mdd(rows):
    o = sorted([r for r in rows if r.exit_time], key=lambda r: r.exit_time); c = p = m = 0
    for r in o: c += ret(r); p = max(p, c); m = min(m, c - p)
    return round(m, 1)
med_ent = ALL_SORTED[len(ALL_SORTED) // 2].entry_time or ALL_SORTED[len(ALL_SORTED) // 2].created_at
def scen_rows(sel, adj=None):
    S_ = [r for r in ENT if sel(r)]; rs = [(adj(r) if adj and adj(r) is not None else ret(r)) for r in S_]; return S_, rs
scen = [("Baseline", lambda r: True, None), ("Excellent entries only", lambda r: r.entry_quality == "excellent", None), ("Longs only", lambda r: r.direction == "long", None), ("No shorts (identical to longs only)", lambda r: r.direction == "long", None),
        ("Reliability(prior) ≥ median", lambda r: RELP[r.id] >= relmed, None), ("Weak structure filtered (structure ≥ 9)", lambda r: r.structure_score >= 9, None), ("RSI 50–70 only", lambda r: 50 <= (ei(r).get("rsi14") or -1) < 70, None),
        ("TP manager (break-even after TP1)", lambda r: True, lambda r: walk(r, be_after_tp1=True)), ("Dynamic stop (trail 50% MFE after TP1)", lambda r: True, lambda r: walk(r, trail=0.5)),
        ("Longs + weak-structure filter", lambda r: r.direction == "long" and r.structure_score >= 9, None), ("Longs + TP manager", lambda r: r.direction == "long", lambda r: walk(r, be_after_tp1=True))]
rows19 = []
for nm, sel, adj in scen:
    S_, rs = scen_rows(sel, adj); a_ = [(adj(r) if adj and adj(r) is not None else ret(r)) for r in S_ if (r.entry_time or r.created_at) < med_ent]; b_ = [(adj(r) if adj and adj(r) is not None else ret(r)) for r in S_ if (r.entry_time or r.created_at) >= med_ent]
    ex1 = sorted(rs, reverse=True)[1:]
    rows19.append([nm, len(S_), fn(pct(len(S_), len(ENT)), 0) + "%", fn(pct(sum(1 for x in rs if x > 0), len(rs)), 1) + "%", fn(pf(rs)), fn(pf(ex1)), fn(med(rs)), mdd(S_) if adj is None else "n/a", f"{fn(pf(a_))} / {fn(pf(b_))}", round(sum(rs), 1)])
rows19s = sorted(rows19, key=lambda z: -(float(z[4]) if z[4] not in ("—", None) else 0)); table(["Scenario (ranked by PF)", "n trades", "Frequency kept", "Win%", "PF", "PF ex-best", "Median ret", "Max DD (summed)", "PF 1st half / 2nd half", "Sum ret%"], rows19s)
W("**Reading:** any scenario that beats baseline PF in *both* halves and with PF-ex-best>1 would be a lead, but all are in-sample. 'Longs only' improves PF mainly because the short cohort's losses were outage-contaminated (§4). TP-manager/dynamic-stop rows rest on partial path coverage (n in §9). Nothing here is CONFIRMED; ranking is descriptive, not a deployment recommendation.")

# ========================================================================= 20
sec(20, "PREDICTION VERSION COMPARISON")
EV_FIRST = min(r.created_at for r in ALL if r.expected_value)
grp = [("v1.0 (pre entry-quality)", [r for r in ENT if r.created_at < EQ_LAUNCH]), ("Entry-Quality launch → EV launch", [r for r in ENT if EQ_LAUNCH <= r.created_at < EV_FIRST]), ("EV + Trade Manager + metadata (same deployment)", [r for r in ENT if r.created_at >= EV_FIRST])]
rows20 = []
for nm, sub in grp:
    ct = [r for r in sub if r.confidence is not None]; x = summ(sub)
    rows20.append([nm] + statline(sub) + [fn(pf([ret(r) for r in sub if r is not max(sub, key=ret)])) if sub else "—", fn(avg([(r.confidence / 100 - (r.status == 'closed_win')) ** 2 for r in ct]), 3), fn(avg([r.confidence for r in ct]), 1), dict(collections.Counter(r.market_regime for r in sub)), round(mdd(sub), 1)])
table(["Version"] + SH + ["PF ex-best", "Brier", "Mean conf", "Regime mix", "Naive DD"], rows20)
tv1 = two(lambda r: r.created_at >= EQ_LAUNCH, ENT); tv2 = two(lambda r: r.created_at >= EV_FIRST, ENT)
table(["Comparison", "n new/old", "Win% new / old", "OR", "p", "Evidence"], [["post-Entry-Quality vs before", f"{tv1['nP']}/{tv1['nA']}", f"{tv1['wrP']}% / {tv1['wrA']}%", tv1["OR"], tv1["p"], gate(tv1['nA'], tv1['p'])], ["post-EV/TradeManager/metadata vs before", f"{tv2['nP']}/{tv2['nA']}", f"{tv2['wrP']}% / {tv2['wrA']}%", tv2["OR"], tv2["p"], gate(tv2['nP'], tv2['p'])]])
W("Trade Manager and prediction-metadata launched with EV (same first stored timestamp), so they are not separable. Win-rate differences are **not** statistically meaningful (p above); PF gains in the latest era depend on a single trade (PF ex-best column) and on a different market window/regime mix. **Improvement is NOT statistically established** for any release.")

# ========================================================================= 21
sec(21, "DASHBOARD API SCHEMA (BACKEND ONLY)")
W("All schemas reuse endpoints/modules that already exist; the additions are fields, not new logic. `n` and an `evidence` label are mandatory in every block; `data_quality` reports scanner uptime and % gap-exposed so consumers cannot present a number without its caveat.")
W("```json"); W(json.dumps({
 "GET /api/performance/daily-scorecard": {"as_of": "iso8601", "data_quality": {"scanner_uptime_pct_24h": "float", "gap_exposed_open_trades": "int", "last_heartbeat": "iso8601"},
   "closed_today": {"n": "int", "win_rate": "float|null", "profit_factor": "float|null", "median_return_pct": "float|null", "ex_top1_profit_factor": "float|null"},
   "funnel": {"scanned": "int", "published": "int", "rejected_by_reason": {"late": "int", "exhausted": "int", "no_trade": "int", "rank_cutoff": "int"}}},
 "GET /api/performance/trade-quality/{id}": {"score_0_100": "int", "band": "A+|A|B|C|D", "components": {"entry_quality": "float", "ev": "float|null", "reliability": "float", "calibration": "float", "structure": "float", "red_flags_inverted": "float"}, "evidence": "string", "n_basis": "int"},
 "GET /api/performance/market-health": {"score_0_100": "int", "components": [{"name": "string", "value": "float|null", "available": "bool", "is_proxy": "bool"}], "unavailable": ["news_stress"]},
 "GET /api/performance/portfolio-exposure": {"open": "int", "pending": "int", "by_family": [{"family": "string", "n": "int", "long": "int", "short": "int"}], "same_direction_share": "float", "warnings": ["string"]},
 "GET /api/performance/coin-reliability": {"pooled_win_rate": "float", "symbols": [{"symbol": "string", "n": "int", "raw_win_rate": "float", "bayes_win_rate": "float", "credible_interval": "[float,float]", "p_above_pooled": "float", "tier": "Trusted|Watch|Caution|Avoid", "evidence": "string"}]},
 "GET /api/performance/opportunities?rank=top|worst&limit=10": {"items": [{"trade_outcome_id": "int", "symbol": "string", "direction": "string", "quality_score": "int", "ev_r": "float|null", "calibrated_p": "float", "calibrated_p_interval": "[float,float]", "flags": ["string"], "monitoring_status": "supervised|unmonitored"}]}}, indent=1))
W("```")

# ========================================================================= 22
sec(22, "IMPLEMENTATION ROADMAP")
W("Priority = evidence × size of lever ÷ (risk × complexity). Items that touch prediction are P3 or 'NOT NOW'. Nothing edits scoring.py, decision.py, the prompt or ML.")
gap_share = fn(pct(-sum(ret(r) for r in LOSS if in_outage(r.exit_time)), -sum(ret(r) for r in LOSS)), 1)
table(["Pri", "Change", "Impact", "Risk", "Evidence (numbers from DB)", "Files affected", "Migration", "Tests", "Expected improvement"], [
 ["P0", "Supervised always-on scanner + heartbeat alert (ops/deploy, not engine code)", "Highest: removes gap exposure", "Very low", f"uptime ≈{round((1 - sum(o['end']-o['start'] for o in OUT)/(max(sn.timestamp for sn in SNAPS)-min(sn.timestamp for sn in SNAPS)))*100,1)}%; {gap_share}% of loss magnitude exits inside gaps; {pct(sum(1 for r in ENT if any(o['start']<(r.exit_time or 0) and o['end']>(r.entry_time or r.created_at) for o in OUT)), len(ENT))}% of trades gap-exposed", "deployment config (systemd/NSSM/Docker), `background_scanner.py` untouched", "No", "Restart/soak test; heartbeat alarm test", "Cleaner data; P&L effect not isolatable"],
 ["P0", "Every KPI shows n, Wilson CI, median, ex-top-3 PF, gap-exposed %", "High (honesty)", "None", f"PF {summ(ENT)['pf']} → {pf([ret(r) for r in sorted(ENT, key=lambda r:-ret(r))[3:]])} ex-top-3", "analytics/`performance_center.py`, `routes/performance.py`", "No", "Unit tests on each KPI", "Prevents mis-decisions"],
 ["P0", "Display calibrated probability (≈base rate ± Wilson) beside raw confidence", "High (honesty)", "None", f"mean conf {fn(avg([r.confidence for r in CT]),1)} vs {fn(base*100,1)}% observed, binomial p≈{binomtest(sum(1 for r in CT if r.status=='closed_win'), len(CT), sum(r.confidence for r in CT)/100/len(CT)).pvalue:.1e}", "`engine/calibration.py` (display only), routes", "No", "Calibration tests exist", "Removes ~24pp overstatement"],
 ["P1", "Persist BOS/CHoCH/sweep/OBV booleans, ATR%, timeframe trends at issuance (additive columns)", "Unblocks §2,5,13", "Low", "0 trades have them → 6 requested features INSUFFICIENT DATA", "`db_models.py` (additive), `feature_builder.py`, `trade_outcomes.py`", "Yes (additive nullable columns via `_sync_additive_columns`)", "Round-trip persistence tests", "Enables future evidence"],
 ["P1", "Wire missed-opportunity recorder + track avoided/late/exhausted plans forward", "Unblocks §14", "Low (needs approval: frozen `background_scanner.py`)", f"{len(AV)} avoided plans, 0 snapshots; {cc.get('late',0)+cc.get('exhausted',0)} late/exhausted scans, no prices", "`background_scanner.py`, `analytics/missed_opportunity.py`", "No (table exists)", "Existing test_missed_opportunity", "Enables unbiased rejection audit"],
 ["P1", "Snapshot post-close price for 72h (per closed trade)", "Unblocks 'should have continued' / early-stop verdicts", "Low", "Verdicts 'TP2 Hit — Should Have Continued' impossible today", "`trade_outcomes.py`/monitor loop", "Yes (new columns or table)", "Unit tests", "Enables exit-policy research"],
 ["P2", "Shadow-log break-even / trailing outcomes for every trade", "Medium (evidence for §9)", "None", "§9 results inconclusive, partial paths", "`analytics/*` only", "No", "Path-sim unit tests", "Decides trailing/BE at n=200"],
 ["P2", "Soft warnings: RSI 30–49 chop; short 'monitoring-sensitive'", "Low–Med", "Low", f"RSI30–49 win 20.8% (n=24) vs 43.8%, p≈0.06", "`red_flags.py` (already there), UI", "No", "Existing", "Possible; unproven"],
 ["P3", "Any weight / decision / regime / prompt change", "Unknown", "High (overfit)", f"0 significant components; CV-AUC ≈ chance-to-weak (§18)", "scoring.py, decision.py, market_regime.py, reasoning.py", "—", "—", "NOT NOW; re-audit at n≥200"],
 ["P3", "Hard short ban", "Unknown", "High", f"uptime-only shorts {fn(summ([r for r in clean if r.direction=='short'])['wr'],1)}% (n={len([r for r in clean if r.direction=='short'])})", "—", "—", "—", "NOT NOW"],
 ["P3", "ML retrain / coin-personality models", "None shown", "High", "AUC unchanged after retrain; n per coin ≤4", "ml_model.py, ml_retrain.py", "—", "—", "NOT before 200 trades (your rule) and a held-out test"]])

# ========================================================================= 23
sec(23, "SAFE IMPLEMENTATION PLAN (COMMIT-BY-COMMIT)")
W("Follows your rules: no scoring.py / decision.py / prompt / ML edits; ML retraining not before 200 resolved trades (currently %d closed; the 'total resolved' counts differ from your brief only because the scanner has kept running). **No diffs or commits were produced now** — none is justified by evidence yet except the additive ones below, which need your go-ahead." % len(ENT))
table(["#", "Commit (message)", "Exact files", "Type", "Gate/evidence", "Tests"], [
 [1, "ops: supervised scanner service + heartbeat alert", "`deploy/` (service unit/NSSM script), `README` run notes; no app code", "Ops", "§U/§4: uptime, gap-exposure", "Manual soak: kill/restart; gap alert fires"],
 [2, "analytics: uptime/gap-exposure annotations on every KPI", "`app/engine/performance_center.py`, `app/routes/performance.py`", "Additive analytics", "§A/§U", "extend `test_performance_center.py`"],
 [3, "analytics: KPI blocks with n, Wilson CI, median, ex-top-k PF", "`app/analytics/kpi.py` (new), `routes/performance.py`", "Additive", "PF fragile ex-top-3", "new `test_kpi.py` with fixed fixtures"],
 [4, "analytics: calibrated-probability display (base-rate ± Wilson) + reliability diagram endpoint", "`app/engine/calibration.py`, `app/analytics/calibration_dashboard.py`", "Additive display", "§3 binomial test", "extend `test_calibration.py`"],
 [5, "feat(data): additive nullable columns for BOS/CHoCH/sweep/ATR%/timeframe trends on TradeOutcome", "`app/models/db_models.py`, `app/engine/feature_builder.py`, `app/engine/trade_outcomes.py`", "Additive migration (auto via `_sync_additive_columns`)", "§2/§5/§13 INSUFFICIENT DATA", "persistence round-trip test; NULL-safe readers"],
 [6, "feat(data): wire missed-opportunity recorder for late/exhausted/rank-cutoff/avoid plans (**requires explicit approval — touches frozen background_scanner.py**)", "`app/engine/background_scanner.py`, `app/analytics/missed_opportunity.py`", "Additive data capture", "§14 INSUFFICIENT DATA", "extend `test_missed_opportunity.py`"],
 [7, "feat(data): 72h post-close price capture", "`app/engine/trade_outcomes.py`, `db_models.py`", "Additive", "'Should have continued' unknowable", "unit test with synthetic closes"],
 [8, "analytics: shadow path-simulation logging for BE/trailing/ATR stops on each closed trade", "`app/analytics/stop_styles.py` (new)", "Additive", "§9 inconclusive", "port §9 simulator into tests with fixed paths"],
 [9, "docs: re-audit scripts (`analysis_karma_*.py`) become `tools/audit/` + weekly run", "`tools/audit/*`", "Docs/tools", "Reproducibility", "smoke-run against a DB copy"],
 ["—", "**Hold until ≥200 resolved trades and explicit approval:** any scoring/decision/regime/prompt/ML change", "—", "—", "§18: no significant component", "Out-of-sample: fit on first half, test on second"]])
W()
W("**END REPORT.**")
open("karma_eng_report.md", "w", encoding="utf-8").write("\n".join(L))
print("OK", len(L), "lines;", sum(len(x.split()) for x in L), "words")
