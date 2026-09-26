"""Direction badge - Karma V3.3-E (informational only; never gates or scores a trade).

For SHORT plans, attach a plain-language badge with the historical facts behind it.
Wording is deliberately about the SAMPLE ("Lower historical reliability (small
sample)"), not a cause: in the 118-trade audit shorts won 15% (3/20) vs 44% for
longs, but 11 of the 20 shorts exited inside scanner downtime and all lost, and the
9 uptime exits (33% win) are statistically indistinguishable from longs (p=1.0).
Downtime is therefore one HYPOTHESIS, and the sample is too small to say more.

The badge disappears on its own when the evidence no longer supports it: it is shown
only while shorts' observed win rate is below longs' AND shorts have fewer than
MIN_SHORTS_TO_DROP resolved trades.
"""

import math
import time

from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import TradeOutcome

_TRADED = ("closed_win", "closed_loss")
MIN_SHORTS_TO_DROP = 30
BADGE_LABEL = "Lower historical reliability (small sample)"
_cache: dict = {"ts": 0.0, "stats": None}
_TTL = 60


def _wilson(k, n, z=1.96):
    if not n:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(max(0, (c - h) / d) * 100), round(min(1, (c + h) / d) * 100)]


def compute_stats(rows: list, outages: list[dict]) -> dict:
    """Pure function: rows are resolved TradeOutcome-like objects (direction/status/exit_time)."""

    def in_gap(r):
        return r.exit_time is not None and any(o["start"] <= r.exit_time <= o["end"] for o in outages)

    def block(rs):
        n = len(rs)
        w = sum(1 for r in rs if r.status == "closed_win")
        return {"n": n, "wins": w, "win_rate_pct": round(w / n * 100, 1) if n else None, "ci_95_pct": _wilson(w, n)}

    shorts = [r for r in rows if r.direction == "short"]
    longs = [r for r in rows if r.direction == "long"]
    return {
        "short": block(shorts),
        "long": block(longs),
        "short_exit_in_gap": block([r for r in shorts if in_gap(r)]),
        "short_exit_in_uptime": block([r for r in shorts if not in_gap(r)]),
        "long_exit_in_uptime": block([r for r in longs if not in_gap(r)]),
    }


def badge_from_stats(direction: str | None, stats: dict) -> dict | None:
    if direction != "short":
        return None
    s, l_ = stats["short"], stats["long"]
    if s["n"] == 0:
        return {"label": BADGE_LABEL, "informational_only": True, "evidence": "INSUFFICIENT DATA",
                "text": "No resolved short trades yet; there is no history to rely on."}
    still_supported = (
        s["win_rate_pct"] is not None and l_["win_rate_pct"] is not None
        and s["win_rate_pct"] < l_["win_rate_pct"] and s["n"] < MIN_SHORTS_TO_DROP
    )
    if not still_supported:
        return None
    up, gap = stats["short_exit_in_uptime"], stats["short_exit_in_gap"]
    return {
        "label": BADGE_LABEL,
        "informational_only": True,
        "evidence": "INSUFFICIENT DATA",
        "facts": stats,
        "text": (
            f"Shorts have won {s['wins']} of {s['n']} resolved trades ({s['win_rate_pct']}%) vs {l_['win_rate_pct']}% for longs. "
            f"Of those shorts, {gap['n']} exited while the scanner was down ({gap['wins']} wins) and {up['n']} exited during normal "
            f"monitoring ({up['win_rate_pct']}% win). The sample is too small to separate a real weakness from missed monitoring; "
            f"this badge is informational and does not change the trade."
        ),
    }


def _stats_cached() -> dict:
    now = time.time()
    if _cache["stats"] is not None and now - _cache["ts"] < _TTL:
        return _cache["stats"]
    from app.engine import performance_center as pc

    session = SessionLocal()
    try:
        rows = session.execute(select(TradeOutcome).where(TradeOutcome.status.in_(_TRADED))).scalars().all()
    finally:
        session.close()
    stats = compute_stats(rows, pc.scanner_health(10).get("outages", []))
    _cache.update(ts=now, stats=stats)
    return stats


def direction_badge(direction: str | None) -> dict | None:
    if direction != "short":
        return None  # avoid any DB work for longs
    return badge_from_stats(direction, _stats_cached())
