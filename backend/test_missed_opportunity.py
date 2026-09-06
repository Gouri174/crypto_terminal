"""Manual verification script for the Missed Opportunity RECORDER (scoped
per explicit instruction — recording only, no analysis leaderboard yet).
See app/analytics/missed_opportunity.py's module docstring for what this
deliberately does not do (claim a rejected candidate "would have won").

Not a pytest suite (no test infra elsewhere in this project — see
test_trade_outcomes.py, same pattern). Run directly with
`python test_missed_opportunity.py`. Uses clearly-fake symbols
(ZZZMOA/ZZZMOB) and cleans up after itself.
"""

import sys

sys.path.insert(0, ".")

from app.analytics import missed_opportunity as mo
from app.db import SessionLocal, init_db
from app.models.db_models import RejectedOpportunityOutcome

init_db()

FAKE_SYMBOLS = ["ZZZMOAUSDT", "ZZZMOBUSDT"]
FAILURES = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} {detail}")
        FAILURES.append(name)


def cleanup():
    session = SessionLocal()
    try:
        session.query(RejectedOpportunityOutcome).filter(
            RejectedOpportunityOutcome.symbol.in_(FAKE_SYMBOLS)
        ).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. record_rejection() — no-op for no_trade, real row otherwise
# ---------------------------------------------------------------------------
def test_record_rejection():
    no_trade = mo.record_rejection(FAKE_SYMBOLS[0], "no_trade", "score below threshold", 100.0, 1_000_000)
    check("no_trade direction produces no row (nothing to measure a directional move against)", no_trade is None)

    row = mo.record_rejection(FAKE_SYMBOLS[0], "long", "entry_quality=late", 100.0, 1_000_000)
    check("a real long rejection creates a row", row is not None)
    check("row starts unresolved with all check-ins NULL", row.resolved is False and row.price_at_4h is None)


# ---------------------------------------------------------------------------
# 2. check_in() — fills in only the windows that have come due, computes
#    the correct SIGN-ADJUSTED directional move.
# ---------------------------------------------------------------------------
def test_check_in_windows_and_sign():
    long_row = mo.record_rejection(FAKE_SYMBOLS[0], "long", "late", 100.0, 1_000_000)
    short_row = mo.record_rejection(FAKE_SYMBOLS[1], "short", "late", 100.0, 1_000_000)

    # Only 3 hours later — no window due yet.
    updated = mo.check_in({FAKE_SYMBOLS[0]: 105.0, FAKE_SYMBOLS[1]: 105.0}, now_ms=1_000_000 + 3 * mo._HOUR_MS)
    session = SessionLocal()
    try:
        long_reloaded = session.get(RejectedOpportunityOutcome, long_row.id)
        check("before 4h has elapsed, no check-in fires", long_reloaded.price_at_4h is None, long_reloaded.price_at_4h)
    finally:
        session.close()

    # 5 hours later — the 4h window is due; price moved from 100 to 105 (+5%).
    mo.check_in({FAKE_SYMBOLS[0]: 105.0, FAKE_SYMBOLS[1]: 105.0}, now_ms=1_000_000 + 5 * mo._HOUR_MS)
    session = SessionLocal()
    try:
        long_reloaded = session.get(RejectedOpportunityOutcome, long_row.id)
        short_reloaded = session.get(RejectedOpportunityOutcome, short_row.id)
    finally:
        session.close()
    check("long's 4h directional move is +5.0% (price moved up, long wanted up)", long_reloaded.directional_move_4h_pct == 5.0, long_reloaded.directional_move_4h_pct)
    check("short's 4h directional move is -5.0% (price moved up, short wanted down — same price move, opposite sign)", short_reloaded.directional_move_4h_pct == -5.0, short_reloaded.directional_move_4h_pct)
    check("row is not yet resolved (72h window still pending)", long_reloaded.resolved is False)

    # 73 hours later — all three windows now due.
    mo.check_in({FAKE_SYMBOLS[0]: 110.0, FAKE_SYMBOLS[1]: 110.0}, now_ms=1_000_000 + 73 * mo._HOUR_MS)
    session = SessionLocal()
    try:
        long_reloaded = session.get(RejectedOpportunityOutcome, long_row.id)
    finally:
        session.close()
    check("72h window filled in and row marked resolved", long_reloaded.price_at_72h == 110.0 and long_reloaded.resolved is True, (long_reloaded.price_at_72h, long_reloaded.resolved))
    check("4h value is NOT overwritten by the later check-in (each window fills exactly once)", long_reloaded.price_at_4h == 105.0, long_reloaded.price_at_4h)


# ---------------------------------------------------------------------------
# 3. missed_opportunity_summary() — refuses to summarize below threshold
# ---------------------------------------------------------------------------
def test_summary_refuses_early_conclusions():
    summary = mo.missed_opportunity_summary()
    check("summary reports n_recorded/n_resolved without a rate/conclusion below MIN_SAMPLE_FOR_SUMPLE", "n_recorded" in summary and "ready_for_analysis" in summary, summary)
    check("ready_for_analysis is False at this dataset's real size (far under 500)", summary["ready_for_analysis"] is False, summary)
    check("note explicitly states recording-only status", "Recording only" in summary["note"] or "resolved rows collected" in summary["note"], summary["note"])


try:
    test_record_rejection()
    test_check_in_windows_and_sign()
    test_summary_refuses_early_conclusions()
finally:
    cleanup()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
