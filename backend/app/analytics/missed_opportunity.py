"""Missed Opportunity — RECORDER ONLY (Karma V3.1).

Per explicit instruction: "build only the recorder... don't build
analytics until 500-1000 rejected scans accumulate." This module does
exactly three things — record a rejection, check in on it later, and (a
thin, honesty-gated) summary that will report "insufficient data" until
that threshold is actually reached. No forensic analysis, no leaderboard,
no conclusions drawn from this data yet.

What this deliberately does NOT do: claim a rejected candidate "would
have won." A rejected candidate never received Claude-generated entry/
stop/TP levels, so there is nothing to grade a literal win/loss against —
attempting to reconstruct hypothetical levels retroactively is exactly
the "invent a TP1 that never existed" problem this project ruled out
earlier this session for historical MarketSnapshot backfill, and the same
reasoning applies here. Instead this tracks DIRECTIONAL price movement
(using the already-deterministic `direction`, decision.py:decide_direction)
as an honest, weaker proxy.

NOT WIRED IN YET: record_rejection() needs to be called once per rejected
ScanSnapshot row at scan time — the natural call site is
background_scanner.py:_persist_scan(), which already computes
symbol/direction/rejection_reason/price every cycle. That file is under
this session's 30-day freeze, so this module is built and tested
standalone; wiring the actual call in is a separate, explicit decision
the user needs to make (a small addition to a frozen file), not made
here. check_in() has no such dependency — it can run independently
against any fresh symbol->price dict (e.g. the same one the scanner
already fetches, or a small independent poller), so it's usable today
even before the recording side is wired in.
"""

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import RejectedOpportunityOutcome

_HOUR_MS = 3_600_000
CHECKIN_WINDOWS = {"price_at_4h": 4 * _HOUR_MS, "price_at_24h": 24 * _HOUR_MS, "price_at_72h": 72 * _HOUR_MS}


def record_rejection(
    symbol: str, direction: str, rejection_reason: str, price: float, rejected_at: int,
    scan_snapshot_id: int | None = None,
) -> RejectedOpportunityOutcome | None:
    """No-op for direction="no_trade" — there's no predicted direction to
    measure a favorable/unfavorable move against."""
    if direction not in ("long", "short"):
        return None
    session = SessionLocal()
    try:
        row = RejectedOpportunityOutcome(
            scan_snapshot_id=scan_snapshot_id, symbol=symbol, direction=direction,
            rejection_reason=rejection_reason, rejected_at=rejected_at, price_at_rejection=price,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
    finally:
        session.close()


def check_in(prices: dict[str, float], now_ms: int) -> int:
    """Fills in whichever check-in window(s) have come due for pending
    rows, using a fresh symbol->price dict — same shape
    background_scanner.py already produces each cycle from already-
    fetched tickers, so this costs nothing extra to call if/when wired
    into that loop. Returns how many rows were updated this call."""
    session = SessionLocal()
    updated = 0
    try:
        pending = (
            session.execute(select(RejectedOpportunityOutcome).where(RejectedOpportunityOutcome.resolved.is_(False)))
            .scalars()
            .all()
        )
        for row in pending:
            price = prices.get(row.symbol)
            if price is None:
                continue
            sign = 1 if row.direction == "long" else -1
            changed = False
            for field, window_ms in CHECKIN_WINDOWS.items():
                if getattr(row, field) is not None:
                    continue
                if now_ms - row.rejected_at < window_ms:
                    continue
                setattr(row, field, price)
                pct_field = field.replace("price_at_", "directional_move_") + "_pct"
                setattr(row, pct_field, round((price - row.price_at_rejection) / row.price_at_rejection * 100 * sign, 3))
                changed = True
            if row.price_at_72h is not None:
                row.resolved = True
            if changed:
                updated += 1
        session.commit()
    finally:
        session.close()
    return updated


MIN_SAMPLE_FOR_SUMMARY = 500  # per explicit instruction — do not summarize below this


def missed_opportunity_summary() -> dict:
    """Deliberately refuses to report a rate below MIN_SAMPLE_FOR_SUMMARY
    — this function exists so the recorder's progress is visible (how
    many rows exist, how many are resolved), not so it can be misread as
    an early conclusion."""
    session = SessionLocal()
    try:
        all_rows = session.execute(select(RejectedOpportunityOutcome)).scalars().all()
    finally:
        session.close()

    resolved = [r for r in all_rows if r.resolved]
    return {
        "n_recorded": len(all_rows),
        "n_resolved": len(resolved),
        "min_sample_for_summary": MIN_SAMPLE_FOR_SUMMARY,
        "ready_for_analysis": len(resolved) >= MIN_SAMPLE_FOR_SUMMARY,
        "note": (
            f"Recording only — {len(resolved)}/{MIN_SAMPLE_FOR_SUMMARY} resolved rows collected. "
            "No rate or conclusion is reported below the minimum sample, per explicit instruction."
            if len(resolved) < MIN_SAMPLE_FOR_SUMMARY else
            "Sample size threshold reached — a real summary can now be built, but isn't computed by this function yet."
        ),
    }
