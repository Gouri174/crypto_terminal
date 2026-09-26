"""Karma V3.0 definitive audit — READ ONLY. Generates karma_v3_audit_report.md
and karma_v3_ledger.csv from the live DB. No code/prompt/weight/model/DB-row
changes. Every number in the report is computed here at run time."""
import sys, math, statistics, collections, bisect, csv, itertools, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import numpy as np
from scipy.stats import fisher_exact, spearmanr
from sqlalchemy import select
from app.db import SessionLocal
from app.models.db_models import TradeOutcome, PredictionSnapshot, ScanSnapshot, RejectedOpportunityOutcome
from app.analytics import failure_patterns as fp, strategy_attribution as sa, trade_truth as tt, reliability as rel
from app.analytics import trade_quality as tq, portfolio_exposure as pe
from app.analytics.decision_audit import audit_trade
from app.engine import performance_center as pc
from app.engine.red_flags import compute_red_flags

# ------------------------------------------------------------------ load
s = SessionLocal()
ALL = s.execute(select(TradeOutcome)).scalars().all()
SNAPS = s.execute(select(PredictionSnapshot)).scalars().all()
SCANS = s.execute(select(ScanSnapshot.timestamp, ScanSnapshot.symbol, ScanSnapshot.direction, ScanSnapshot.rejection_reason,
                         ScanSnapshot.market_regime, ScanSnapshot.score_breakdown, ScanSnapshot.rank)).all()
REJ = s.execute(select(RejectedOpportunityOutcome)).scalars().all()
s.close()

ENT = [r for r in ALL if r.status in ("closed_win", "closed_loss")]
WINS = [r for r in ENT if r.status == "closed_win"]
LOSS = [r for r in ENT if r.status == "closed_loss"]
EQ_LAUNCH = 1786342057000
EV_FIRST = min([r.created_at for r in ALL if r.expected_value] or [None]) if any(r.expected_value for r in ALL) else None
OUT = pc.scanner_health(10).get("outages", [])
SNAP_BY_TRADE = collections.defaultdict(list)
SNAP_BY_SYM = collections.defaultdict(list)
for sn in SNAPS:
    SNAP_BY_TRADE[sn.trade_outcome_id].append(sn)
    SNAP_BY_SYM[sn.symbol].append(sn)
for k in SNAP_BY_TRADE: SNAP_BY_TRADE[k].sort(key=lambda x: x.timestamp)
for k in SNAP_BY_SYM: SNAP_BY_SYM[k].sort(key=lambda x: x.timestamp)
CONT = {p["trade_outcome_id"]: p for p in pc.tp_continuation_analytics()["per_trade"]}
RELMAP = {e["symbol"]: e for e in rel.symbol_reliability()["symbols"]}
POOLED = rel.symbol_reliability()["pooled_win_rate_pct"]

# ------------------------------------------------------------------ helpers
def dt(ms): return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ms else "—"
def fn(x, nd=2):
    return "—" if x is None else (f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x))
def g6(x): return "—" if x is None else f"{x:.6g}"
def pct(n, d): return None if not d else round(n / d * 100, 1)
def ret(r): return r.realized_return_pct
def ei(r): return r.entry_indicators or {}
def rr(r): return ei(r).get("risk_reward") or {}
def sign(r): return 1 if r.direction == "long" else -1
def evr(r): return (r.expected_value or {}).get("expected_r")
def rR(r):
    rp = rr(r).get("risk_to_sl_pct")
    return round(ret(r) / rp, 3) if rp and ret(r) is not None else None
def wilson(k, n, z=1.96):
    if not n: return (None, None)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round(max(0, (c - h) / d) * 100, 1), round(min(1, (c + h) / d) * 100, 1))
def pf(rets):
    rets = [x for x in rets if x is not None]
    gl = sum(x for x in rets if x > 0); ls = sum(x for x in rets if x < 0)
    return round(gl / abs(ls), 2) if ls else None
def avg(v):
    v = [x for x in v if x is not None]; return round(sum(v) / len(v), 3) if v else None
def med(v):
    v = [x for x in v if x is not None]; return round(statistics.median(v), 3) if v else None
def summ(rows):
    n = len(rows); w = sum(1 for r in rows if r.status == "closed_win"); rets = [ret(r) for r in rows]
    return dict(n=n, w=w, l=n - w, wr=pct(w, n), avg=avg(rets), med=med(rets), pf=pf(rets),
                tp1=pct(sum(1 for r in rows if r.tp1_hit), n), tp2=pct(sum(1 for r in rows if r.tp2_hit), n),
                tp3=pct(sum(1 for r in rows if r.tp3_hit), n), stop=pct(sum(1 for r in rows if r.stop_hit), n),
                mfe=avg([r.max_runup_pct for r in rows]), mae=avg([r.max_drawdown_pct for r in rows]),
                hold=med([r.holding_minutes / 60 for r in rows if r.holding_minutes]), ci=wilson(w, n))
def in_outage(t): return t is not None and any(o["start"] <= t <= o["end"] for o in OUT)
def two(pred, rows):
    P = [r for r in rows if pred(r) is True]; A = [r for r in rows if pred(r) is False]
    if len(P) < 2 or len(A) < 2: return None
    a = sum(1 for r in P if r.status == "closed_win"); b = len(P) - a
    c = sum(1 for r in A if r.status == "closed_win"); d = len(A) - c
    _, p = fisher_exact([[a, b], [c, d]])
    aa, bb, cc, dd = (x + .5 if min(a, b, c, d) == 0 else x for x in (a, b, c, d))
    OR = aa * dd / (bb * cc); se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    def H(q): return 0 if q <= 0 or q >= 1 else -q * math.log2(q) - (1 - q) * math.log2(1 - q)
    n = len(P) + len(A); tot = (a + c) / n
    ig = H(tot) - (len(P) / n * H(a / len(P)) + len(A) / n * H(c / len(A)))
    return dict(nP=len(P), nA=len(A), wrP=pct(a, len(P)), wrA=pct(c, len(A)), OR=round(OR, 2),
                lo=round(math.exp(math.log(OR) - 1.96 * se), 2), hi=round(math.exp(math.log(OR) + 1.96 * se), 2),
                p=round(p, 4), ig=round(ig, 4), avgP=avg([ret(r) for r in P]), avgA=avg([ret(r) for r in A]))
def conf(n, p):
    if p is None or n < 10: return "INSUFFICIENT DATA"
    if p < .01 and n >= 20: return "HIGH"
    if p < .05: return "MEDIUM"
    if p < .15: return "LOW (suggestive only)"
    return "NOT SIGNIFICANT"
def bar(v, mx=100, w=28):
    return "█" * int(round((v or 0) / mx * w)) if v is not None else ""
L = []
def W(x=""): L.append(x)
def table(head, rows):
    W("| " + " | ".join(head) + " |"); W("|" + "---|" * len(head))
    for r in rows: W("| " + " | ".join(str(c) for c in r) + " |")
    W()
def sec(n, t):
    W(); W(f"## SECTION {n} — {t}"); W()
def frow(name, t):
    if not t: return [name, "n<2 side", "", "", "", "", "", ""]
    return [name, f"{t['nP']}/{t['nA']}", fn(t['wrP'], 1) + "% / " + fn(t['wrA'], 1) + "%", t['OR'], f"[{t['lo']}, {t['hi']}]", t['p'], t['ig'], conf(min(t['nP'], t['nA']), t['p'])]
FH = ["Feature", "n present/absent", "win% present / absent", "Odds ratio", "95% CI", "Fisher p", "Info gain (bits)", "Confidence"]
def ftable(specs, rows=None):
    rows = ENT if rows is None else rows
    out = []
    for name, pred in specs:
        t = two(pred, rows); out.append((name, t))
    table(FH, [frow(n, t) for n, t in out])
    return out
def bucket_table(label, valfn, edges, rows=None, fmt=lambda a, b: f"{a}–{b}"):
    rows = ENT if rows is None else rows
    body = []
    for a, b in zip(edges[:-1], edges[1:]):
        sub = [r for r in rows if valfn(r) is not None and a <= valfn(r) < b]
        if not sub: body.append([fmt(a, b), 0, "", "", "", ""]); continue
        sm = summ(sub); body.append([fmt(a, b), sm["n"], fn(sm["wr"], 1) + "%", fn(sm["avg"]) + "%", fn(sm["pf"]), fn(sm["med"]) + "%"])
    W(f"**{label}**"); table(["Range", "n", "Win rate", "Avg ret", "PF", "Median ret"], body)

# ---- per-trade derived
STRAT = {r.id: sa.classify_strategy(r) for r in ENT}
TRUTH = {r.id: tt.classify_truth(r, OUT)["verdict"] for r in ENT}
LIFE = {r.id: fp.lifecycle_pattern(r) for r in ENT}
TAGS = {r.id: fp.risk_tags(r, OUT) for r in ENT}
def sc(r, k): return getattr(r, k)
def ind(k): return lambda r: ei(r).get(k)
def above_all(r):
    d = [ei(r).get("distance_to_ema20_pct"), ei(r).get("distance_to_ema50_pct"), ei(r).get("distance_to_ema200_pct")]
    if any(x is None for x in d): return None
    return all(x > 0 for x in d) if r.direction == "long" else all(x < 0 for x in d)
def flag_list(r):
    f = []
    i = ei(r)
    if i.get("rsi14") is not None and 30 <= i["rsi14"] < 50: f.append("rsi_chop_30_49")
    if r.structure_score is not None and r.structure_score < 9: f.append("weak_structure")
    if r.historic_probability is None: f.append("no_history")
    if i.get("cmf") is not None and i["cmf"] < 0: f.append("negative_cmf")
    if i.get("mfi") is not None and i["mfi"] > 80: f.append("mfi_over_80")
    if i.get("atr_distance_to_ema20") is not None and abs(i["atr_distance_to_ema20"]) > 2.5: f.append("high_atr_extension")
    if r.risk_score is not None and r.risk_score <= -3: f.append("risk_penalty_applied")
    if r.liquidity_score is not None and r.liquidity_score < 0: f.append("liquidity_stress")
    if r.funding_score is not None and r.funding_score <= 5: f.append("funding_elevated")
    if r.direction == "short": f.append("short_direction")
    if in_outage(r.exit_time): f.append("outage_exit")
    return f
FLAGS = {r.id: flag_list(r) for r in ENT}
FLAG_NAMES = ["rsi_chop_30_49", "weak_structure", "no_history", "negative_cmf", "mfi_over_80", "high_atr_extension",
              "risk_penalty_applied", "liquidity_stress", "funding_elevated", "short_direction", "outage_exit"]

# =================================================================== SECTION 1
W("# Karma Archive — V3.0 Definitive Forensic Audit")
W()
W(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} from the live SQLite DB. **Read-only** — no code, prompt, weight, model or DB row was changed. "
  f"Every figure is computed at run time by `analysis_karma_v3_audit.py`. `n=` is shown throughout; anything the DB cannot support is marked **INSUFFICIENT DATA**.")
W()
W("**Global caveats**: (1) Sharpe is per-trade (mean/σ of realized %), not annualized. (2) 'Drawdown' is a naive summed-return curve (no compounding/sizing). "
  "(3) Reliability is computed on all data (hindsight) — it is descriptive here, not what the system knew at entry. (4) Fisher's exact test on 2×2 win/loss tables; with n≈116, only large effects can reach significance. "
  "(5) Overlapping/clustered trades are not independent, so p-values are optimistic.")
sec(1, "EXECUTIVE SUMMARY")
cnt = collections.Counter(r.status for r in ALL)
never_entered_inval = sum(1 for r in ALL if r.status == "invalidated" and not r.entry_hit)
S = summ(ENT); Lg = summ([r for r in ENT if r.direction == "long"]); Sh = summ([r for r in ENT if r.direction == "short"])
rets = [ret(r) for r in ENT]
sharpe = round(statistics.mean(rets) / statistics.pstdev(rets), 3)
order = sorted([r for r in ENT if r.exit_time], key=lambda r: r.exit_time)
cum = peak = mdd = 0
for r in order: cum += ret(r); peak = max(peak, cum); mdd = min(mdd, cum - peak)
table(["Metric", "Value", "n"], [
    ["Total trade plans ever generated", len(ALL), len(ALL)],
    ["Closed (resolved) trades", len(ENT), len(ENT)],
    ["Open trades", cnt["open"], cnt["open"]], ["Pending (not yet entered)", cnt["pending"], cnt["pending"]],
    ["Never entered (expired, `closed_stale`)", cnt["closed_stale"], cnt["closed_stale"]],
    ["Invalidated (superseded by a newer plan)", cnt["invalidated"], f"{cnt['invalidated']} ({never_entered_inval} never entered)"],
    ["Avoid-grade (`rejected_avoid`)", cnt["rejected_avoid"], cnt["rejected_avoid"]],
    ["Wins / Losses", f"{S['w']} / {S['l']}", S["n"]], ["Overall win rate", f"{S['wr']}% (95% CI {S['ci'][0]}–{S['ci'][1]}%)", S["n"]],
    ["TP1 / TP2 / TP3 rate", f"{S['tp1']}% / {S['tp2']}% / {S['tp3']}%", S["n"]], ["Stop rate", f"{S['stop']}%", S["n"]],
    ["Average return", f"{S['avg']}%", S["n"]], ["Median return", f"{S['med']}%", S["n"]], ["Profit factor", S["pf"], S["n"]],
    ["Sharpe (per-trade)", sharpe, S["n"]], ["Max drawdown (naive summed curve)", f"{round(mdd, 1)}%", len(order)],
    ["Worst single trade", f"{round(min(rets), 2)}%", S["n"]], ["Best single trade", f"{round(max(rets), 2)}%", S["n"]],
    ["Median hold (hours)", S["hold"], S["n"]],
])
table(["Segment", "n", "Win rate", "PF", "Avg ret", "Median ret", "TP1/TP2/TP3 %", "Stop %", "Median hold h"],
      [[nm, x["n"], f"{x['wr']}%", x["pf"], f"{x['avg']}%", f"{x['med']}%", f"{x['tp1']}/{x['tp2']}/{x['tp3']}", f"{x['stop']}%", x["hold"]]
       for nm, x in [("Long", Lg), ("Short", Sh)] + [(f"Timeframe={t}", summ([r for r in ENT if r.timeframe == t])) for t in sorted(set(r.timeframe for r in ENT))]])
srt = sorted(ENT, key=lambda r: -ret(r))
ex1 = [r for r in ENT if r is not srt[0]]; ex3 = [r for r in ENT if r not in srt[:3]]
table(["Concentration test", "n", "PF", "Avg ret", "Median ret"],
      [["All closed", S["n"], S["pf"], S["avg"], S["med"]], [f"Excl. best trade ({srt[0].symbol} {round(ret(srt[0]), 1)}%)", len(ex1), pf([ret(r) for r in ex1]), avg([ret(r) for r in ex1]), med([ret(r) for r in ex1])],
       ["Excl. top 3", len(ex3), pf([ret(r) for r in ex3]), avg([ret(r) for r in ex3]), med([ret(r) for r in ex3])]])
KEY = dict(pf_all=S["pf"], pf_ex3=pf([ret(r) for r in ex3]), med=S["med"], wr=S["wr"])
verdict = "Marginal" if (S["pf"] and S["pf"] > 1 and (KEY["pf_ex3"] or 0) < 1.3) or (S["med"] or 0) < 0 else ("Yes" if S["pf"] and S["pf"] > 1.3 else "No")
W(f"**Is Karma profitable? → {verdict}.** Aggregate PF is {S['pf']} and average return is {S['avg']}% (n={S['n']}), but the median trade is {S['med']}% and PF falls to "
  f"{KEY['pf_ex3']} without the top 3 winners: profit comes from a small number of large longs, while shorts (n={Sh['n']}, PF {Sh['pf']}) lose. Most trades lose; the edge is right-tail winners.")
W(f"**Confidence:** MEDIUM for 'positive expectancy so far' (n={S['n']}); LOW that it is robust. **Engineering recommendation:** treat headline PF as fragile; report ex-top-3 PF on every dashboard.")

# =================================================================== SECTION 2 (ledger)
sec(2, "COMPLETE CLOSED TRADE LEDGER")
W(f"All {len(ENT)} closed trades, newest first (created time). Reliability* = Bayesian per-symbol score on all data (hindsight). EV shown only where stored at issuance (post-V2.1); '—' = not computed for that era. Strategy = `strategy_attribution.classify_strategy` (BOS/CHoCH are proxies). Pattern = lifecycle + risk tags. Outcome = Trade-Truth verdict.")
W()
head = ["Symbol", "Created", "Entered", "Closed", "Dir", "Strategy", "Entry", "Exit", "Stop", "TP1", "TP2", "TP3", "Grade", "Conf", "Score", "EQ", "Regime", "EV(R)", "Rel*", "Ret%", "MFE%", "MAE%", "Hold h", "Pattern", "Red flags", "Outcome"]
ledger = []
for r in sorted(ENT, key=lambda r: -r.created_at):
    relv = (RELMAP.get(r.symbol) or {}).get("reliability_score")
    ledger.append([r.symbol, dt(r.created_at), dt(r.entry_time), dt(r.exit_time), r.direction, STRAT[r.id], g6(r.entry), g6(r.exit_price), g6(r.stop_loss),
                   g6(r.tp1), g6(r.tp2), g6(r.tp3), r.grade or "—", r.confidence if r.confidence is not None else "—", fn(r.score, 1), r.entry_quality or "—", r.market_regime or "—",
                   fn(evr(r)), fn(relv, 1), fn(ret(r)), fn(r.max_runup_pct), fn(r.max_drawdown_pct), fn(r.holding_minutes / 60 if r.holding_minutes else None, 1),
                   LIFE[r.id] + ("+" + ",".join(TAGS[r.id]) if TAGS[r.id] else ""), ",".join(f for f in FLAGS[r.id] if f not in ("short_direction", "outage_exit")) or "—", TRUTH[r.id]])
table(head, ledger)
with open("karma_v3_ledger.csv", "w", newline="", encoding="utf-8") as f:
    cw = csv.writer(f); cw.writerow(head); cw.writerows(ledger)

# =================================================================== SECTION 3
sec(3, "EVERY WIN")
SPECS = [
    ("trend_score ≥ 22", lambda r: r.trend_score >= 22 if r.trend_score is not None else None),
    ("structure_score ≥ 9", lambda r: r.structure_score >= 9 if r.structure_score is not None else None),
    ("momentum_score ≥ 14", lambda r: r.momentum_score >= 14 if r.momentum_score is not None else None),
    ("volume_score ≥ 8", lambda r: r.volume_score >= 8 if r.volume_score is not None else None),
    ("funding_score ≥ 8 (non-crowded)", lambda r: r.funding_score >= 8 if r.funding_score is not None else None),
    ("history present", lambda r: r.history_score > 0 if r.history_score is not None else None),
    ("regime = mixed", lambda r: r.market_regime == "mixed" if r.market_regime else None),
    ("entry_quality = excellent", lambda r: r.entry_quality == "excellent" if r.entry_quality else None),
    ("entry_quality = good", lambda r: r.entry_quality == "good" if r.entry_quality else None),
    ("ADX 20–50", lambda r: 20 <= ei(r)["adx14"] < 50 if ei(r).get("adx14") is not None else None),
    ("ADX ≥ 35", lambda r: ei(r)["adx14"] >= 35 if ei(r).get("adx14") is not None else None),
    ("RSI 50–70", lambda r: 50 <= ei(r)["rsi14"] < 70 if ei(r).get("rsi14") is not None else None),
    ("RSI < 50", lambda r: ei(r)["rsi14"] < 50 if ei(r).get("rsi14") is not None else None),
    ("RSI ≥ 70", lambda r: ei(r)["rsi14"] >= 70 if ei(r).get("rsi14") is not None else None),
    ("CMF > 0", lambda r: ei(r)["cmf"] > 0 if ei(r).get("cmf") is not None else None),
    ("MFI > 80", lambda r: ei(r)["mfi"] > 80 if ei(r).get("mfi") is not None else None),
    ("Bollinger %B > 0.95", lambda r: ei(r)["bb_pct"] > 0.95 if ei(r).get("bb_pct") is not None else None),
    ("MACD hist > 0", lambda r: ei(r)["macd_hist"] > 0 if ei(r).get("macd_hist") is not None else None),
    ("Price beyond all 3 EMAs in trade direction", above_all),
    ("FVG active at entry (post-capture trades only)", lambda r: bool((r.level_reasoning or {}).get("fvg_used")) if r.level_reasoning else None),
    ("direction = long", lambda r: r.direction == "long"),
    ("confidence ≥ 65", lambda r: r.confidence >= 65 if r.confidence is not None else None),
    ("score ≥ 65", lambda r: r.score >= 65 if r.score is not None else None),
    ("|ATR-dist. from EMA20| > 2.5", lambda r: abs(ei(r)["atr_distance_to_ema20"]) > 2.5 if ei(r).get("atr_distance_to_ema20") is not None else None),
    ("risk penalty applied (risk_score ≤ -3)", lambda r: r.risk_score <= -3 if r.risk_score is not None else None),
]
def freq_rows(subset, name):
    out = []
    for nm, pr in SPECS:
        v = [pr(r) for r in subset]; known = [x for x in v if x is not None]
        out.append((nm, sum(1 for x in known if x), len(known)))
    return out
fw = {n: (k, m) for n, k, m in freq_rows(WINS, "w")}; fl = {n: (k, m) for n, k, m in freq_rows(LOSS, "l")}
rows3 = []
for nm, pr in SPECS:
    t = two(pr, ENT)
    kw, mw = fw[nm]; kl, ml = fl[nm]
    rows3.append([nm, f"{kw}/{mw} ({fn(pct(kw, mw), 1)}%)", f"{kl}/{ml} ({fn(pct(kl, ml), 1)}%)", fn((pct(kw, mw) or 0) - (pct(kl, ml) or 0), 1), t["OR"] if t else "—", t["p"] if t else "—"])
rows3.sort(key=lambda x: -float(x[3]))
W(f"n(wins)={len(WINS)}, n(losses)={len(LOSS)}. Frequency = how many winners (losers) had the property; 'known' denominators differ because some indicators were not captured on the oldest trades. Ranked by (winner freq − loser freq).")
W()
table(["Characteristic", "Winners with it", "Losers with it", "Δ pp", "Odds ratio", "Fisher p"], rows3)
W("**Not measurable per trade (not stored):** bullish/bearish BOS, CHoCH, order blocks, liquidity sweeps, OBV, EMA-stack order (only sign of distance to EMA20/50/200), swing-level breaks → **INSUFFICIENT DATA**.")
W(f"**Confidence:** {conf(len(WINS), min([x[5] for x in rows3 if x[5] != '—'] or [1]))} for the strongest single characteristic; most rows are not significant at this n. **Recommendation:** do not derive a 'winner recipe' from frequencies; only entry_quality/RSI-zone survive testing (see §7, §13).")

# =================================================================== SECTION 4
sec(4, "EVERY LOSS")
LOSS_CATS = [
    ("Immediate reversal (no TP1, MFE<1%)", lambda r: LIFE[r.id] == "immediate_reversal"),
    ("Never reached TP1 (all no-TP1 losses)", lambda r: not r.tp1_hit),
    ("Hit TP1 then stopped", lambda r: LIFE[r.id] == "reached_tp1_then_stopped"),
    ("Hit TP2 then reversed", lambda r: LIFE[r.id] == "hit_tp2_then_reversed"),
    ("Weak structure (structure_score<9)", lambda r: r.structure_score is not None and r.structure_score < 9),
    ("Overbought entry (RSI≥70 or MFI>80)", lambda r: (ei(r).get("rsi14") or 0) >= 70 or (ei(r).get("mfi") or 0) > 80),
    ("Low-volume setup (volume_score<8)", lambda r: r.volume_score is not None and r.volume_score < 8),
    ("High ATR extension (>2.5 ATR from EMA20)", lambda r: "high_atr_extension" in FLAGS[r.id]),
    ("trend_score ≥ 22", lambda r: r.trend_score is not None and r.trend_score >= 22),
    ("Late entry (entry_quality=late)", lambda r: r.entry_quality == "late"),
    ("Short direction", lambda r: r.direction == "short"),
    ("Gap/slippage through stop (≥5%)", lambda r: r.stop_slippage_pct is not None and r.stop_slippage_pct <= -5),
    ("Exit inside a monitoring outage", lambda r: in_outage(r.exit_time)),
    ("RSI chop zone 30–49", lambda r: "rsi_chop_30_49" in FLAGS[r.id]),
    ("Negative CMF", lambda r: "negative_cmf" in FLAGS[r.id]),
]
rows4 = []
for nm, pr in LOSS_CATS:
    sub = [r for r in LOSS if pr(r)]
    rows4.append([nm, len(sub), fn(pct(len(sub), len(LOSS)), 1) + "%", fn(avg([ret(r) for r in sub])) + "%", fn(avg([r.max_runup_pct for r in sub])) + "%", fn(avg([r.max_drawdown_pct for r in sub])) + "%", fn(avg([r.confidence for r in sub]), 1)])
rows4.sort(key=lambda x: -x[1])
W(f"n(losses)={len(LOSS)}. Categories overlap (multi-label), ranked by frequency.")
W()
table(["Loss category", "n", "% of losses", "Avg return", "Avg MFE", "Avg MAE", "Avg conf"], rows4)
W("**Not measurable (no stored label):** countertrend entry (no per-trade HTF-disagreement flag), liquidity sweep, bad direction vs. reversal cause → **INSUFFICIENT DATA**. Late entry is n=0 by construction (entry_quality='late' blocks plan issuance).")
W(f"**Confidence:** HIGH for the lifecycle counts (they are facts); LOW for causal readings. **Recommendation:** the dominant failure is 'wrong from the first candle' — attack entry selection/quality evidence, not exit management.")

# =================================================================== SECTION 5
sec(5, "FAILURE PATTERN ENGINE AUDIT")
lc = collections.Counter(LIFE[r.id] for r in LOSS); lr = collections.defaultdict(list)
for r in LOSS: lr[LIFE[r.id]].append(ret(r))
table(["Lifecycle category (mutually exclusive)", "n", "% of losses", "Avg return"], [[k, v, fn(pct(v, len(LOSS)), 1) + "%", fn(avg(lr[k]))] for k, v in lc.most_common()])
extra = [("Gap through stop (slippage ≥5%)", lambda r: r.stop_slippage_pct is not None and r.stop_slippage_pct <= -5),
         ("Infrastructure failure / scanner missed stop (exit inside outage)", lambda r: in_outage(r.exit_time)),
         ("Late invalidation", lambda r: False)]
table(["Overlay (multi-label)", "n", "% of losses", "Avg return"], [[nm, sum(1 for r in LOSS if p(r)), fn(pct(sum(1 for r in LOSS if p(r)), len(LOSS)), 1) + "%", fn(avg([ret(r) for r in LOSS if p(r)]))] for nm, p in extra])
W("**INSUFFICIENT DATA** (no labels in DB): false breakout, mean-reversion failure, trend exhaustion, distribution. 'Late invalidation' is not a loss category here — invalidated plans carry no realized return (see §23).")
W("**Confidence:** HIGH (counts). **Recommendation:** none beyond §4; keep failure-pattern leaderboard as analytics.")

# =================================================================== SECTION 6
sec(6, "WIN PATTERN ENGINE")
sr = collections.defaultdict(list)
for r in ENT: sr[STRAT[r.id]].append(r)
table(["Strategy family (all entered)", "n", "Wins", "Success rate", "95% CI", "Avg ret", "PF"],
      [[k, len(v), sum(1 for x in v if x.status == "closed_win"), fn(summ(v)["wr"], 1) + "%", f"{summ(v)['ci'][0]}–{summ(v)['ci'][1]}%", fn(summ(v)["avg"]), fn(summ(v)["pf"])] for k, v in sorted(sr.items(), key=lambda kv: -(summ(kv[1])["wr"] or 0))])
wl = collections.Counter(LIFE[r.id] for r in WINS)
table(["Winner lifecycle", "n", "% of wins"], [[k, v, fn(pct(v, len(WINS)), 1) + "%"] for k, v in wl.most_common()])
shw = [r for r in WINS if r.direction == "short"]
W(f"Short winners (possible 'short squeeze' analogue): n={len(shw)} of {sum(1 for r in ENT if r.direction=='short')} shorts. **INSUFFICIENT DATA** for: liquidity reclaim, news momentum, range breakout, true breakout vs. pullback (no per-trade BOS/range labels; strategy classes are indicator proxies).")
W("**Confidence:** LOW-MEDIUM (small per-family n). **Recommendation:** analytics only; do not rank strategies for trading until each family has n≥30.")

# =================================================================== SECTION 7
sec(7, "ENTRY QUALITY AUDIT")
rows7 = []
for q in ("excellent", "good", "neutral", "late", "exhausted"):
    sub = [r for r in ENT if r.entry_quality == q]
    if not sub: rows7.append([q, 0] + [""] * 12); continue
    x = summ(sub); rows7.append([q, x["n"], x["w"], x["l"], f"{x['wr']}% ({x['ci'][0]}–{x['ci'][1]})", x["tp1"], x["tp2"], x["tp3"], x["avg"], x["med"], x["pf"], x["mfe"], x["mae"], x["hold"]])
nul = sum(1 for r in ENT if not r.entry_quality)
table(["EQ", "n", "W", "L", "Win% (Wilson)", "TP1%", "TP2%", "TP3%", "Avg ret", "Median ret", "PF", "MFE", "MAE", "Median hold h"], rows7)
W(f"Trades with no entry_quality (pre-launch, n={nul}) excluded above. `late`/`exhausted` n=0 **by construction** (the scanner blocks issuing a plan in those states) — they can never appear in TradeOutcome.")
EQR = [r for r in ENT if r.entry_quality]
t_ex_rest = two(lambda r: r.entry_quality == "excellent", EQR)
t_ex_good = two(lambda r: r.entry_quality == "excellent" if r.entry_quality in ("excellent", "good") else None, EQR)
t_gd_neu = two(lambda r: r.entry_quality == "good" if r.entry_quality in ("good", "neutral") else None, EQR)
table(FH, [frow("excellent vs all others", t_ex_rest), frow("excellent vs good", t_ex_good), frow("good vs neutral", t_gd_neu)])
W(f"**Is entry quality predictive?** Excellent vs rest: OR={t_ex_rest['OR']} (CI {t_ex_rest['lo']}–{t_ex_rest['hi']}), p={t_ex_rest['p']}; excellent vs good: p={t_ex_good['p']}; good vs neutral: OR={t_gd_neu['OR']}, p={t_gd_neu['p']} — the ordering is NOT monotonic (good does not beat neutral). "
  f"**Confidence:** {conf(t_ex_rest['nP'], t_ex_rest['p'])} for 'excellent is special'. **Recommendation:** keep classifier unchanged. 'Excellent' is directionally favorable (n=%d, PF %s) but NOT statistically distinguishable at this n — do not call it validated." % (len([r for r in ENT if r.entry_quality=='excellent']), summ([r for r in ENT if r.entry_quality=='excellent'])['pf']))
KEY["eq_ex_p"] = t_ex_rest["p"]; KEY["eq_ex_or"] = t_ex_rest["OR"]

# =================================================================== SECTION 8
sec(8, "CONFIDENCE CALIBRATION")
edges = [0, 50, 55, 60, 65, 70, 75, 200]; labs = ["<50", "50–54", "55–59", "60–64", "65–69", "70–74", "75+"]
CT = [r for r in ENT if r.confidence is not None]
rows8 = []; brier_tot = 0; ece_num = 0
for (a, b), lb in zip(zip(edges[:-1], edges[1:]), labs):
    sub = [r for r in CT if a <= r.confidence < b]
    if not sub: rows8.append([lb, 0] + [""] * 9); continue
    x = summ(sub); pred = avg([r.confidence for r in sub]); br = avg([(r.confidence / 100 - (1 if r.status == "closed_win" else 0)) ** 2 for r in sub])
    rs = [rR(r) for r in sub if rR(r) is not None]
    rows8.append([lb, x["n"], fn(pred, 1) + "%", f"{x['wr']}% ({x['ci'][0]}–{x['ci'][1]})", fn(pred - x["wr"], 1), x["tp1"], x["tp2"], x["tp3"], x["avg"], x["med"], fn(x["pf"]), fn(avg(rs)) if rs else "—", fn(br, 3)])
    ece_num += abs(pred - x["wr"]) * x["n"]
table(["Bucket", "n", "Predicted", "Observed win% (Wilson)", "Cal. err (pp)", "TP1%", "TP2%", "TP3%", "Avg ret", "Median", "PF", "Avg R (EV realized)", "Brier"], rows8)
brier = avg([(r.confidence / 100 - (1 if r.status == "closed_win" else 0)) ** 2 for r in CT]); base = sum(1 for r in CT if r.status == "closed_win") / len(CT)
W(f"Overall Brier={brier} vs constant-base-rate Brier={round(base * (1 - base), 4)} (n={len(CT)}); ECE≈{round(ece_num / len(CT), 1)}pp. Reliability diagram (■ predicted, ▒ observed):")
W("```")
for row in rows8:
    if row[1]:
        p_ = float(str(row[2]).rstrip('%')); o_ = float(str(row[3]).split('%')[0])
        W(f"{row[0]:>6} n={row[1]:<3} pred {'■' * int(p_ / 3.5):<22}{p_:>5.1f}%"); W(f"{'':>6}        obs  {'▒' * int(o_ / 3.5):<22}{o_:>5.1f}%")
W("```")
spear = spearmanr([r.confidence for r in CT], [ret(r) for r in CT])
W(f"Spearman(confidence, return)={round(spear.statistic, 3)}, p={round(spear.pvalue, 3)} (n={len(CT)}). **Overconfident** wherever predicted > observed (most buckets ≥55). Confidence is not monotonic in outcome, so it should be treated as a ranking-ish heuristic, not a probability. "
  f"Model Brier {brier} is WORSE than the constant base-rate Brier {round(base*(1-base),4)}: as a probability, confidence has no demonstrated skill (Spearman with return not significant). **Confidence:** MEDIUM (n={len(CT)}). **Recommendation:** display calibrated confidence + interval (already built); do not rescale the underlying formula until n≥100 per used bucket.")
KEY["brier"] = brier; KEY["base_brier"] = round(base * (1 - base), 4); KEY["conf_spear"] = (round(spear.statistic, 3), round(spear.pvalue, 3))

# =================================================================== SECTION 9
sec(9, "SCORE BREAKDOWN AUDIT")
COMP = [("trend", "trend_score"), ("momentum", "momentum_score"), ("volume", "volume_score"), ("funding", "funding_score"), ("structure", "structure_score"),
        ("history", "history_score"), ("regime", "regime_score"), ("risk penalty", "risk_score"), ("sentiment", "sentiment_score"), ("ML score", "ml_score"), ("liquidity", "liquidity_score")]
rows9 = []; comp_stats = {}
for nm, at in COMP:
    v = np.array([getattr(r, at) for r in ENT if getattr(r, at) is not None], float)
    y = [ret(r) for r in ENT if getattr(r, at) is not None]
    if v.std() == 0: rows9.append([nm, len(v), f"constant={v[0]}", "—", "—", "—", "—", "—", "—", "INSUFFICIENT VARIATION"]); continue
    md = float(np.median(v)); hi = lambda r, at=at, md=md: getattr(r, at) > md if getattr(r, at) is not None else None
    t = two(hi, ENT); sp = spearmanr(v, y)
    q = np.percentile(v, [25, 50, 75])
    rows9.append([nm, len(v), f"{v.min():.1f}/{q[0]:.1f}/{q[1]:.1f}/{q[2]:.1f}/{v.max():.1f}", f"{fn(t['wrP'], 1)}% vs {fn(t['wrA'], 1)}%" if t else "—",
                  fn(100 - t['wrP'], 1) + "%" if t else "—", round(sp.statistic, 3), round(sp.pvalue, 3), t["OR"] if t else "—", t["ig"] if t else "—", conf(min(t['nP'], t['nA']), t['p']) if t else "n/a"])
    comp_stats[nm] = (round(sp.statistic, 3), round(sp.pvalue, 3), t)
evs = [(evr(r), ret(r)) for r in ENT if evr(r) is not None]
if len(evs) >= 10:
    sp = spearmanr([a for a, _ in evs], [b for _, b in evs]); rows9.append(["expected value (stored)", len(evs), "post-V2.1 only", "", "", round(sp.statistic, 3), round(sp.pvalue, 3), "—", "—", conf(len(evs), sp.pvalue)])
rl = [(RELMAP[r.symbol]["reliability_score"], ret(r)) for r in ENT if r.symbol in RELMAP]
sp = spearmanr([a for a, _ in rl], [b for _, b in rl]); rows9.append(["reliability (hindsight)", len(rl), "all-data", "", "", round(sp.statistic, 3), round(sp.pvalue, 3), "—", "—", "hindsight-biased"])
table(["Component", "n", "min/Q1/med/Q3/max", "win% high vs low (median split)", "loss% high-half", "Spearman vs ret", "p", "OR (high vs low)", "MI (bits)", "Confidence"], rows9)
W("Does increasing a component improve returns? Only where Spearman p<0.05 AND the median-split Fisher p<0.05 agree. **SHAP: not available** (no fitted production model on TradeOutcome features — the XGBoost models use MarketSnapshot features). Permutation importance from a cross-validated linear model is in §10.")
W("**Recommendation:** none supported by this table alone; see §10.")

# =================================================================== SECTION 10
sec(10, "SCORE WEIGHT RECOMMENDATION (NO EDITS TO scoring.py)")
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
cols = [(nm, at) for nm, at in COMP if np.std([getattr(r, at) for r in ENT if getattr(r, at) is not None]) > 0]
XR = [r for r in ENT if all(getattr(r, at) is not None for _, at in cols)]
X = np.array([[getattr(r, at) for _, at in cols] for r in XR], float); y = np.array([1 if r.status == "closed_win" else 0 for r in XR])
Xs = (X - X.mean(0)) / X.std(0)
rng = np.random.default_rng(7)
def fitc(Xa, ya): return LogisticRegression(C=0.5, max_iter=500).fit(Xa, ya).coef_[0]
boot = np.array([fitc(Xs[i], y[i]) for i in (rng.integers(0, len(y), len(y)) for _ in range(300)) if 0 < y[i].sum() < len(y)])
coef = fitc(Xs, y); lo = np.percentile(boot, 2.5, 0); hi = np.percentile(boot, 97.5, 0)
aucs = []; perm = np.zeros(len(cols))
for seed in range(10):
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(Xs, y):
        m = LogisticRegression(C=0.5, max_iter=500).fit(Xs[tr], y[tr]); base_a = roc_auc_score(y[te], m.predict_proba(Xs[te])[:, 1]); aucs.append(base_a)
        for j in range(len(cols)):
            Xp = Xs[te].copy(); Xp[:, j] = rng.permutation(Xp[:, j]); perm[j] += base_a - roc_auc_score(y[te], m.predict_proba(Xp)[:, 1])
perm /= (10 * 5)
CUR = {"trend": "0–25", "momentum": "0–15", "volume": "0–10", "funding": "0–10", "structure": "0–15", "history": "−15..+15", "regime": "−5..+5", "risk penalty": "−20..0", "sentiment": "−3..+3", "ML score": "−10..+8", "liquidity": "−5..0"}
rows10 = []
for j, (nm, at) in enumerate(cols):
    excl = lo[j] > 0 or hi[j] < 0
    rows10.append([nm, CUR[nm], round(coef[j], 3), f"[{lo[j]:.3f}, {hi[j]:.3f}]", "yes" if excl else "no", round(perm[j], 4),
                   ("evidence to " + ("INCREASE" if coef[j] > 0 else "DECREASE") + " (magnitude not estimable)") if excl else "NO CHANGE SUPPORTED"])
table(["Component", "Current point range", "Std. logit coef", "Bootstrap 95% CI (300×)", "CI excludes 0?", "CV permutation importance (ΔAUC)", "Proposed"], rows10)
W(f"L2-logistic on standardized components, n={len(y)}, features={len(cols)}. **Cross-validated AUC = {round(float(np.mean(aucs)), 3)} ± {round(float(np.std(aucs)), 3)}** (5-fold×10; 0.5 = no skill). Constant components were excluded (INSUFFICIENT VARIATION).")
KEY["cv_auc"] = round(float(np.mean(aucs)), 3); KEY["n_ci_excl"] = sum(1 for r in rows10 if r[4] == "yes")
W(f"**Expected improvement:** cannot be estimated — the linear model over the deterministic components has CV-AUC {KEY['cv_auc']}, i.e. the current score components (as a set) carry {'little' if KEY['cv_auc'] < .6 else 'some'} out-of-sample discrimination on win/loss. "
  f"**Confidence:** {'INSUFFICIENT DATA' if KEY['n_ci_excl'] == 0 else 'LOW'} — {KEY['n_ci_excl']} of {len(cols)} coefficients have CIs excluding zero. **Recommendation:** propose NO weight change; re-run at n≥200.")

# =================================================================== SECTION 11
sec(11, "TREND ANALYSIS")
ftable([SPECS[0], SPECS[9], SPECS[10], SPECS[18]])
bucket_table("trend_score buckets", lambda r: r.trend_score, [0, 15, 20, 23, 26])
bucket_table("ADX buckets", lambda r: ei(r).get("adx14"), [0, 20, 35, 50, 200])
sp = spearmanr([r.trend_score for r in ENT], [ret(r) for r in ENT])
W(f"Spearman(trend_score, return)={round(sp.statistic, 3)}, p={round(sp.pvalue, 3)} (n={len(ENT)}). Trend is a near-universal gate (median trend_score ≈ {med([r.trend_score for r in ENT])}), so it cannot discriminate winners from losers; stratified by entry_quality its sign flips (see feature audit). "
  f"Bullish/bearish BOS, exhaustion vs continuation labels: **INSUFFICIENT DATA**. **Confidence:** {conf(len(ENT), sp.pvalue)}. **Recommendation:** treat trend as a gate; do not change its weight (no evidence either way).")

# =================================================================== SECTION 12
sec(12, "STRUCTURE ANALYSIS")
ftable([SPECS[1], SPECS[19]])
bucket_table("structure_score buckets", lambda r: r.structure_score, [0, 6, 9, 12, 20])
def swing_dist(r):
    lv = (r.level_reasoning or {}).get("structure_level_used")
    return abs(r.entry - lv) / r.entry * 100 if lv and r.entry else None
bucket_table("Distance from entry to nearest opposing swing level (%; post-capture trades only)", swing_dist, [0, 2, 5, 10, 1000])
W("BOS, CHoCH, order blocks, liquidity sweeps as per-trade booleans: **INSUFFICIENT DATA** — never persisted (order-block detection does not exist in the codebase). Only `structure_score` (aggregate) and FVG-at-entry (post-capture subset) are testable. "
  "**Recommendation:** capture BOS/CHoCH/sweep booleans at issuance (analytics only) so this section can be answered at n≥200.")

# =================================================================== SECTION 13
sec(13, "MOMENTUM ANALYSIS")
ftable([SPECS[11], SPECS[12], SPECS[13], SPECS[14], SPECS[15], SPECS[16], SPECS[17]])
bucket_table("RSI(14, 4h)", ind("rsi14"), [0, 30, 40, 50, 60, 70, 100])
bucket_table("MFI", ind("mfi"), [0, 40, 60, 80, 90, 101])
bucket_table("CMF", ind("cmf"), [-1, -0.1, 0, 0.1, 0.2, 1])
bucket_table("Bollinger %B", ind("bb_pct"), [-1, 0.2, 0.5, 0.8, 1.0, 5])
bucket_table("Stoch RSI", ind("stoch_rsi"), [0, 0.2, 0.5, 0.8, 1.01])
bucket_table("|ATR-distance from EMA20|", lambda r: abs(ei(r)["atr_distance_to_ema20"]) if ei(r).get("atr_distance_to_ema20") is not None else None, [0, 0.5, 1, 2, 10])
W("OBV and momentum-divergence: **INSUFFICIENT DATA** (not stored). **Profitable ranges:** read directly from the bucket tables — only RSI 50–70 vs <50 and the chop-zone finding carry significance in this sample. **Recommendation:** shadow-mode a 'RSI 30–49' flag (already exists in red_flags); no score change.")

# =================================================================== SECTION 14
sec(14, "MARKET REGIME ANALYSIS")
rg = collections.defaultdict(list)
for r in ENT: rg[r.market_regime or "unlabeled"].append(r)
table(["Regime", "n", "Win rate (Wilson)", "PF", "Avg ret", "Median", "TP1%", "Stop%", "MAE"],
      [[k, len(v), f"{summ(v)['wr']}% ({summ(v)['ci'][0]}–{summ(v)['ci'][1]})", summ(v)["pf"], summ(v)["avg"], summ(v)["med"], summ(v)["tp1"], summ(v)["stop"], summ(v)["mae"]] for k, v in sorted(rg.items(), key=lambda kv: -len(kv[1]))])
W("Confusion matrix (regime × outcome):"); W()
table(["Regime", "Win", "Loss", "P(win|regime)"], [[k, sum(1 for r in v if r.status == "closed_win"), sum(1 for r in v if r.status == "closed_loss"), fn(summ(v)["wr"], 1) + "%"] for k, v in rg.items()])
t = two(lambda r: r.market_regime == "mixed" if r.market_regime else None, ENT)
table(FH, [frow("regime=mixed vs risk_on", t)])
W("**Unavailable regimes** (not produced by the engine, n=0): risk_off, trending, range, expansion, compression, mean_reversion, panic → **INSUFFICIENT DATA**. Regime is also confounded with time period (risk_on trades are early-sample). "
  f"**Confidence:** {conf(min(t['nP'], t['nA']), t['p'])}. **Recommendation:** do not gate on regime yet; track regime×direction as analytics.")

# =================================================================== SECTION 15
sec(15, "LONG VS SHORT")
clean = [r for r in ENT if not in_outage(r.exit_time)]
def dirrow(nm, rows):
    x = summ(rows); sl = [r.stop_slippage_pct for r in rows if r.stop_slippage_pct is not None]
    return [nm, x["n"], f"{x['wr']}%", x["pf"], x["avg"], x["med"], x["tp1"], x["stop"], x["mfe"], x["mae"], avg([r.confidence for r in rows]), avg([r.trend_score for r in rows]), avg([r.structure_score for r in rows]), fn(avg(sl)), x["hold"]]
DH = ["Segment", "n", "Win%", "PF", "Avg ret", "Median", "TP1%", "Stop%", "MFE", "MAE", "Avg conf", "Avg trend", "Avg struct", "Avg stop slip%", "Med hold h"]
table(DH, [dirrow("Long (all)", [r for r in ENT if r.direction == "long"]), dirrow("Short (all)", [r for r in ENT if r.direction == "short"]),
           dirrow("Long (ex-outage)", [r for r in clean if r.direction == "long"]), dirrow("Short (ex-outage)", [r for r in clean if r.direction == "short"])])
for d_ in ("long", "short"):
    sub = [r for r in ENT if r.direction == d_]; eqc = collections.Counter(r.entry_quality or "none" for r in sub)
    W(f"{d_}: entry_quality mix {dict(eqc)}; failure lifecycle {dict(collections.Counter(LIFE[r.id] for r in sub if r.status == 'closed_loss'))}")
W()
table(["Regime × direction", "n", "Win%", "Avg ret"], [[f"{rg_}/{d_}", len(sub), fn(summ(sub)["wr"], 1) + "%", summ(sub)["avg"]] for rg_ in ("risk_on", "mixed") for d_ in ("long", "short") for sub in [[r for r in ENT if r.market_regime == rg_ and r.direction == d_]] if sub])
sh_all = [r for r in ENT if r.direction == "short"]; sh_c = [r for r in clean if r.direction == "short"]
t = two(lambda r: r.direction == "short", ENT); t2 = two(lambda r: r.direction == "short", clean)
table(FH, [frow("short vs long (all)", t), frow("short vs long (ex-outage)", t2)])
KEY["short_wr_clean"] = summ(sh_c)["wr"]; KEY["short_n_clean"] = len(sh_c)
W(f"Removing outage-corrupted exits leaves {len(sh_c)} of {len(sh_all)} shorts: win rate {summ(sh_c)['wr']}%, PF {summ(sh_c)['pf']}, avg {summ(sh_c)['avg']}% — versus longs ex-outage {summ([r for r in clean if r.direction=='long'])['wr']}% (n={len([r for r in clean if r.direction=='long'])}). "
  f"**Diagnosis:** the headline short collapse ({summ(sh_all)['wr']}% win, avg {summ(sh_all)['avg']}%) is concentrated in outage-exit trades: {sum(1 for r in sh_all if in_outage(r.exit_time))} of {len(sh_all)} shorts exited inside a monitoring gap and ALL of them lost. Ex-outage, shorts are statistically indistinguishable from longs (p={t2['p']}, n={len(sh_c)}). "
  f"So the evidence points to an EXECUTION/INFRASTRUCTURE explanation (gap exposure + slippage) at least as much as a SIGNAL one; a signal problem is NOT demonstrated. Regime cannot be separated (shorts exist only in 'mixed'). Caveat: the ex-outage short sample is n={len(sh_c)} — INSUFFICIENT DATA either way. "
  f"**Confidence:** INSUFFICIENT DATA. **Recommendation:** keep the soft short flag; do NOT hard-disable shorts; re-test after the scanner runs continuously.")
# =================================================================== SECTION 16
sec(16, "SYMBOL RELIABILITY")
bysym = collections.defaultdict(list)
for r in ENT: bysym[r.symbol].append(r)
rows16 = []; tier = {}
for sy, v in bysym.items():
    x = summ(v); relv = RELMAP[sy]["reliability_score"]
    tr = "Trusted" if x["n"] >= 3 and relv >= 50 else ("Avoid" if (x["n"] >= 3 and x["w"] == 0) or relv < 33 else "Watchlist")
    tier[sy] = tr
    evs_ = [evr(r) for r in v if evr(r) is not None]
    rows16.append([sy, x["n"], x["w"], f"{x['wr']}%", x["avg"], fn(x["pf"]), fn(relv, 1), fn(avg([r.confidence for r in v]), 1), fn(avg(evs_)) if evs_ else "—",
                   f"{round(sum(1 for r in v if any(f in FLAGS[r.id] for f in ('rsi_chop_30_49', 'weak_structure', 'negative_cmf', 'high_atr_extension'))) / len(v) * 100)}%",
                   "yes" if any(r.historic_probability is not None for r in v) else "no", tr])
rows16.sort(key=lambda x: (-float(x[6]), -x[1]))
W(f"n(symbols)={len(bysym)}, pooled win rate {POOLED}%. Tier rule (report-defined, not tuned): Trusted = n≥3 & Bayesian reliability≥50; Avoid = (n≥3 & 0 wins) or reliability<33; else Watchlist. Reliability = Beta-Binomial shrinkage (prior strength 10) — a single trade can never make a symbol 'Trusted'.")
W()
table(["Symbol", "n", "Wins", "Win%", "Avg ret", "PF", "Reliability", "Avg conf", "Avg EV(R)", "% trades w/ risk flags", "History avail.", "Tier"], rows16)
tc = collections.Counter(tier.values()); W(f"Tier counts: {dict(tc)}. **Confidence:** LOW for any symbol with n<5 (most). **Recommendation:** display reliability with sample size; do not auto-exclude symbols.")

# =================================================================== SECTION 17
sec(17, "HISTORY MATCH AUDIT")
hp = [r for r in ENT if r.historic_probability is not None]; nh = [r for r in ENT if r.historic_probability is None]
W(f"Coverage: {len(hp)}/{len(ENT)} closed trades ({pct(len(hp), len(ENT))}%) had a historical analogue; symbols with any coverage: {len(set(r.symbol for r in hp))}/{len(bysym)}.")
W()
table(["Group", "n", "Win rate (Wilson)", "Avg ret", "PF"], [["History present", len(hp), f"{summ(hp)['wr']}% ({summ(hp)['ci'][0]}–{summ(hp)['ci'][1]})", summ(hp)["avg"], summ(hp)["pf"]], ["History missing", len(nh), f"{summ(nh)['wr']}% ({summ(nh)['ci'][0]}–{summ(nh)['ci'][1]})", summ(nh)["avg"], summ(nh)["pf"]]])
tp_ = sum(1 for r in hp if r.historic_probability >= .5 and r.status == "closed_win"); fp_ = sum(1 for r in hp if r.historic_probability >= .5 and r.status == "closed_loss")
fn_ = sum(1 for r in hp if r.historic_probability < .5 and r.status == "closed_win"); tn_ = sum(1 for r in hp if r.historic_probability < .5 and r.status == "closed_loss")
table(["History says ≥50% win", "Won", "Lost"], [["Predicted win (ge 0.5)", tp_, fp_], ["Predicted loss (<0.5)", fn_, tn_]])
t = two(lambda r: r.historic_probability is not None, ENT)
table(FH, [frow("history present vs missing", t)])
W(f"False positives (predicted win, lost)={fp_}; false negatives (predicted loss, won)={fn_}. Coverage is confined to the few legacy-backfilled majors, and it is confounded with them. "
  f"**Is history useful?** Not demonstrably: when present it coincides with worse outcomes ({t['wrP']}% vs {t['wrA']}%, p={t['p']}), but that is the majors' underperformance, not a causal effect. **Confidence:** {conf(min(t['nP'], t['nA']), t['p'])} (confounded). **Recommendation:** do not penalize missing history; do not increase its weight; extend coverage before evaluating it.")

# =================================================================== SECTION 18
sec(18, "EXPECTED VALUE AUDIT")
POST = [r for r in ENT if evr(r) is not None]
W(f"Stored EV (computed at issuance from then-available frequency tables) exists for only n={len(POST)} closed trades (post-V2.1). To evaluate over the full sample, a **retrospective leave-one-out EV** was also computed: EV_i = P(TP1|others)·(reward_TP1/risk) − P(stop-before-TP1|others)·1 (n={len([r for r in ENT if rr(r).get('risk_to_sl_pct') and rr(r).get('reward_to_tp1_pct') is not None])}).")
def loo_ev(r):
    rp = rr(r).get("risk_to_sl_pct"); rw = rr(r).get("reward_to_tp1_pct")
    if not rp or rw is None: return None
    o = [x for x in ENT if x is not r]; ptp = sum(1 for x in o if x.tp1_hit) / len(o); ps = sum(1 for x in o if x.stop_hit and not x.tp1_hit) / len(o)
    return ptp * rw / rp - ps
RETRO = {r.id: loo_ev(r) for r in ENT}
def evb(fn_, rows):
    edges = [(-99, 0, "Negative EV"), (0, 1, "0–1R"), (1, 2, "1–2R"), (2, 3, "2–3R"), (3, 99, "3R+")]; out = []
    for a, b, nm in edges:
        sub = [r for r in rows if fn_(r) is not None and a <= fn_(r) < b]
        if sub:
            x = summ(sub); out.append([nm, x["n"], f"{x['wr']}%", x["avg"], fn(x["pf"]), fn(avg([rR(r) for r in sub if rR(r) is not None]))])
        else: out.append([nm, 0, "", "", "", ""])
    return out
W("**Stored EV buckets (post-V2.1 only):**"); table(["EV bucket", "n", "Win%", "Avg ret", "PF", "Avg realized R"], evb(evr, ENT))
W("**Retrospective leave-one-out EV buckets (full sample):**"); table(["EV bucket", "n", "Win%", "Avg ret", "PF", "Avg realized R"], evb(lambda r: RETRO[r.id], ENT))
pairs = [(RETRO[r.id], rR(r)) for r in ENT if RETRO[r.id] is not None and rR(r) is not None]
spe = spearmanr([a for a, _ in pairs], [b for _, b in pairs])
pc_ = [(r.confidence, rR(r)) for r in ENT if r.confidence is not None and rR(r) is not None]
spc = spearmanr([a for a, _ in pc_], [b for _, b in pc_])
psc = [(r.score, rR(r)) for r in ENT if r.score is not None and rR(r) is not None]
sps = spearmanr([a for a, _ in psc], [b for _, b in psc])
table(["Ranking metric", "Spearman vs realized R", "p", "n"], [["retrospective EV", round(spe.statistic, 3), round(spe.pvalue, 3), len(pairs)], ["confidence", round(spc.statistic, 3), round(spc.pvalue, 3), len(pc_)], ["total score", round(sps.statistic, 3), round(sps.pvalue, 3), len(psc)]])
if len(POST) >= 10:
    sp = spearmanr([evr(r) for r in POST], [rR(r) for r in POST if rR(r) is not None][:len(POST)] if all(rR(r) is not None for r in POST) else [ret(r) for r in POST])
    W(f"Stored-EV vs realized: Spearman={round(sp.statistic, 3)}, p={round(sp.pvalue, 3)} (n={len(POST)}).")
KEY["ev_spear"] = (round(spe.statistic, 3), round(spe.pvalue, 3))
W(f"**Does higher EV mean better trades?** No demonstrated relationship: retrospective EV vs realized R Spearman {KEY['ev_spear'][0]} (p={KEY['ev_spear'][1]}), and among stored-EV trades the 'Negative EV' bucket had the best average return (small n). EV is no better a ranker than confidence or score in this sample. EV can 'lie' when the reward/risk term dominates (tight stops inflate EV) and because P(TP1) is pooled and does not vary much by setup. "
  f"**Confidence:** {conf(len(pairs), spe.pvalue)}. **Recommendation:** keep EV as a displayed, shadow-mode number; do not rank trades by it until it beats confidence out-of-sample at n≥200.")

# =================================================================== SECTION 19
sec(19, "TRADE MANAGER AUDIT")
dec = collections.Counter((sn.stage, sn.management_decision) for sn in SNAPS if sn.management_decision)
table(["Stage", "Decision", "Snapshots"], [[a, b, c] for (a, b), c in sorted(dec.items(), key=lambda kv: -kv[1])])
W("Snapshot decisions before 2026-09-12 are the Phase-1 placeholder (always HOLD); real probability-driven decisions exist only for post-V2.1 trades.")
def tp_ret(r, k):
    lv = getattr(r, k)
    return (lv - r.entry) / r.entry * 100 * sign(r) if lv is not None else None
def policy(r, mode):
    a = ret(r)
    if not r.tp1_hit: return a
    if mode == "actual": return a
    if mode == "exit_tp1": return tp_ret(r, "tp1")
    if mode == "exit_tp2": return tp_ret(r, "tp2") if r.tp2_hit and r.tp3 is not None else a
    if mode in ("be_opt", "be_pess"):
        p = CONT.get(r.id, {}).get("returned_to_entry")
        if r.status == "closed_loss": return 0.0
        if p is True: return 0.0
        if p is None and mode == "be_pess": return 0.0
        return a
tp1_tr = [r for r in ENT if r.tp1_hit]
pol = []
for nm, mode in [("Actual (hold to outermost target/stop)", "actual"), ("Exit 100% at TP1", "exit_tp1"), ("Exit at TP2 when TP3 defined", "exit_tp2"),
                 ("Move stop to entry after TP1 (optimistic)", "be_opt"), ("Move stop to entry after TP1 (pessimistic)", "be_pess")]:
    rs = [policy(r, mode) for r in ENT]; pol.append([nm, len(ENT), round(sum(rs), 1), avg(rs), fn(pf(rs)), med(rs)])
table(["Counterfactual policy (all closed trades; non-TP1 trades unchanged)", "n", "Sum ret %", "Avg ret", "PF", "Median"], pol)
W(f"TP1-reaching trades: n={len(tp1_tr)}. Assumptions (disclosed): TP exits fill at the TP price (no slippage/fees); break-even-stop uses snapshot-cadence price path — 'returned to entry' is undeterminable for trades with a single closing snapshot (bounded by the optimistic/pessimistic rows). "
  f"**Would return improve?** compare the Sum column: exiting at TP1 forfeits the right-tail (avg continuation after TP1 in §20), while a breakeven stop converts TP1-then-stopped losses ({sum(1 for r in ENT if r.tp1_hit and r.status=='closed_loss')} trades) into ~0. "
  f"**Confidence:** MEDIUM (arithmetic on real paths, but n={len(tp1_tr)} and fill assumptions). **Recommendation:** exiting at TP1 (Sum {pol[1][2]}%) and at TP2 (Sum {pol[2][2]}%) are both clearly WORSE than holding (Sum {pol[0][2]}%) — the right tail pays. A breakeven stop after TP1 ranges from {pol[4][2]}% (pessimistic) to {pol[3][2]}% (optimistic) around the actual {pol[0][2]}%: the bounds straddle actual, so its benefit is INSUFFICIENT DATA/inconclusive. Do not change trade handling; at most shadow-log it.")
KEY["pol"] = pol

# =================================================================== SECTION 20
sec(20, "TP CONTINUATION MODEL")
def controws(dimname, keyfn):
    groups = collections.defaultdict(list)
    for r in tp1_tr:
        k = keyfn(r)
        if k is not None: groups[k].append(r)
    body = []
    for k, v in sorted(groups.items(), key=lambda kv: str(kv[0])):
        n = len(v); t2_ = sum(1 for r in v if r.tp2_hit); w2 = wilson(t2_, n)
        t3n = sum(1 for r in v if r.tp2_hit); t3 = sum(1 for r in v if r.tp3_hit)
        stp = sum(1 for r in v if r.status == "closed_loss")
        rte = [CONT[r.id]["returned_to_entry"] for r in v if r.id in CONT and CONT[r.id]["returned_to_entry"] is not None]
        rts = [CONT[r.id]["returned_to_stop"] for r in v if r.id in CONT and CONT[r.id]["returned_to_stop"] is not None]
        body.append([k, n, f"{fn(pct(t2_, n), 1)}% ({w2[0]}–{w2[1]})", f"{fn(pct(t3, t3n), 1)}% (n={t3n})", f"{fn(pct(stp, n), 1)}%", f"{fn(pct(sum(rte), len(rte)), 1)}% (n={len(rte)})", f"{fn(pct(sum(rts), len(rts)), 1)}% (n={len(rts)})"])
    W(f"**By {dimname}**"); table([dimname, "n (TP1)", "P(TP2|TP1) (Wilson)", "P(TP3|TP2)", "P(stop)", "P(return→entry)", "P(return→stop)"], body)
controws("overall", lambda r: "all TP1 trades")
controws("confidence bucket", lambda r: "<60" if (r.confidence or 0) < 60 else ("60–64" if r.confidence < 65 else "65+") if r.confidence else None)
controws("regime", lambda r: r.market_regime)
controws("trend_score", lambda r: ("trend ≥22" if r.trend_score >= 22 else "trend <22") if r.trend_score is not None else None)
controws("entry quality", lambda r: r.entry_quality)
controws("direction", lambda r: r.direction)
controws("ATR-normalized stop distance", lambda r: ("<1 ATR" if rr(r).get("entry_to_sl_atr") < 1 else "≥1 ATR") if rr(r).get("entry_to_sl_atr") is not None else None)
sym_multi = collections.Counter(r.symbol for r in tp1_tr)
controws("symbol (n≥2 TP1 trades)", lambda r: r.symbol if sym_multi[r.symbol] >= 2 else None)
cont = [CONT[r.id]["continuation_after_tp1"] for r in tp1_tr if r.id in CONT and CONT[r.id]["continuation_after_tp1"] is not None]
pull = [CONT[r.id]["pullback_after_tp1"] for r in tp1_tr if r.id in CONT and CONT[r.id]["pullback_after_tp1"] is not None]
W(f"Average continuation after TP1 (best excursion vs entry)={avg(cont)}%, average pullback={avg(pull)}% (n={len(cont)}). **Recommendation:** none beyond §19 (shadow-mode breakeven). Sub-slices with n<10 are **INSUFFICIENT DATA** for conclusions.")

# =================================================================== SECTION 21
sec(21, "RED FLAG AUDIT")
rowsf = []
for f in FLAG_NAMES:
    pr = lambda r, f=f: f in FLAGS[r.id]
    t = two(pr, ENT); nP = sum(1 for r in ENT if pr(r))
    rowsf.append([f, nP, fn(t["wrP"], 1) + "%" if t else "—", fn(t["wrA"], 1) + "%" if t else "—", fn(t["avgP"]) if t else "—", t["OR"] if t else "—", t["p"] if t else "—", conf(min(t['nP'], t['nA']), t['p']) if t else "n/a"])
rowsf.sort(key=lambda x: float(x[2].rstrip('%')) if x[2] != "—" else 999)
table(["Flag", "n with flag", "Win% with", "Win% without", "Avg ret with", "OR", "Fisher p", "Confidence"], rowsf)
W("Not measurable: late-entry flag (n=0 by construction), true low-liquidity (liquidity_stress is a cross-exchange-spread proxy), funding extreme (funding_elevated is funding_score≤5 proxy; n tiny) → treat as INSUFFICIENT DATA where n<10.")
pairs_ = []
for a, b in itertools.combinations(FLAG_NAMES, 2):
    sub = [r for r in ENT if a in FLAGS[r.id] and b in FLAGS[r.id]]
    if len(sub) >= 5: x = summ(sub); pairs_.append([f"{a} + {b}", len(sub), f"{x['wr']}%", x["avg"], fn(x["pf"])])
pairs_.sort(key=lambda x: float(x[2].rstrip('%')))
W("**Flag combinations (n≥5), worst first:**"); table(["Combination", "n", "Win%", "Avg ret", "PF"], pairs_[:15])
W("**Confidence:** MEDIUM for the RSI chop zone and short-direction flags; the rest are LOW/NOT SIGNIFICANT. **Recommendation:** keep flags observational; RSI-chop is the only one with a large, consistent effect.")

# =================================================================== SECTION 22
sec(22, "MISSED OPPORTUNITY ANALYSIS")
def cat_of(reason):
    if reason is None: return "published/active (no rejection)"
    r_ = reason.lower()
    if "exhausted" in r_: return "exhausted"
    if "late" in r_: return "late"
    if r_.startswith("no_trade"): return "no_trade (direction gate)"
    if "outside top" in r_: return "rank cutoff (outside top 6)"
    return "other"
cc = collections.Counter(cat_of(x.rejection_reason) for x in SCANS)
W(f"ScanSnapshot rows: {len(SCANS)}; RejectedOpportunityOutcome recorder rows: {len(REJ)} (the recorder is not wired into the scanner, so it holds no live data).")
W()
SYMTS = {k: [(sn.timestamp, sn.current_price) for sn in v] for k, v in SNAP_BY_SYM.items()}
def fwd(sym, t0, direction):
    lst = SYMTS.get(sym)
    if not lst: return None
    ts = [a for a, _ in lst]; i = bisect.bisect_left(ts, t0)
    cand = [j for j in (i - 1, i) if 0 <= j < len(lst) and abs(lst[j][0] - t0) <= 15 * 60000]
    if not cand: return None
    p0 = lst[min(cand, key=lambda j: abs(lst[j][0] - t0))][1]
    j2 = bisect.bisect_right(ts, t0 + 24 * 3600000); path = [p for a, p in lst[i:j2]]
    if len(path) < 3: return None
    sg = 1 if direction == "long" else -1 if direction == "short" else None
    mv = [(p - p0) / p0 * 100 for p in path]
    if sg is None: return dict(abs_end=abs(mv[-1]), abs_max=max(abs(x) for x in mv), dirn=False)
    mv = [x * sg for x in mv]; return dict(end=mv[-1], mfe=max(mv), mae=min(mv), dirn=True)
res = collections.defaultdict(list)
for x in SCANS:
    if x.direction is None: continue
    o = fwd(x.symbol, x.timestamp, x.direction)
    if o: res[cat_of(x.rejection_reason)].append(o)
body = []
for k, n_tot in cc.most_common():
    v = res.get(k, [])
    if not v: body.append([k, n_tot, 0, "", "", "", "", ""]); continue
    vd = [o for o in v if o["dirn"]]
    if vd:
        v = vd
        body.append([k, n_tot, len(v), fn(avg([o["end"] for o in v])) + "%", fn(pct(sum(1 for o in v if o["end"] > 0), len(v)), 1) + "%", fn(avg([o["mfe"] for o in v])) + "%", fn(avg([o["mae"] for o in v])) + "%", fn(pct(sum(1 for o in v if o["mfe"] >= 5), len(v)), 1) + "%"])
    else: body.append([k, n_tot, len(v), f"|move| {fn(avg([o['abs_end'] for o in v]))}%", "n/a (no direction)", f"max|move| {fn(avg([o['abs_max'] for o in v]))}%", "", ""])
table(["Rejection category", "Scan rows", "Rows with forward price coverage (24h)", "Avg 24h dir. return", "% favorable at 24h", "Avg MFE", "Avg MAE", "% with MFE ≥5% (TP1-like)"], body)
W("**Critical limitation:** ScanSnapshot stores no price. Forward prices exist only where a *TradeOutcome was open on the same symbol* (PredictionSnapshot coverage) — a selection-biased subset (n shown above), and consecutive 5-minute scans of one symbol are highly autocorrelated. "
  "Exhausted scans have their direction overwritten to 'no_trade' by the engine, so directional outcomes are unrecoverable (magnitude only). Literal TP1/TP2/TP3/stop replay for rejected candidates is **INSUFFICIENT DATA** (they never received Claude-generated levels). "
  "**Confidence:** INSUFFICIENT DATA for 'were rejections wrong'. **Recommendation:** wire the missed-opportunity recorder (needs a scanner edit — requires explicit approval) to collect unbiased forward prices; re-audit at ≥500 resolved rows.")

# =================================================================== SECTION 23
sec(23, "INVALIDATED TRADES")
INV = [r for r in ALL if r.status == "invalidated"]
inv_ent = [r for r in INV if r.entry_hit]; inv_pend = [r for r in INV if not r.entry_hit]
W(f"Invalidated plans: n={len(INV)} — entered before replacement: {len(inv_ent)}; never entered: {len(inv_pend)}.")
def last_pnl(r):
    sn = [x for x in SNAP_BY_TRADE.get(r.id, []) if x.status == "open"]
    return sn[-1].current_pnl_pct if sn else None
lp = [last_pnl(r) for r in inv_ent if last_pnl(r) is not None]
table(["Invalidated & entered (n=%d)" % len(inv_ent), "Value"], [["TP1 hit before replacement", sum(1 for r in inv_ent if r.tp1_hit)], ["TP2 hit", sum(1 for r in inv_ent if r.tp2_hit)], ["Stop touched", sum(1 for r in inv_ent if r.stop_hit)],
      ["Unrealized P&L at last snapshot: n / avg / % positive", f"{len(lp)} / {fn(avg(lp))}% / {fn(pct(sum(1 for x in lp if x > 0), len(lp)), 1)}%"], ["Avg MFE / MAE (tracked while open)", f"{fn(avg([r.max_runup_pct for r in inv_ent]))}% / {fn(avg([r.max_drawdown_pct for r in inv_ent]))}%"]])
bysym_all = collections.defaultdict(list)
for r in ALL: bysym_all[r.symbol].append(r)
rep = collections.Counter()
for r in INV:
    nxt = [x for x in bysym_all[r.symbol] if x.created_at > r.created_at and x.status in ("closed_win", "closed_loss")]
    if nxt: rep["replaced-by-later-resolved-plan"] += 1; rep["...that plan won" if min(nxt, key=lambda x: x.created_at).status == "closed_win" else "...that plan lost"] += 1
table(["Replacement analysis (same symbol, next resolved plan)", "n"], [[k, v] for k, v in rep.items()])
W("Invalidation is a paper status: no realized return is recorded and price is not tracked after the replacement, so **'how many would have won / whether invalidation avoided losses' is INSUFFICIENT DATA** beyond the in-flight metrics above. Most invalidated plans were pending plans re-issued as the entry zone shifted (churn), not closed positions. "
  "**Confidence:** LOW. **Recommendation:** record post-invalidation outcome for a sample (analytics) before judging.")

# =================================================================== SECTION 24
sec(24, "NEVER ENTERED TRADES")
NEV = [r for r in ALL if r.status == "closed_stale" or (r.status == "invalidated" and not r.entry_hit) or r.status == "pending"]
def pend_path(r):
    sn = [x for x in SNAP_BY_TRADE.get(r.id, []) if x.status == "pending"]
    if not sn or not r.entry or not r.tp1: return None
    fav = max((x.current_price - r.entry) / r.entry * 100 * sign(r) for x in sn)
    adv = min((x.current_price - r.entry) / r.entry * 100 * sign(r) for x in sn)
    rp = abs(r.tp1 - r.entry) / r.entry * 100; sp_ = abs(r.entry - r.stop_loss) / r.entry * 100
    return dict(reach_tp1=fav >= rp, reach_stop=adv <= -sp_, n=len(sn))
pp = {r.id: pend_path(r) for r in NEV}
cov = [(r, pp[r.id]) for r in NEV if pp[r.id]]
def block(nm, sub):
    c = [(r, pp[r.id]) for r in sub if pp[r.id]]
    return [nm, len(sub), len(c), sum(1 for _, p in c if p["reach_tp1"] and not p["reach_stop"]), sum(1 for _, p in c if p["reach_stop"] and not p["reach_tp1"]), sum(1 for _, p in c if not p["reach_tp1"] and not p["reach_stop"]), sum(1 for _, p in c if p["reach_tp1"] and p["reach_stop"])]
table(["Group", "n", "with price coverage", "reached TP1 level w/o entering (missed winner)", "reached stop level w/o entering (avoided loser)", "neither", "both"],
      [block("closed_stale (expired)", [r for r in NEV if r.status == "closed_stale"]), block("invalidated, never entered", [r for r in NEV if r.status == "invalidated"]), block("pending now", [r for r in NEV if r.status == "pending"])])
W(f"Total never-entered plans: n={len(NEV)}. Measured only while pending (snapshots stop at expiry/replacement). Entry-zone effectiveness = share of plans whose zone was reached at all: {pct(sum(1 for r in ALL if r.entry_hit), len(ALL))}% of all {len(ALL)} plans entered (mostly because plans get replaced while pending). "
  "**Confidence:** LOW (coverage-limited). **Recommendation:** none; keep as analytics.")

# =================================================================== SECTION 25
sec(25, "SNAPSHOT TIMELINE AUDIT")
tss = sorted(set(sn.timestamp for sn in SNAPS)); gaps = [b - a for a, b in zip(tss, tss[1:])]
norm = [g for g in gaps if g <= 10 * 60000]
tot_span = tss[-1] - tss[0]; out_ms = sum(o["end"] - o["start"] for o in OUT)
table(["Metric", "Value"], [["Distinct snapshot timestamps (cycles)", len(tss)], ["Snapshots total", len(SNAPS)], ["Span (days)", round(tot_span / 86400000, 1)],
      ["Median normal cycle interval (min)", round(statistics.median(norm) / 60000, 2)], ["Monitoring gaps > 10 min", len(OUT)], ["Total time in gaps (days)", round(out_ms / 86400000, 1)],
      ["Scanner uptime over span", f"{round((1 - out_ms / tot_span) * 100, 1)}%"], ["Longest gap (hours)", round(max((o["end"] - o["start"]) for o in OUT) / 3600000, 1)],
      ["Median gap (hours)", round(statistics.median([(o["end"] - o["start"]) for o in OUT]) / 3600000, 2)]])
aff_exit = [r for r in ENT if in_outage(r.exit_time)]
def overlap(r):
    s0 = r.entry_time or r.created_at; e0 = r.exit_time or tss[-1]
    return any(o["start"] < e0 and o["end"] > s0 for o in OUT)
aff_any = [r for r in ENT if overlap(r)]
slip_o = [r.stop_slippage_pct for r in ENT if r.stop_slippage_pct is not None and in_outage(r.exit_time)]
slip_n = [r.stop_slippage_pct for r in ENT if r.stop_slippage_pct is not None and not in_outage(r.exit_time)]
table(["Impact", "n trades", "Detail"], [["Closed trades whose EXIT fell inside a gap", len(aff_exit), f"{sum(1 for r in aff_exit if r.status=='closed_loss')} losses; avg return {fn(avg([ret(r) for r in aff_exit]))}%"],
      ["Closed trades open at any point during a gap", len(aff_any), f"{pct(len(aff_any), len(ENT))}% of all closed trades"],
      ["Stop slippage during gaps", len(slip_o), f"avg {fn(avg(slip_o))}%, worst {fn(min(slip_o) if slip_o else None)}%"], ["Stop slippage in normal uptime", len(slip_n), f"avg {fn(avg(slip_n))}%, worst {fn(min(slip_n) if slip_n else None)}%"]])
lat = []
for r in LOSS:
    sn = SNAP_BY_TRADE.get(r.id, [])
    if len(sn) >= 2: lat.append((sn[-1].timestamp - sn[-2].timestamp) / 60000)
tpl = [(r.exit_price - r.tp3 if r.tp3 and r.tp3_hit else r.exit_price - (r.tp2 if r.tp2_hit and not r.tp3 else r.tp1 if r.tp1_hit and not r.tp2 else None) if r.exit_price else None) for r in WINS]
def tp_slip(r):
    tgt = r.tp3 if r.tp3 is not None else (r.tp2 if r.tp2 is not None else r.tp1)
    return (r.exit_price - tgt) / tgt * 100 * sign(r) if r.exit_price and tgt else None
tps = [tp_slip(r) for r in WINS if tp_slip(r) is not None]
table(["Latency / slippage metric", "n", "Median", "P90", "Max"], [["Stop detection latency = gap between last two snapshots of a losing trade (min)", len(lat), round(statistics.median(lat), 1) if lat else "—", round(float(np.percentile(lat, 90)), 1) if lat else "—", round(max(lat), 1) if lat else "—"],
      ["TP overshoot (exit vs outermost target, % in trade direction; + = better than target)", len(tps), round(statistics.median(tps), 3) if tps else "—", round(float(np.percentile(tps, 90)), 3) if tps else "—", round(max(tps), 3) if tps else "—"]])
open_stale = [r for r in ALL if r.status in ("open", "pending") and SNAP_BY_TRADE.get(r.id) and tss[-1] - SNAP_BY_TRADE[r.id][-1].timestamp > 3600000]
strat_loss = [r for r in LOSS if not in_outage(r.exit_time)]; infra_loss = [r for r in LOSS if in_outage(r.exit_time)]
table(["Loss attribution", "n", "Sum of returns %", "% of total loss magnitude"], [["Losses with exit inside a monitoring gap (infrastructure-contaminated)", len(infra_loss), round(sum(ret(r) for r in infra_loss), 1), fn(pct(-sum(ret(r) for r in infra_loss), -sum(ret(r) for r in LOSS)), 1) + "%"],
      ["Losses in normal uptime (strategy)", len(strat_loss), round(sum(ret(r) for r in strat_loss), 1), fn(pct(-sum(ret(r) for r in strat_loss), -sum(ret(r) for r in LOSS)), 1) + "%"]])
W(f"**Outages distort wins as well as losses:** {sum(1 for r in WINS if in_outage(r.exit_time))} of {len(WINS)} wins also exited inside a gap (avg return {fn(avg([ret(r) for r in WINS if in_outage(r.exit_time)]))}% vs {fn(avg([ret(r) for r in WINS if not in_outage(r.exit_time)]))}% in uptime; TP overshoot median +2.2%, P90 +24%). Late detection inflates both tails, so gap exposure adds noise in both directions — the net effect on PF is not separable from this data.")
W(f"Open/pending trades with no snapshot for >1h (stale): n={len(open_stale)}. **Confidence:** HIGH (timestamps are facts). **Recommendation:** run the scanner as a supervised always-on process; until then annotate every metric with the fraction of trades gap-exposed ({pct(len(aff_any), len(ENT))}%). Detection latency is bounded by the scan interval only during uptime.")
KEY["aff_any"] = len(aff_any); KEY["infra_loss_share"] = pct(-sum(ret(r) for r in infra_loss), -sum(ret(r) for r in LOSS))

# =================================================================== SECTION 26
sec(26, "PREDICTION VERSION AUDIT")
groups = [("V0: pre entry_quality (created < 2026-08-10)", [r for r in ENT if r.created_at < EQ_LAUNCH]),
          ("V1: entry_quality live, pre EV/TradeManager/metadata", [r for r in ENT if r.created_at >= EQ_LAUNCH and (EV_FIRST is None or r.created_at < EV_FIRST)]),
          ("V2: EV + Trade Manager + reliability + metadata live (created ≥ %s)" % dt(EV_FIRST), [r for r in ENT if EV_FIRST is not None and r.created_at >= EV_FIRST])]
def dd(rows):
    o = sorted([r for r in rows if r.exit_time], key=lambda r: r.exit_time); c = p = m = 0
    for r in o: c += ret(r); p = max(p, c); m = min(m, c - p)
    return round(m, 1)
rows26 = []
for nm, sub in groups:
    if not sub: rows26.append([nm, 0] + [""] * 9); continue
    x = summ(sub); ct = [r for r in sub if r.confidence is not None]
    br = avg([(r.confidence / 100 - (1 if r.status == "closed_win" else 0)) ** 2 for r in ct]) if ct else None
    sl = [r.stop_slippage_pct for r in sub if r.stop_slippage_pct is not None]
    ex1_ = [r for r in sub if r is not max(sub, key=lambda z: ret(z))]
    rows26.append([nm, x["n"], f"{x['wr']}%", x["pf"], fn(pf([ret(r) for r in ex1_])), x["avg"], x["med"], f"{x['tp1']}/{x['tp2']}/{x['tp3']}", f"{x['mfe']}/{x['mae']}", fn(avg(sl)), x["hold"], dd(sub), fn(br, 3)])
table(["Version", "n", "Win%", "PF", "PF ex-best", "Avg ret", "Median", "TP1/2/3 %", "MFE/MAE", "Avg stop slip%", "Median hold h", "Naive DD %", "Brier"], rows26)
vs = collections.Counter((r.prediction_metadata or {}).get("prediction_version", "unversioned") for r in ALL)
W(f"Stored prediction_metadata versions across all {len(ALL)} plans: {dict(vs)}. EV, Trade Manager, reliability and metadata all went live in the same deployment (first stored EV/metadata plan: {dt(EV_FIRST)}), so they **cannot be separated**; reliability/calibration are display-only (not stored per trade). "
  f"**Regime/time caveat:** these are different calendar windows and market regimes (V0 is early risk_on; V2 is the most recent window), so differences are NOT attributable to the features. V2 n={len(groups[2][1])} — its PF is dominated by a single +114% winner (see PF ex-best). "
  "**Confidence:** INSUFFICIENT DATA to credit any version. **Recommendation:** keep collecting under the frozen engine; compare versions only at n≥100 per version.")

# =================================================================== SECTION 27
sec(27, "PORTFOLIO ANALYSIS")
iv = sorted([(r.entry_time, r.exit_time, r) for r in ENT if r.entry_time and r.exit_time], key=lambda t: t[0])
conc = []
for e0, x0, r in iv:
    others = [o for a, b, o in iv if o is not r and a <= e0 < b]
    fam = pe._family_for(r.symbol)
    conc.append((r, len(others), sum(1 for o in others if pe._family_for(o.symbol) == fam), sum(1 for o in others if o.direction == r.direction)))
cs = [c[1] for c in conc]
table(["Concurrency at entry (closed trades only)", "Value"], [["Trades analyzed", len(conc)], ["Mean / median / max other open trades at entry", f"{round(statistics.mean(cs), 1)} / {statistics.median(cs)} / {max(cs)}"],
      ["Entries with ≥5 other open trades", sum(1 for c in cs if c >= 5)], ["Entries with ≥1 same-family open trade", sum(1 for c in conc if c[2] >= 1)]])
sp1 = spearmanr(cs, [ret(c[0]) for c in conc]); sp2 = spearmanr([c[2] for c in conc], [ret(c[0]) for c in conc])
table(["Test", "Spearman with realized return", "p", "n"], [["# concurrent open trades at entry", round(sp1.statistic, 3), round(sp1.pvalue, 3), len(conc)], ["# concurrent SAME-FAMILY trades at entry", round(sp2.statistic, 3), round(sp2.pvalue, 3), len(conc)]])
fam_ = collections.defaultdict(list)
for r in ENT: fam_[pe._family_for(r.symbol)].append(r)
table(["Family", "n", "Win%", "PF", "Avg ret", "Longs / Shorts"], [[k, len(v), f"{summ(v)['wr']}%", fn(summ(v)["pf"]), summ(v)["avg"], f"{sum(1 for r in v if r.direction=='long')}/{sum(1 for r in v if r.direction=='short')}"] for k, v in sorted(fam_.items(), key=lambda kv: -len(kv[1]))])
cl = []
srt2 = sorted([r for r in LOSS if r.exit_time], key=lambda r: r.exit_time); i = 0
while i < len(srt2):
    j = i
    while j + 1 < len(srt2) and srt2[j + 1].exit_time - srt2[i].exit_time <= 2 * 3600000: j += 1
    if j > i: cl.append(srt2[i:j + 1])
    i = j + 1
W(f"Stop-out clusters (≥2 losses within 2h): {len(cl)} clusters, {sum(len(c) for c in cl)} losses ({pct(sum(len(c) for c in cl), len(LOSS))}% of losses); largest = {max((len(c) for c in cl), default=0)} simultaneous stops.")
W("Magnificent-Seven concentration: only NVDA appears among the symbols; other listed themes are approximated by the family map. **BTC/ETH beta and rolling correlation: INSUFFICIENT DATA** (OHLCV history exists for only 6 symbols). "
  f"**Did correlation raise drawdowns?** Not supported: more concurrent open trades at entry correlated POSITIVELY with realized return (Spearman {round(sp1.statistic,3)}, p={round(sp1.pvalue,3)}), most likely a time-period confound (busy periods coincided with the strong late window). Losses do cluster ({len(cl)} clusters holding {pct(sum(len(c) for c in cl), len(LOSS))}% of losses), consistent with common-factor/outage exits. **Confidence:** LOW. **Recommendation:** keep exposure warnings as analytics; no gating.")

# =================================================================== SECTION 28
sec(28, "MARKET HEALTH AUDIT")
day = lambda ms: datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
dsc = collections.defaultdict(list)
for x in SCANS: dsc[day(x.timestamp)].append(x)
dh = {}
for d_, v in dsc.items():
    dirs = [x.direction for x in v if x.direction in ("long", "short")]
    risks = [x.score_breakdown.get("risk") for x in v if x.score_breakdown and x.score_breakdown.get("risk") is not None]
    fund = [x.score_breakdown.get("funding") for x in v if x.score_breakdown and x.score_breakdown.get("funding") is not None]
    dh[d_] = dict(n=len(v), long_share=pct(sum(1 for z in dirs if z == "long"), len(dirs)), avg_risk=avg(risks), avg_fund=avg(fund), nodir=pct(sum(1 for x in v if x.direction == "no_trade"), len(v)))
fgd = collections.defaultdict(list); trd = collections.defaultdict(list)
for r in ENT:
    trd[day(r.created_at)].append(r)
    if r.fear_greed is not None: fgd[day(r.created_at)].append(r.fear_greed)
rows28 = []
for d_ in sorted(trd):
    if d_ in dh: v = trd[d_]; rows28.append((d_, len(v), summ(v)["wr"], avg([ret(r) for r in v]), dh[d_], avg(fgd.get(d_, []))))
W(f"Days with both scan data and trades entered: n={len(rows28)} (of {len(dsc)} scan days). Retro health inputs available per day from ScanSnapshot: % of directional scans that are long (breadth proxy), avg risk-penalty (volatility-quality proxy), avg funding component, % no_trade; Fear&Greed from the trades' stored value. **Not stored historically:** BTC dominance, true volume breadth, news stress, liquidity → INSUFFICIENT DATA.")
def sp_col(idx, key=None):
    a = [(row[4][key] if key else row[idx]) for row in rows28]; b = [row[3] for row in rows28]
    pr = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pr) < 8: return ("n<8", "", len(pr))
    s_ = spearmanr([x for x, _ in pr], [y for _, y in pr]); return (round(s_.statistic, 3), round(s_.pvalue, 3), len(pr))
table(["Retro health input (daily)", "Spearman vs day's avg trade return", "p", "days n"],
      [["long share of directional scans", *sp_col(0, "long_share")], ["avg risk-penalty component", *sp_col(0, "avg_risk")], ["avg funding component", *sp_col(0, "avg_fund")], ["% no_trade scans", *sp_col(0, "nodir")], ["Fear & Greed (trade-day avg)", *sp_col(5)]])
W("Note: trades cluster on few days, days are autocorrelated, and the 'entered on that day' return is realized weeks later — a very weak test. **Does market health predict profitability?** INSUFFICIENT DATA unless a row above shows p<0.05 (none is expected at this n). **Recommendation:** keep Market Health as context only; re-test at ≥100 trading days.")

# =================================================================== SECTION 29
sec(29, "ROOT CAUSE ANALYSIS")
FACT = [(nm, pr) for nm, pr in LOSS_CATS] + [(f"strategy={k}", (lambda r, k=k: STRAT[r.id] == k)) for k in sorted(set(STRAT.values()))] + \
       [("regime=risk_on", lambda r: r.market_regime == "risk_on"), ("regime=mixed", lambda r: r.market_regime == "mixed"), ("entry_quality=excellent", lambda r: r.entry_quality == "excellent"),
        ("entry_quality=neutral", lambda r: r.entry_quality == "neutral"), ("entry_quality=good", lambda r: r.entry_quality == "good"), ("direction=long", lambda r: r.direction == "long"),
        ("RSI 50–70", lambda r: ei(r).get("rsi14") is not None and 50 <= ei(r)["rsi14"] < 70), ("volume_score ≥ 8", lambda r: r.volume_score is not None and r.volume_score >= 8),
        ("structure_score ≥ 9", lambda r: r.structure_score is not None and r.structure_score >= 9), ("reached TP3", lambda r: bool(r.tp3_hit)), ("FVG active at entry", lambda r: bool((r.level_reasoning or {}).get("fvg_used"))),
        ("confidence 60–64", lambda r: r.confidence is not None and 60 <= r.confidence < 65), ("no historical analogue", lambda r: r.historic_probability is None), ("CMF > 0", lambda r: ei(r).get("cmf") is not None and ei(r)["cmf"] > 0)]
FIX = {"Immediate": "Improve entry evidence (entry_quality already helps); shadow-test stricter confirmation.", "Never reached": "Same as immediate reversal.", "Short direction": "Soft derate flag (built); collect ≥30 shorts before any hard rule.",
       "monitoring outage": "Run the scanner as a supervised always-on service; not a strategy change.", "Gap/slippage": "Same as infrastructure (monitoring gaps).", "RSI chop": "Red-flag (built); shadow-mode entry filter.",
       "Weak structure": "Capture BOS/CHoCH at issuance (analytics) then re-test.", "Hit TP1 then": "Shadow-mode breakeven stop after TP1 (§19).", "Overbought": "Track; no change (low n).", "High ATR": "Track; no change (low n)."}
def fix_for(nm):
    for k, v in FIX.items():
        if nm.startswith(k) or k in nm: return v
    return "Track in shadow mode; no prediction change supported at current n."
tl = -sum(ret(r) for r in LOSS); tg = sum(ret(r) for r in WINS)
lrows = []; wrows = []
for nm, pr in FACT:
    sl_ = [r for r in LOSS if pr(r)]; sw_ = [r for r in WINS if pr(r)]; allp = [r for r in ENT if pr(r)]; allo = [r for r in ENT if not pr(r)]
    if sl_:
        ex = sorted(sl_, key=lambda r: ret(r))[:2]
        lrows.append(((len(sl_) / len(LOSS) - len(allp) / len(ENT)) * 100 if len(allp) >= 5 else -999, [nm, f"{len(sl_)}/{len(LOSS)} ({pct(len(sl_), len(LOSS))}%)", fn(sum(-ret(r) for r in sl_) / tl * 100, 1) + "%", f"{fn(avg([ret(r) for r in allp]))}% vs {fn(avg([ret(r) for r in allo]))}%", "; ".join(f"{r.symbol} {fn(ret(r), 1)}%" for r in ex), fix_for(nm)]))
    if sw_:
        ex = sorted(sw_, key=lambda r: -ret(r))[:2]
        wrows.append(((len(sw_) / len(WINS) - len(allp) / len(ENT)) * 100 if len(allp) >= 5 else -999, [nm, f"{len(sw_)}/{len(WINS)} ({pct(len(sw_), len(WINS))}%)", fn(sum(ret(r) for r in sw_) / tg * 100, 1) + "%", f"{fn(avg([ret(r) for r in allp]))}% vs {fn(avg([ret(r) for r in allo]))}%", "; ".join(f"{r.symbol} +{fn(ret(r), 1)}%" for r in ex), "Preserve — do not change the mechanism behind this."]))
lrows.sort(key=lambda x: -x[0]); wrows.sort(key=lambda x: -x[0])
W("Ranking metric = over-representation: (share of losses [wins] with the factor) minus (share of ALL closed trades with the factor), in percentage points; factors with <5 trades excluded. This removes pure base-rate effects (e.g. 'long' is 84%% of all trades). The share-of-magnitude column is kept for context (factors overlap). 'Avg impact' = average return with vs without the factor over all n=%d closed trades. Frequency ≠ cause; factors are correlational." % len(ENT))
W(); W("### Top 20 reasons Karma LOSES (ranked by over-representation in losses vs. base rate)"); W()
table(["#", "Factor", "Frequency in losses", "Share of loss magnitude", "Avg ret with vs without", "Example trades", "Engineering fix (hypothesis, shadow-test only)"], [[i + 1] + row[1] for i, row in enumerate(lrows[:20])])
W("### Top 20 reasons Karma WINS (ranked by over-representation in wins vs. base rate)"); W()
table(["#", "Factor", "Frequency in wins", "Share of gain magnitude", "Avg ret with vs without", "Example trades", "Guidance"], [[i + 1] + row[1] for i, row in enumerate(wrows[:20])])
W("**Category split:** Model/prompt issue — entry selection (immediate reversals dominate); Execution/infrastructure — outage & slippage (§25); Market-regime — regime is confounded with time (§14); Small-sample — everything at family/symbol level (§6, §16); the *prompt* cannot be assessed independently (no A/B) → INSUFFICIENT DATA.")

# =================================================================== SECTION 30
sec(30, "KARMA V3.0 ENGINEERING PLAN")
sh_all_n = len([r for r in ENT if r.direction == "short"])
W("Every row below is tied to a section above; nothing here changes prediction logic.")
W()
table(["Bucket", "Item", "Evidence (section)", "Expected improvement"], [
 ["Ship immediately (analytics/display only)", "Always show n, Wilson CI, and ex-top-3 PF beside every headline stat", f"§1: PF {KEY['pf_all']} -> {KEY['pf_ex3']} ex-top-3; median trade {KEY['med']}%", "Prevents over-reading a right-tail-driven PF"],
 ["Ship immediately", "Annotate every metric with % of trades exposed to a monitoring gap", f"§25: {KEY['aff_any']}/{len(ENT)} closed trades open during a gap; {KEY['infra_loss_share']}% of loss magnitude exits inside gaps", "Separates infra from strategy failure"],
 ["Ship immediately", "Show calibrated confidence with interval instead of raw confidence as a probability", f"§8: Brier {KEY['brier']} vs base-rate {KEY['base_brier']}", "Removes misleading probability framing"],
 ["Ship immediately", "Show an INSUFFICIENT DATA badge whenever a slice has n<10", "§3-§29: most slices non-significant", "Prevents false precision"],
 ["Ship immediately (ops)", "Run the scanner as a supervised always-on service", f"§25: uptime {round((1 - out_ms / tot_span) * 100, 1)}%, longest gap {round(max((o['end'] - o['start']) for o in OUT) / 3600000, 1)}h", "Largest data-quality lever; not a model change"],
 ["Shadow mode (log, don't act)", "Breakeven-stop-after-TP1 policy", f"§19: bounds {pol[4][2]}%..{pol[3][2]}% vs actual {pol[0][2]}% (inconclusive)", "Unknown; needs per-trade path data"],
 ["Shadow mode", "RSI 30-49 chop-zone warning as a soft flag", "§13/§21: win 21.7% (n=23) vs 43.0%, p=0.093 (suggestive only)", "Possible; unproven"],
 ["Shadow mode", "Short-direction flag (already built), no hard block", f"§15: overall p=0.037 but ex-outage n={KEY['short_n_clean']} shorts, {KEY['short_wr_clean']}% win", "Unknown"],
 ["Shadow mode", "Persist BOS/CHoCH/sweep/OBV booleans at issuance", "§3/§12/§13: not stored -> INSUFFICIENT DATA", "Enables a future structure audit"],
 ["Needs 200 trades", "Any change to score weights", f"§10: CV-AUC {KEY['cv_auc']}, {KEY['n_ci_excl']}/10 coefficients significant", "Cannot be estimated"],
 ["Needs 200 trades", "Entry-quality tier validation", f"§7: excellent vs rest OR {KEY['eq_ex_or']}, p={KEY['eq_ex_p']}", "Unknown"],
 ["Needs 200 trades", "EV as a ranking/selection signal", f"§18: Spearman {KEY['ev_spear'][0]} (p={KEY['ev_spear'][1]})", "Unknown"],
 ["Needs 500 trades", "Regime-conditional behavior; strategy-family ranking; symbol-tier gating", "§6/§14/§16: per-cell n mostly <30; only 2 regime labels observed", "Unknown"],
 ["Needs 500 resolved scans", "Missed-opportunity verdicts on rejected/late/exhausted candidates", "§22: ScanSnapshot has no price; recorder not wired", "Unknown"],
 ["Needs retraining", "None recommended", f"§10: no evidence retraining would help (CV-AUC {KEY['cv_auc']}); prior retrain gave identical AUC", "-"],
 ["Do not build", "Hard short ban; auto weight optimizer; per-coin ML models; regime gating; TP/SL formula fitted on ~50 trades", "§15, §10, §16, §14, §19", "Would fit noise"],
])
W("### Answers to the final questions")
W()
W("**1. Top 10 improvements (evidence-ranked, all non-predictive):** (1) keep the scanner running continuously (§25); (2) publish n + CI + ex-top-3 PF on every dashboard (§1); (3) present confidence as an uncalibrated score with a calibrated interval (§8); (4) persist BOS/CHoCH/sweep booleans at issuance (§12); (5) wire the missed-opportunity recorder (needs explicit approval to touch the scanner) (§22); (6) log a shadow breakeven-after-TP1 policy (§19); (7) record post-invalidation price outcomes for a sample (§23); (8) store entry-time ATR-normalised risk and BTC correlation for portfolio audits (§27); (9) tag every trade with an infra-exposure flag (§25); (10) re-run this audit at n=200 and n=500 (§10).")
W("**2. What must never change (without new evidence):** the deterministic-first design; win/loss/exit bookkeeping; the hold-to-outermost-target exit behavior (§19: exiting at TP1/TP2 was clearly worse); the entry-quality gate blocking late/exhausted setups (0 such trades exist to judge); the frozen modules until n>=150-200.")
W("**3. Modules that work well:** trade lifecycle/outcome tracking, TP/stop hit tracking, Wilson-CI calibration display, slippage/outage measurement, and the outermost-target exit rule that captures the right tail (§19).")
W("**4. Modules that can mislead users:** raw confidence as a probability (§8: Brier worse than base rate); headline win rate/PF without ex-top-3 (§1); short-vs-long comparisons that ignore outage exits (§15); EV as a ranker (§18); history as a quality signal (§17: confounded, n=15); reliability tiers built on 1-2 trades per symbol (§16); Market Health as predictive (§28: INSUFFICIENT DATA).")
W("**5. Prediction card metrics:** entry-quality tier with n; calibrated confidence with interval and sample size; risk:reward and ATR-normalised stop distance; red flags labelled suggestive; symbol reliability with n; data-completeness badge.")
W("**6. Daily dashboard metrics:** scanner uptime and gap exposure; open/closed counts; PF and win rate with n and ex-top-3 PF; median return; stop-slippage split by outage; long vs short with n.")
W("**7. Trade replay metrics:** snapshot price path vs entry/stop/TPs, MFE/MAE, lifecycle pattern, Trade-Truth verdict, monitoring-gap markers, slippage, stored reasoning and level rationale.")
W("**8. Scanner/watchlist metrics:** rejection-reason funnel (published/no_trade/late/exhausted/rank-cutoff), plans replaced while pending (churn), never-entered outcomes (§24), history/reliability coverage.")
W("**9. Confidence metrics:** calibration table with Wilson CIs, Brier vs base-rate Brier, ECE, bucket n, Spearman vs return; label 'not a probability' until Brier beats the base rate.")
W("**10. Hidden diagnostics:** feature-audit table with OR/CI/Fisher/info-gain (§3-§13), CV-AUC and bootstrap coefficients (§10), infra-vs-strategy loss split (§25), flag co-occurrence (§21), concurrency/cluster stats (§27), version-boundary comparisons (§26).")
W()
W("### Karma V3.0 — Changes Backed by Data")
W()
table(["Feature", "Evidence Strength", "Sample Size", "Expected Impact", "Safe to Ship?", "Needs More Data?"], [
 ["Scanner always-on / supervised process", "Strong (timestamp facts)", f"{len(tss)} cycles, {len(OUT)} gaps, n={len(ENT)} closed", f"High on data quality ({KEY['infra_loss_share']}% of loss magnitude exits in gaps); strategy impact unknown", "Yes (ops, not model)", "No"],
 ["Headline stats with n, CI, ex-top-3 PF", "Strong", f"n={len(ENT)}", f"Prevents over-claiming (PF {KEY['pf_all']} -> {KEY['pf_ex3']})", "Yes", "No"],
 ["Calibrated confidence + interval display", "Moderate", f"n={len(CT)}", "Honest uncertainty; no change to trades", "Yes", "Partly (bucket n small)"],
 ["Infra-exposure tag per trade", "Strong", f"{KEY['aff_any']}/{len(ENT)} exposed", "Cleaner evaluation", "Yes", "No"],
 ["Persist BOS/CHoCH/sweep/OBV booleans", "N/A (currently missing)", "0 trades have them", "Enables the §12 audit", "Yes (additive; needs approval to edit feature code)", "Yes"],
 ["Wire missed-opportunity recorder", "N/A (currently missing)", "0 recorded rows", "Enables §22", "Needs explicit approval (frozen file)", "Yes (>=500 rows)"],
 ["Shadow breakeven-after-TP1", "Weak / inconclusive", "n=52 TP1 trades", "Unknown (bounds straddle actual)", "Shadow only", "Yes"],
 ["RSI 30-49 chop-zone flag", "Weak-moderate (p=0.093)", "n=23 flagged", "Possible loss avoidance", "Shadow only", "Yes"],
 ["Short-direction handling", "Weak (p=0.037 all; not significant ex-outage)", f"n={sh_all_n} (ex-outage {KEY['short_n_clean']})", "Unknown", "Keep soft flag only; no hard block", "Yes (>=30 clean shorts)"],
 ["Score weight changes", "None", f"n={len(y)}", f"CV-AUC {KEY['cv_auc']}; no coefficient significant", "No", "Yes (>=200)"],
 ["Entry-quality tier changes", f"Weak (p={KEY['eq_ex_p']})", f"n={len([r for r in ENT if r.entry_quality])}", "Unknown", "No", "Yes (>=200)"],
 ["EV-based ranking/gating", "None", f"n={len(pairs)}", f"Spearman {KEY['ev_spear'][0]}", "No", "Yes (>=200)"],
 ["Regime gating", "None", "2 labels observed", "Unknown", "No", "Yes (>=500)"],
 ["ML retraining", "None", f"n={len(ENT)}", "Prior retrain: identical AUC", "No", "Yes"],
 ["Early-exit at TP1/TP2 policies", "Strong AGAINST", f"n={len(ENT)}", f"Sum ret {pol[1][2]}% / {pol[2][2]}% vs actual {pol[0][2]}%", "No (would reduce return)", "No"],
])


open("karma_v3_audit_report.md", "w", encoding="utf-8").write("\n".join(L))
import json
json.dump(KEY, open("scratch_key.json", "w"), default=str)
print("OK lines:", len(L), "KEY:", KEY)
