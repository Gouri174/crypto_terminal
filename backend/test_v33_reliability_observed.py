"""Karma V3.3-D — history labels + observed-outcome rates. Pure-function tests plus read-only real-DB shape checks."""
import sys
from types import SimpleNamespace as NS

from app.analytics import observed_outcomes as oo
from app.analytics import reliability as rel

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"PASS  {name}")
    else:
        FAIL += 1; print(f"FAIL  {name}  {detail}")


POOLED = 0.39
# --- history labels
check("n=0 -> Insufficient history", rel.history_label(0, 0, POOLED)["history_label"] == rel.LABEL_INSUFFICIENT)
check("2 wins from 2 trades is NOT 'Positive history' (min-sample rule)", rel.history_label(2, 2, POOLED)["history_label"] == rel.LABEL_INSUFFICIENT)
check("0 wins from 3 trades is NOT 'Negative history'", rel.history_label(0, 3, POOLED)["history_label"] == rel.LABEL_INSUFFICIENT)
check("9 wins from 10 -> Positive history", rel.history_label(9, 10, POOLED)["history_label"] == rel.LABEL_POSITIVE, rel.history_label(9, 10, POOLED))
check("0 wins from 10 -> Negative history", rel.history_label(0, 10, POOLED)["history_label"] == rel.LABEL_NEGATIVE, rel.history_label(0, 10, POOLED))
check("4 wins from 10 (~pooled) -> Insufficient history", rel.history_label(4, 10, POOLED)["history_label"] == rel.LABEL_INSUFFICIENT)
check("stronger label needs more evidence (5/5 positive? p_above>=0.9)", rel.history_label(5, 5, POOLED)["history_label"] in (rel.LABEL_POSITIVE, rel.LABEL_INSUFFICIENT))
check("label carries the not-predictive caveat", "not been shown to predict" in rel.history_label(9, 10, POOLED)["label_note"])
check("no predictive-sounding labels exist", not any(x in (rel.LABEL_POSITIVE + rel.LABEL_NEGATIVE + rel.LABEL_INSUFFICIENT) for x in ("Trusted", "Avoid", "Watch")))
p = [rel._prob_above(w, 10, POOLED) for w in range(0, 11)]
check("P(above pooled) is monotone increasing in wins", all(p[i] <= p[i + 1] for i in range(10)), p)
check("P(above pooled) bounded in [0,1]", all(0 <= x <= 1 for x in p))

# --- observed outcome rates
rows = ([NS(status="closed_win", tp1_hit=True, tp2_hit=True, tp3_hit=True, stop_hit=False)] * 2
        + [NS(status="closed_win", tp1_hit=True, tp2_hit=True, tp3_hit=False, stop_hit=False)] * 3
        + [NS(status="closed_loss", tp1_hit=True, tp2_hit=False, tp3_hit=False, stop_hit=True)] * 1
        + [NS(status="closed_loss", tp1_hit=False, tp2_hit=False, tp3_hit=False, stop_hit=True)] * 4)
o = oo.outcome_rates(rows)
check("n counted", o["n_entered_resolved"] == 10)
check("TP1 = 6/10", o["tp1"]["count"] == 6 and o["tp1"]["pct"] == 60.0)
check("TP2 = 5/10, TP3 = 2/10, stop = 5/10", o["tp2"]["count"] == 5 and o["tp3"]["count"] == 2 and o["stop"]["count"] == 5)
check("TP2 given TP1 = 5/6", o["tp2_given_tp1"]["count"] == 5 and o["tp2_given_tp1"]["n"] == 6)
check("TP3 given TP2 = 2/5", o["tp3_given_tp2"]["count"] == 2 and o["tp3_given_tp2"]["n"] == 5)
check("final loss given TP1 = 1/6", o["final_loss_given_tp1"]["count"] == 1)
check("intervals bracket point estimates", all(v["ci_95_pct"][0] <= v["pct"] <= v["ci_95_pct"][1] for v in (o["tp1"], o["tp2"], o["stop"])))
check("n=10 is at the minimum sample (OBSERVED), n=6 conditional is INSUFFICIENT", o["tp1"]["evidence"] == "OBSERVED" and o["tp2_given_tp1"]["evidence"] == "INSUFFICIENT DATA")
e = oo.outcome_rates([])
check("empty input does not divide by zero", e["tp1"]["pct"] is None and e["n_entered_resolved"] == 0)

# --- real DB (read-only) shape
real = oo.observed_outcomes()
check("real DB: observed_outcomes returns rates + note", "tp1" in real and "note" in real and real["n_entered_resolved"] > 0)
check("real DB: TP1 and stop are not complements of a fixed 68/32 (sanity)", real["tp1"]["pct"] is not None and abs(real["tp1"]["pct"] - 68) > 10, real["tp1"])
short = oo.observed_outcomes(direction="short")
check("direction filter narrows n", short["n_entered_resolved"] < real["n_entered_resolved"])
sr = rel.symbol_reliability()
check("real DB: every symbol entry has a label from the allowed set", all(e["history_label"] in (rel.LABEL_POSITIVE, rel.LABEL_NEGATIVE, rel.LABEL_INSUFFICIENT) for e in sr["symbols"]))
check("real DB: thin symbols (n<5) are never labelled Positive/Negative", all(e["history_label"] == rel.LABEL_INSUFFICIENT for e in sr["symbols"] if e["n"] < rel.MIN_TRADES_FOR_LABEL))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
