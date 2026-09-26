"""Karma V3.3-A — range-based calibration display. Pure-function tests (no DB writes)."""
import sys

from app.engine import calibration as cal

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"PASS  {name}")
    else:
        FAIL += 1; print(f"FAIL  {name}  {detail}")


def mk(spec):
    """spec = {raw_confidence: (wins, n)} -> [(conf, won)]"""
    out = []
    for c, (w, n) in spec.items():
        out += [(c, True)] * w + [(c, False)] * (n - w)
    return out


# 1. the real-data shape from the 118-trade audit collapses into few monotone ranges
audit = mk({46: (0, 3), 52: (4, 7), 57: (7, 22), 62: (18, 39), 67: (11, 29), 72: (4, 13)})
blocks = cal.build_range_blocks(audit)
rates = [b["wins"] / b["n"] for b in blocks]
check("blocks are monotone non-decreasing in observed rate", all(rates[i] <= rates[i + 1] + 1e-12 for i in range(len(rates) - 1)), rates)
check("non-monotone buckets are pooled (fewer blocks than buckets)", len(blocks) < 6, blocks)
check("total n and wins are conserved by pooling", sum(b["n"] for b in blocks) == 113 and sum(b["wins"] for b in blocks) == 44, blocks)
check("blocks are contiguous and ordered", all(blocks[i]["hi_key"] < blocks[i + 1]["lo_key"] for i in range(len(blocks) - 1)), blocks)

# 2. already-monotone data is left alone
mono = cal.build_range_blocks(mk({52: (2, 10), 57: (4, 10), 62: (6, 10), 67: (8, 10)}))
check("monotone data yields one block per bucket", len(mono) == 4, mono)

# 3. empty / single-class inputs
check("empty input -> no blocks", cal.build_range_blocks([]) == [])
d0 = cal.range_display(63, blocks=[])
check("no data -> INSUFFICIENT DATA, no fabricated probability", d0["evidence"] == "INSUFFICIENT DATA" and d0["observed_probability_pct"] is None, d0)
allwin = cal.build_range_blocks(mk({62: (30, 30)}))
d1 = cal.range_display(62, blocks=allwin)
check("all-win block reports 100% with a Wilson interval below 100 upper bound <=100", d1["observed_probability_pct"] == 100 and d1["interval_pct"][1] <= 100 and d1["interval_pct"][0] < 100, d1)

# 4. display semantics
b = cal.build_range_blocks(audit)
d63, d64, d80 = (cal.range_display(c, blocks=b) for c in (63, 64, 80))
check("63 and 64 get the SAME displayed probability (no per-point false precision)", d63["observed_probability_pct"] == d64["observed_probability_pct"] and d63["range_label"] == d64["range_label"])
check("display carries sample sizes and an interval", d63["n_range"] > 0 and d63["n_total"] == 113 and len(d63["interval_pct"]) == 2, d63)
check("interval brackets the point estimate", d63["interval_pct"][0] <= d63["observed_probability_pct"] <= d63["interval_pct"][1], d63)
check("text never presents raw confidence as a probability", "not a probability" in d63["text"])
check("very high confidence (80) is served by the top range, not extrapolated", d80["range_label"].endswith("+"), d80)
low = cal.range_display(40, blocks=b)
check("thin lowest range (n=3) falls back to overall rate with INSUFFICIENT DATA", low["evidence"] == "INSUFFICIENT DATA" and low["n_range"] == 113, low)
check("None confidence handled", cal.range_display(None, blocks=b)["observed_probability_pct"] is None)

# 5. displayed probability stays inside [0,100] and integer
check("probability is an integer percent in range", all(isinstance(cal.range_display(c, blocks=b)["observed_probability_pct"], int) and 0 <= cal.range_display(c, blocks=b)["observed_probability_pct"] <= 100 for c in range(30, 100)))

# 6. legacy keys retained (backward compat) + new 'display' present against the real DB (read-only)
legacy = cal.confidence_display(62)
check("confidence_display keeps legacy keys", all(k in legacy for k in ("raw_confidence", "calibrated_confidence", "sample_size", "note")), list(legacy))
check("confidence_display adds the range display", "display" in legacy and "text" in legacy["display"], list(legacy))

# 7. frozen modules untouched by this feature
src = open(cal.__file__, encoding="utf-8").read()
check("calibration.py does not import scoring/decision/confidence modules", not any(x in src for x in ("from app.engine.scoring", "from app.engine.decision", "from app.engine.confidence", "import scoring", "import decision")))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
