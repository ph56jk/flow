param(
    [switch]$NoOpenBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$port = 3170
$workerName = "worker-3170"
$workerRoot = Join-Path $root "data\workers\3170"
$workerEnv = Join-Path $root ".env.worker-3170.local"
$url = "http://127.0.0.1:$port/"

function Get-EnvValue {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path -LiteralPath $Path)) { return "" }
    $matched = Get-Content -LiteralPath $Path | Where-Object {
        $_ -match "^\s*$([regex]::Escape($Key))\s*="
    } | Select-Object -Last 1
    if (-not $matched) { return "" }
    return (($matched -split "=", 2)[1]).Trim().Trim('"').Trim("'")
}

& (Join-Path $PSScriptRoot "setup_flow_worker_3170.ps1")

$profileDirs = Get-EnvValue -Path $workerEnv -Key "FLOW_CHROME_PROFILE_DIRS"
$profileProjects = Get-EnvValue -Path $workerEnv -Key "FLOW_CHROME_PROFILE_PROJECTS"
if ([string]::IsNullOrWhiteSpace($profileDirs) -or [string]::IsNullOrWhiteSpace($profileProjects)) {
    throw "Worker 3170 chua co Flow account. Hay cau hinh profile va project trong .env.worker-3170.local."
}

$env:FLOW_WORKER_NAME = $workerName
$env:FLOW_DATA_DIR = $workerRoot
$env:FLOW_ENV_FILE = $workerEnv
$env:FLOW_CHROME_PROFILE_DIRS = $profileDirs
$env:FLOW_CHROME_PROFILE_PROJECTS = $profileProjects

function Get-WorkerHealth {
    try {
        return Invoke-RestMethod -Uri "${url}api/health" -TimeoutSec 5
    } catch {
        return $null
    }
}

$health = Get-WorkerHealth
if ($null -ne $health) {
    if ([string]$health.instance -ne $workerName) {
        throw "Port $port dang duoc dung boi instance khac."
    }
    Write-Host "Worker 3170 dang chay san tai $url"
    if (-not $NoOpenBrowser) {
        Start-Process $url
    }
    exit 0
}

$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    throw "Port $port dang bi PID $($listener.OwningProcess) chiem dung."
}

$watchdog = Join-Path $PSScriptRoot "keep_flow_web_open_month.ps1"
$until = (Get-Date).AddMonths(1).ToString("o")
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$watchdog`" -AppHost 127.0.0.1 -Port $port -Until `"$until`""
$watchdogProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -PassThru

$deadline = (Get-Date).AddSeconds(60)
do {
    Start-Sleep -Seconds 2
    $health = Get-WorkerHealth
    if ($null -ne $health -and [string]$health.instance -eq $workerName) {
        Write-Host "Worker 3170 da chay tai $url - watchdog PID $($watchdogProcess.Id)."
        if (-not $NoOpenBrowser) {
            Start-Process $url
        }
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Worker 3170 khong khoi dong trong 60 giay. Xem logs\flow-web-3170-watchdog.log."
