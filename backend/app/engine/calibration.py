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
