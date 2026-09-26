"""Karma V3.3 G — heartbeat + watchdog tests. Uses an isolated in-memory DB (never touches the real one)."""
import importlib.util
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.analytics import heartbeat
from app.models.db_models import Base, ScanSnapshot

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"PASS  {name}")
    else:
        FAIL += 1; print(f"FAIL  {name}  {detail}")


engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
heartbeat.SessionLocal = Session  # isolate from the real database

NOW = 1_800_000_000_000
INT = 300

r = heartbeat.scanner_heartbeat(now_ms=NOW, interval_seconds=INT)
check("empty table -> never_scanned", r["status"] == "never_scanned" and r["age_seconds"] is None, r)

s = Session()
s.add(ScanSnapshot(timestamp=NOW - 100_000, symbol="AAAUSDT", rank=1, score_total=50.0, score_breakdown={}, direction="no_trade", in_top_candidates=False, explained_this_cycle=False, had_active_plan=False))
s.commit(); s.close()
r = heartbeat.scanner_heartbeat(now_ms=NOW, interval_seconds=INT)
check("100s old with 300s interval -> ok", r["status"] == "ok" and abs(r["age_seconds"] - 100.0) < 0.01, r)

for age_s, want in [(599, "ok"), (601, "late"), (1199, "late"), (1201, "down"), (10 ** 6, "down")]:
    r = heartbeat.scanner_heartbeat(now_ms=NOW - 100_000 + age_s * 1000, interval_seconds=INT)
    check(f"age {age_s}s -> {want}", r["status"] == want, r)

r = heartbeat.scanner_heartbeat(now_ms=NOW - 500_000, interval_seconds=INT)  # clock skew: newest scan 'in the future'
check("future timestamp clamps age to 0 and stays ok", r["status"] == "ok" and r["age_seconds"] == 0, r)

# ---- watchdog (pure functions; no network to anything real)
spec = importlib.util.spec_from_file_location("heartbeat_watch", Path(__file__).resolve().parent.parent / "deploy" / "heartbeat_watch.py")
hw = importlib.util.module_from_spec(spec); spec.loader.exec_module(hw)
check("first observation ok -> no message", hw.transition_message(None, {"status": "ok"}) is None)
check("first observation down -> message", "down" in (hw.transition_message(None, {"status": "down", "age_seconds": 5000}) or ""))
check("ok -> late -> message", "late" in (hw.transition_message("ok", {"status": "late", "age_seconds": 700}) or ""))
check("down -> ok -> recovery message", "recovered" in (hw.transition_message("down", {"status": "ok", "age_seconds": 3}) or ""))
check("same status -> no spam", hw.transition_message("down", {"status": "down"}) is None)
check("unreachable API reported, not raised", hw.fetch("http://127.0.0.1:1", timeout=1)["status"] == "api_unreachable")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
