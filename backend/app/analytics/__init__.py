"""Karma V3.0 analytics — read-only intelligence layer.

Everything under app/analytics/ reads already-stored data (TradeOutcome,
PredictionSnapshot, ScanSnapshot) and computes statistics or suggestions.
Nothing here writes to scoring.py, confidence.py, decision.py,
entry_quality.py, ml_model.py, or any DB row — same contract as
app/engine/performance_center.py and app/engine/forensic_diagnostics.py,
which this package complements rather than duplicates.

No new DB columns are added by this package (see each module's own
docstring) — everything is computed live on request, consistent with how
every other diagnostics function in this codebase already works, and per
the explicit "no database migrations unless necessary" instruction this
package was built under.
"""
