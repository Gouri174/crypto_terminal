"""Heartbeat watchdog (Karma V3.3, operations only).

Polls GET /api/performance/heartbeat and records every status change to
deploy/logs/heartbeat.log. Alert channels (all optional, off by default):
  * console/stdout (always)
  * Windows toast via `msg` is NOT used (needs services this box may not have)
  * HEARTBEAT_WEBHOOK_URL env var: if set, a JSON POST {"text": ...} is sent on
    every transition into late/down and back to ok. Nothing is sent unless you
    set that variable yourself.

Standard library only (no new dependencies).

    python deploy/heartbeat_watch.py --url http://127.0.0.1:8000 --every 60
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"


def fetch(url: str, timeout: float = 10.0) -> dict:
    """Returns the heartbeat dict, or a synthetic {'status': 'api_unreachable'} on any failure."""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/api/performance/heartbeat", timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as exc:
        return {"status": "api_unreachable", "error": str(exc)[:200]}


def transition_message(prev: str | None, cur: dict) -> str | None:
    """Returns a message when the status changed (or on first observation of a bad state), else None."""
    status = cur.get("status")
    if status == prev:
        return None
    if prev is None and status == "ok":
        return None
    age = cur.get("age_seconds")
    detail = f" (newest scan {age:.0f}s ago)" if isinstance(age, (int, float)) else ""
    if status == "ok":
        return f"Scanner recovered: status ok{detail}"
    return f"Scanner status {status}{detail} — open trades are NOT being monitored"


def notify(msg: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    line = f"{stamp} {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / "heartbeat.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    hook = os.environ.get("HEARTBEAT_WEBHOOK_URL")
    if hook:
        try:
            req = urllib.request.Request(hook, data=json.dumps({"text": line}).encode("utf-8"), headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as exc:  # never let an alert failure kill the watchdog
            print(f"{stamp} webhook failed: {exc}", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--every", type=int, default=60, help="poll interval, seconds")
    ap.add_argument("--once", action="store_true", help="check once and exit (code 0=ok, 1=late, 2=down/unreachable)")
    args = ap.parse_args(argv)

    prev = None
    while True:
        cur = fetch(args.url)
        msg = transition_message(prev, cur)
        if msg:
            notify(msg)
        prev = cur.get("status")
        if args.once:
            print(json.dumps(cur))
            return 0 if prev == "ok" else 1 if prev == "late" else 2
        time.sleep(args.every)


if __name__ == "__main__":
    sys.exit(main())
