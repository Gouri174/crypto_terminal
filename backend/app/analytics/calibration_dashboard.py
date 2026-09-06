"""Calibration Dashboard — Karma V3.2 Phase H.

Consolidates confidence calibration (calibration.py), Brier score/ECE
(performance_center.py:confidence_lab), TP continuation calibration
(performance_center.py:tp_continuation_analytics), and expected-value
calibration (expected_value.py's Wilson-CI'd frequency tables) into one
endpoint. Every number already exists elsewhere; this is assembly only.
"""


def calibration_dashboard() -> dict:
    from app.engine.calibration import calibration_table
    from app.engine.expected_value import historical_tp_probabilities
    from app.engine.performance_center import confidence_lab, tp_continuation_analytics

    return {
        "confidence_calibration_curve": calibration_table(),
        "confidence_brier_and_ece": confidence_lab(),
        "tp_continuation_calibration": tp_continuation_analytics(),
        "expected_value_calibration": historical_tp_probabilities(),
    }
