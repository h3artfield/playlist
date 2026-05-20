# Run the Schedule Builder API from this repo (supports multi-week auto-generate).
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$port = 8765
$listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $listeners) {
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($null -eq $proc) { continue }
    Write-Host "Stopping $($proc.ProcessName) (PID $($proc.Id)) on port $port..."
    Stop-Process -Id $proc.Id -Force
    Start-Sleep -Seconds 1
}

Write-Host "Starting dev API on http://127.0.0.1:$port ..."
python -m binge_schedule.cli serve --host 127.0.0.1 --port $port --reload
