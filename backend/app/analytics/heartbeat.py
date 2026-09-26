"""Scanner heartbeat — Karma V3.3 (operations, read-only).

The single largest data-quality problem in the archive is monitoring
downtime: uptime was ~16% of the observed span, and most of the loss
magnitude in the closed-trade ledger exits inside a monitoring gap. This
module answers one operational question — "is the scanner alive right
now?" — from the one signal that is written every cycle regardless of
whether any trade is open: ScanSnapshot.timestamp.

Read-only. Nothing here touches scoring, decision, trade generation or
the scanner loop itself.
"""

import time

from sqlalchemy import func, select

from app.config import SCAN_INTERVAL_SECONDS
from app.db import SessionLocal
from app.models.db_models import ScanSnapshot

# A cycle can legitimately run longer than the sleep interval (LLM calls,
# network), so "late" starts at 2x the interval and "down" at 4x.
LATE_MULTIPLIER = 2
DOWN_MULTIPLIER = 4


def scanner_heartbeat(now_ms: int | None = None, interval_seconds: int | None = None) -> dict:
    """Returns the age of the newest ScanSnapshot and a status:
    ok (<2 intervals) / late (<4 intervals) / down (>=4 intervals) /
    never_scanned (empty table)."""
    interval = int(interval_seconds or SCAN_INTERVAL_SECONDS)
    now = int(now_ms if now_ms is not None else time.time() * 1000)

    session = SessionLocal()
    try:
        last_ts = session.execute(select(func.max(ScanSnapshot.timestamp))).scalar()
    finally:
        session.close()

    if last_ts is None:
        return {
            "status": "never_scanned", "last_scan_timestamp": None, "age_seconds": None,
            "expected_interval_seconds": interval,
            "note": "No ScanSnapshot rows exist — the scanner has never completed a cycle on this database.",
        }

    age = max(0, (now - int(last_ts)) / 1000)
    if age < LATE_MULTIPLIER * interval:
        status = "ok"
    elif age < DOWN_MULTIPLIER * interval:
        status = "late"
    else:
        status = "down"
    return {
        "status": status,
        "last_scan_timestamp": int(last_ts),
        "age_seconds": round(age, 1),
        "expected_interval_seconds": interval,
        "late_after_seconds": LATE_MULTIPLIER * interval,
        "down_after_seconds": DOWN_MULTIPLIER * interval,
        "note": (
            "Derived from the newest ScanSnapshot (written every cycle). While status is late/down, "
            "open trades are NOT being monitored: TP/stop touches are only detected when the scanner "
            "next runs, and stop exits can fill far beyond the stop level."
        ),
    }
