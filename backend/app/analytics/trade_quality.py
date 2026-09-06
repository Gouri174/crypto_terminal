"""Trade Quality Score — Karma V3.1.

A single 0-100 composite that synthesizes already-computed outputs
(entry_quality, expected_value, reliability, calibrated_confidence,
structure_score, red_flags) — it does NOT introduce a new judgment or
touch scoring.py's weights. Every sub-component is read straight off a
TradeOutcome row (or the live inputs a not-yet-opened plan would produce),
scaled to 0-100, then combined with the fixed formula below. No ML, no
training, purely arithmetic.

Formula (fixed, not tuned against outcome data — same "first pass,
inspectable, not a black box" status as decision.py:market_checklist()):
    trade_quality = 0.30*entry_quality_pts + 0.20*ev_pts + 0.15*reliability_pts
                  + 0.15*calibration_pts + 0.10*structure_pts + 0.10*risk_flag_pts
"""

_ENTRY_QUALITY_POINTS = {
    "excellent": 100.0, "good": 75.0, "neutral": 50.0, "late": 25.0, "exhausted": 0.0,
}
_GRADE_BANDS = [(85, "A+"), (70, "A"), (55, "B"), (40, "C"), (0, "D")]


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _ev_points(expected_r: float | None) -> float | None:
    """Maps expected_r onto 0-100 over a [-1R, +3R] range — chosen because
    that's roughly the span this project's own EV audits have actually
    observed (karma_v2_1_model_improvement_report.md Section 4), not an
    arbitrary window."""
    if expected_r is None:
        return None
    return round(_clamp((expected_r - (-1.0)) / (3.0 - (-1.0)) * 100), 1)


def _structure_points(structure_score: float | None) -> float | None:
    if structure_score is None:
        return None
    return round(_clamp(structure_score / 15.0 * 100), 1)


def _risk_flag_points(red_flag_score: int | None, red_flag_max: int = 3) -> float | None:
    if red_flag_score is None:
        return None
    return round(_clamp((red_flag_max - red_flag_score) / red_flag_max * 100), 1)


def _grade_for(score: float) -> str:
    for threshold, grade in _GRADE_BANDS:
        if score >= threshold:
            return grade
    return "D"


def compute_trade_quality(
    entry_quality: str | None,
    expected_r: float | None,
    reliability_score: float | None,
    calibrated_confidence: float | None,
    structure_score: float | None,
    red_flag_score: int | None,
) -> dict:
    """Every argument is optional — a missing input contributes its
    weight's worth of a neutral 50 rather than crashing or silently
    dropping that term (which would let one strong sub-score dominate
    just because everything else was unavailable)."""
    components = {
        "entry_quality_pts": _ENTRY_QUALITY_POINTS.get(entry_quality, 50.0),
        "ev_pts": _ev_points(expected_r) if expected_r is not None else 50.0,
        "reliability_pts": reliability_score if reliability_score is not None else 50.0,
        "calibration_pts": calibrated_confidence if calibrated_confidence is not None else 50.0,
        "structure_pts": _structure_points(structure_score) if structure_score is not None else 50.0,
        "risk_flag_pts": _risk_flag_points(red_flag_score) if red_flag_score is not None else 50.0,
    }
    weights = {
        "entry_quality_pts": 0.30, "ev_pts": 0.20, "reliability_pts": 0.15,
        "calibration_pts": 0.15, "structure_pts": 0.10, "risk_flag_pts": 0.10,
    }
    total = round(sum(components[k] * weights[k] for k in weights), 1)
    return {
        "trade_quality": total,
        "grade": _grade_for(total),
        "components": components,
        "weights": weights,
        "inputs_used": {
            "entry_quality": entry_quality, "expected_r": expected_r,
            "reliability_score": reliability_score, "calibrated_confidence": calibrated_confidence,
            "structure_score": structure_score, "red_flag_score": red_flag_score,
        },
    }


def trade_quality_for_row(row) -> dict:
    """Convenience wrapper — pulls every input straight off an already-
    persisted TradeOutcome row (expected_value/red_flags/
    calibrated_confidence are all populated at issuance since V2.1)."""
    ev = (row.expected_value or {}).get("expected_r")
    cal = (row.calibrated_confidence or {}).get("calibrated_confidence")
    rf = (row.red_flags or {}).get("red_flag_score")

    from app.analytics.reliability import symbol_reliability  # lazy: avoid import-order coupling

    reliability = symbol_reliability(symbol=row.symbol).get("reliability_score")

    return compute_trade_quality(
        entry_quality=row.entry_quality, expected_r=ev, reliability_score=reliability,
        calibrated_confidence=cal, structure_score=row.structure_score, red_flag_score=rf,
    )
