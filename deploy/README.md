# deploy/ — keeping the scanner alive (operations only)

Why this exists: over the observed span the scanner was running only ~16% of the time, and most of the
loss magnitude in the closed-trade ledger exits inside a monitoring gap. This folder contains no trading
logic — it only supervises the process and reports when it stops.

| File | Purpose |
|---|---|
| `run_supervised.ps1` | Runs `uvicorn app.main:app` (scanner enabled) and restarts it on crash/exit, with capped exponential backoff. Logs to `deploy/logs/supervisor.log`. |
| `heartbeat_watch.py` | Polls `/api/performance/heartbeat`; logs status transitions (ok / late / down / api_unreachable) to `deploy/logs/heartbeat.log`; optional webhook via `HEARTBEAT_WEBHOOK_URL` (off unless you set it). |

Run both (two terminals):

```powershell
powershell -ExecutionPolicy Bypass -File deploy\run_supervised.ps1
python deploy\heartbeat_watch.py --every 60
```

One-shot health check (exit code 0 ok / 1 late / 2 down or unreachable):

```powershell
python deploy\heartbeat_watch.py --once
```

## What this cannot fix
* **A sleeping or shut-down machine.** Restart-on-crash does nothing if the laptop is asleep. For real
  continuous monitoring run the backend on an always-on host, or disable sleep on this machine yourself
  (Settings → System → Power). This script does not change power settings.
* **A process that is running but hung.** The watchdog reports it (`late`/`down`); it does not kill it.

Status thresholds: `ok` < 2 × `SCAN_INTERVAL_SECONDS`, `late` < 4 ×, `down` ≥ 4 × (default interval 300s).
While `late`/`down`, open trades are **not monitored** — TP/stop touches are only noticed on the next cycle.
