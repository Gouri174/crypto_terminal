"""Confidence Calibration — Karma V2.1 Phase 4.

Maps raw confidence.py output onto its OBSERVED historical win rate, using
the exact bucket scheme already established in the V2.1 forensic report
and performance_center.py:confidence_lab() (50-54, 55-59, 60-64, 65-69,
70-74, 75+). This is a post-hoc lookup table over resolved TradeOutcome
history — NOT a retrained model, and it does NOT change confidence.py's
underlying weighted-agreement formula (that file is untouched). Rule 7 of
the V2.1 report: "remap confidence, don't retrain it."

Every result carries its own sample size and a 95% Wilson CI — a bucket
with too few resolved trades reports the RAW confidence back unchanged,
with an explicit "insufficient_data" note, rather than a fabricated
calibrated number.
"""

import math

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

MIN_SAMPLE = 5
_TRADED_STATUSES = ("closed_win", "closed_loss")
_BUCKETS = [(50, 55), (55, 60), (60, 65), (65, 70), (70, 75), (75, 101)]
_LABELS = ["50-54", "55-59", "60-64", "65-69", "70-74", "75+"]


def _traded_rows() -> list[TradeOutcome]:
    session = SessionLocal()
    try:
        return (
            session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(_TRADED_STATUSES)))
            .scalars()
            .all()
        )
    finally:
        session.close()


def _wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if n == 0:
        return (None, None)
    phat = successes / n
    denom = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    half = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    return (round(max(0.0, (center - half) / denom) * 100, 1), round(min(1.0, (center + half) / denom) * 100, 1))


def _bucket_for(confidence: int) -> tuple[int, int, str] | None:
    for (lo, hi), label in zip(_BUCKETS, _LABELS):
        if lo <= confidence < hi:
            return (lo, hi, label)
    return None


def calibration_table(min_sample: int = MIN_SAMPLE) -> dict:
    """Every bucket's predicted (avg raw confidence) vs actual win rate,
    with a 95% Wilson CI — the same table karma_v2_1_model_improvement_
    report.md Section 3 reports by hand, computed live here so it updates
    as new trades resolve."""
    rows = [r for r in _traded_rows() if r.confidence is not None]
    buckets = []
    for (lo, hi), label in zip(_BUCKETS, _LABELS):
        b = [r for r in rows if lo <= r.confidence < hi]
        n = len(b)
        if n == 0:
            buckets.append({"bucket": label, "n": 0})
            continue
        wins = sum(1 for r in b if r.status == "closed_win")
        lo_ci, hi_ci = _wilson_ci(wins, n)
        buckets.append({
            "bucket": label, "n": n,
            "avg_raw_confidence": round(sum(r.confidence for r in b) / n, 1),
            "actual_win_rate_pct": round(wins / n * 100, 1),
            "ci_95": (lo_ci, hi_ci),
            "reliable": n >= min_sample,
        })
    return {"buckets": buckets, "min_sample": min_sample}


def calibrated_confidence(raw_confidence: int | None, min_sample: int = MIN_SAMPLE) -> dict:
    """Looks up which bucket raw_confidence falls in and returns that
    bucket's OBSERVED win rate as the calibrated value. Falls back to the
    raw value, unchanged, with an explicit note, when the bucket has fewer
    than min_sample resolved trades — never invents a calibrated number
    from a sample too small to support one."""
    if raw_confidence is None:
        return {"raw_confidence": None, "calibrated_confidence": None, "confidence_bucket": None, "sample_size": 0, "note": "No confidence to calibrate."}

    match = _bucket_for(raw_confidence)
    if match is None:
        return {
            "raw_confidence": raw_confidence, "calibrated_confidence": raw_confidence,
            "confidence_bucket": None, "sample_size": 0,
            "note": "Confidence outside the calibrated 50-100 range — returned unchanged.",
        }
    lo, hi, label = match
    rows = [r for r in _traded_rows() if r.confidence is not None and lo <= r.confidence < hi]
    n = len(rows)
    if n < min_sample:
        return {
            "raw_confidence": raw_confidence, "calibrated_confidence": raw_confidence,
            "confidence_bucket": label, "sample_size": n,
            "note": f"insufficient_data — bucket {label} has only {n} resolved trades (need >= {min_sample}); returning raw confidence unchanged.",
        }
    wins = sum(1 for r in rows if r.status == "closed_win")
    lo_ci, hi_ci = _wilson_ci(wins, n)
    return {
        "raw_confidence": raw_confidence,
        "calibrated_confidence": round(wins / n * 100, 1),
        "confidence_bucket": label,
        "sample_size": n,
        "ci_95": (lo_ci, hi_ci),
        "note": f"Calibrated from {n} resolved trades in the {label} confidence bucket (observed win rate, not the raw formula's output).",
    }


def confidence_display(raw_confidence: int | None, min_sample: int = MIN_SAMPLE) -> dict:
    """Karma V3.1 — the "71 raw / 58 calibrated ±10%, n=22" display format.
    Thin wrapper around calibrated_confidence(): derives a symmetric ±
    half-width from the same Wilson CI already computed there, rather
    than introducing a second uncertainty calculation."""
    result = calibrated_confidence(raw_confidence, min_sample=min_sample)
    ci = result.get("ci_95")
    half_width = None
    if ci and ci[0] is not None and ci[1] is not None and result.get("calibrated_confidence") is not None:
        half_width = round((ci[1] - ci[0]) / 2, 1)
    return {
        "raw_confidence": result["raw_confidence"],
        "calibrated_confidence": result["calibrated_confidence"],
        "uncertainty_pm_pct_points": half_width,
        "sample_size": result["sample_size"],
        "confidence_bucket": result["confidence_bucket"],
        "note": result["note"],
        # V3.3-A: what a UI should actually show (ranges, not per-point precision).
        # The keys above are the legacy per-5-point-bucket view, kept for
        # backward compatibility; they are non-monotone and over-precise.
        "display": range_display(raw_confidence),
    }


# ---------------------------------------------------------------------------
# Karma V3.3-A — honest RANGE display (display only; never feeds scoring).
#
# Evidence (karma_v3_plan.md Part 3, 118 resolved trades): observed win rate is
# NOT monotone in raw confidence (55-59: 32%, 60-64: 46%, 65-69: 38%,
# 70-74: 33%), and on a chronological hold-out every mapping that used the
# rank of confidence lost to a constant at the base rate. Showing a different
# precise percentage per point (63 -> 40.8%, 64 -> 41.2%) would therefore be
# false precision. So: pool-adjacent-violators over the 5-point buckets
# collapses the data into the fewest monotone RANGES it can support, and the
# display shows the pooled observed rate + interval + sample size for the
# range the raw confidence falls in — never a per-point number.
# ---------------------------------------------------------------------------

RANGE_MIN_BLOCK_N = 20
_RANGE_LOW_KEY = 45    # everything below 50 is pooled into the lowest key
_RANGE_HIGH_KEY = 70   # 70-74 and 75+ share one key (75+ has ~1 trade)
_range_cache: dict = {"ts": 0.0, "blocks": None}
_RANGE_CACHE_TTL_SECONDS = 60


def _range_key(confidence: float) -> int:
    return int(min(max(confidence // 5 * 5, _RANGE_LOW_KEY), _RANGE_HIGH_KEY))


def build_range_blocks(pairs: list[tuple[float, bool]]) -> list[dict]:
    """pairs = [(raw_confidence, won)]. Returns monotone non-decreasing
    blocks [{'lo_key','hi_key','wins','n'}] by pool-adjacent-violators
    over the 5-point buckets. Pure function (no DB) so it is testable."""
    grp: dict[int, list[int]] = {}
    for conf, won in pairs:
        k = _range_key(conf)
        w, n = grp.get(k, (0, 0))
        grp[k] = [w + (1 if won else 0), n + 1]
    keys = sorted(grp)
    blocks = [{"lo_key": k, "hi_key": k, "wins": grp[k][0], "n": grp[k][1]} for k in keys]
    i = 0
    while i < len(blocks) - 1:
        a, b = blocks[i], blocks[i + 1]
        if a["wins"] / a["n"] > b["wins"] / b["n"]:  # violates monotonicity -> pool
            blocks[i] = {"lo_key": a["lo_key"], "hi_key": b["hi_key"], "wins": a["wins"] + b["wins"], "n": a["n"] + b["n"]}
            del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    return blocks


def _block_label(block: dict, is_first: bool, is_last: bool, next_lo: int | None) -> str:
    if is_first and is_last:
        return "all confidence levels"
    if is_first:
        return f"below {next_lo}"
    if is_last:
        return f"{block['lo_key']}+"
    return f"{block['lo_key']}–{next_lo - 1}"


def get_range_blocks(force: bool = False) -> list[dict]:
    import time

    now = time.time()
    if not force and _range_cache["blocks"] is not None and now - _range_cache["ts"] < _RANGE_CACHE_TTL_SECONDS:
        return _range_cache["blocks"]
    rows = [r for r in _traded_rows() if r.confidence is not None]
    blocks = build_range_blocks([(r.confidence, r.status == "closed_win") for r in rows])
    _range_cache.update(ts=now, blocks=blocks)
    return blocks


def range_display(raw_confidence: int | None, blocks: list[dict] | None = None) -> dict:
    """The user-facing calibrated display: a RANGE label, the pooled observed
    win rate for that range (integer %, with a 95% Wilson interval) and the
    sample sizes behind it. If the range holds fewer than RANGE_MIN_BLOCK_N
    resolved trades, the overall observed win rate is shown instead and the
    evidence is labelled INSUFFICIENT DATA."""
    if raw_confidence is None:
        return {"raw_confidence": None, "range_label": None, "observed_probability_pct": None, "evidence": "INSUFFICIENT DATA", "text": "No confidence to display."}
    blocks = blocks if blocks is not None else get_range_blocks()
    total_n = sum(b["n"] for b in blocks)
    if total_n == 0:
        return {"raw_confidence": raw_confidence, "range_label": None, "observed_probability_pct": None, "n_total": 0, "evidence": "INSUFFICIENT DATA",
                "text": "No resolved trades yet - no observed probability available."}
    k = _range_key(raw_confidence)
    idx = next(i for i, b in enumerate(blocks) if b["lo_key"] <= k <= b["hi_key"]) if any(b["lo_key"] <= k <= b["hi_key"] for b in blocks) else (0 if k < blocks[0]["lo_key"] else len(blocks) - 1)
    b = blocks[idx]
    label = _block_label(b, idx == 0, idx == len(blocks) - 1, blocks[idx + 1]["lo_key"] if idx + 1 < len(blocks) else None)
    if b["n"] >= RANGE_MIN_BLOCK_N:
        wins, n, evidence = b["wins"], b["n"], "LIKELY" if b["n"] >= 30 else "POSSIBLE"
    else:
        wins, n, evidence = sum(x["wins"] for x in blocks), total_n, "INSUFFICIENT DATA"
        label = "all confidence levels (this range has too few trades)"
    lo, hi = _wilson_ci(wins, n)
    pct = round(wins / n * 100)
    return {
        "raw_confidence": raw_confidence,
        "range_label": label,
        "observed_probability_pct": pct,
        "interval_pct": [round(lo), round(hi)],
        "n_range": n,
        "n_total": total_n,
        "evidence": evidence,
        "text": f"Observed win rate ~{pct}% (95% interval {round(lo)}–{round(hi)}%) "
                f"{('across ' + label) if label.startswith('all ') else ('for confidence ' + label)}, "
                f"based on {n} of {total_n} resolved historical trades. Raw confidence is not a probability.",
        "tooltip": f"Based on {total_n} historical trades. Expected to become more precise as more trades resolve.",
    }
