"""Karma V3.3-E - short badge. Pure-function tests + read-only real-DB check."""
import sys
from types import SimpleNamespace as NS

from app.analytics import direction_badge as db

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"PASS  {name}")
    else:
        FAIL += 1; print(f"FAIL  {name}  {detail}")


def r(direction, won, exit_time=10):
    return NS(direction=direction, status="closed_win" if won else "closed_loss", exit_time=exit_time)


GAP = [{"start": 100, "end": 200}]
rows = [r("long", True)] * 6 + [r("long", False)] * 4 + [r("short", False, 150)] * 3 + [r("short", True, 10)] + [r("short", False, 10)]
st = db.compute_stats(rows, GAP)
check("counts by direction", st["short"]["n"] == 5 and st["long"]["n"] == 10 and st["short"]["wins"] == 1)
check("gap vs uptime split for shorts", st["short_exit_in_gap"]["n"] == 3 and st["short_exit_in_uptime"]["n"] == 2 and st["short_exit_in_uptime"]["wins"] == 1)
b = db.badge_from_stats("short", st)
check("short with lower win rate + small sample -> badge with the agreed wording", bool(b) and b["label"] == "Lower historical reliability (small sample)")
check("badge is informational and states so", b["informational_only"] is True and "does not change the trade" in b["text"])
check("badge text frames downtime as unresolved, not as the cause", "too small to separate" in b["text"])
check("no 'monitoring-sensitive' wording", "monitoring-sensitive" not in b["text"] and "monitoring-sensitive" not in b["label"])
check("longs never get a badge", db.badge_from_stats("long", st) is None and db.direction_badge("long") is None)
check("None direction -> no badge", db.direction_badge(None) is None)

good_shorts = [r("long", True)] * 4 + [r("long", False)] * 6 + [r("short", True)] * 4 + [r("short", False)] * 2
check("badge withdrawn if shorts outperform longs", db.badge_from_stats("short", db.compute_stats(good_shorts, [])) is None)
many = [r("long", True)] * 20 + [r("long", False)] * 20 + [r("short", True)] * 5 + [r("short", False)] * 30
check("badge withdrawn once >=30 shorts exist (sample no longer small)", db.badge_from_stats("short", db.compute_stats(many, [])) is None)
check("no shorts yet -> INSUFFICIENT DATA badge, no numbers invented", db.badge_from_stats("short", db.compute_stats([r("long", True)], []))["evidence"] == "INSUFFICIENT DATA")
check("empty rows do not divide by zero", db.compute_stats([], [])["short"]["win_rate_pct"] is None)

real = db.direction_badge("short")
check("real DB: short badge present with facts and n", real is not None and real["facts"]["short"]["n"] > 0, real)
check("real DB: long trades get None", db.direction_badge("long") is None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
