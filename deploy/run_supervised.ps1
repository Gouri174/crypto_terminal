<#
  Supervised backend runner (Karma V3.3, operations only — no app code).

  Restarts the API + scanner if the process exits or crashes, with capped
  exponential backoff, and appends every start/exit to deploy/logs/supervisor.log.

  Usage (from the repo root):
      powershell -ExecutionPolicy Bypass -File deploy\run_supervised.ps1

  What this does NOT do (be honest about it):
    * It cannot keep a sleeping/closed laptop scanning. Uptime was ~16% mainly
      because the dev machine sleeps/shuts down. For continuous monitoring, run
      this on an always-on machine/server, or disable sleep on this one
      (Settings > System > Power). I do not change power settings for you.
    * It does not detect a hung-but-running process; run deploy\heartbeat_watch.py
      alongside it for that.
#>
param(
    [int]$Port = 8000,
    [string]$BindHost = "127.0.0.1",
    [int]$MaxBackoffSeconds = 60,
    [int]$StableAfterSeconds = 600
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repoRoot "backend"
$logDir = Join-Path $PSScriptRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "supervisor.log"
$python = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

function Write-Log($msg) {
    $line = "{0} {1}" -f (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ssZ"), $msg
    Add-Content -Path $log -Value $line
    Write-Host $line
}

$backoff = 2
Write-Log "supervisor started (port $Port, python=$python)"
while ($true) {
    $started = Get-Date
    Write-Log "starting uvicorn app.main:app on ${BindHost}:$Port"
    $env:SCANNER_ENABLED = "true"
    Push-Location $backend
    try {
        & $python -m uvicorn app.main:app --host $BindHost --port $Port
        $code = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    $ranFor = [int]((Get-Date) - $started).TotalSeconds
    Write-Log "uvicorn exited with code $code after ${ranFor}s"
    if ($ranFor -ge $StableAfterSeconds) { $backoff = 2 }
    Write-Log "restarting in ${backoff}s"
    Start-Sleep -Seconds $backoff
    $backoff = [Math]::Min($backoff * 2, $MaxBackoffSeconds)
}
