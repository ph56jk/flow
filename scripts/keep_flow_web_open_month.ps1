param(
    [string]$AppHost = "127.0.0.1",
    [int]$Port = 6000,
    [string]$Until = "",
    [int]$HealthIntervalSeconds = 30,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$logsDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$watchdogLog = Join-Path $logsDir "flow-web-$Port-watchdog.log"
$pidFile = Join-Path $logsDir "flow-web-$Port-watchdog.pid"

function Write-WatchdogLog {
    param([string]$Message)

    $line = "{0} {1}" -f (Get-Date).ToString("s"), $Message
    Add-Content -LiteralPath $watchdogLog -Value $line -Encoding UTF8
}

function Test-FlowHealth {
    try {
        $url = "http://$AppHost`:$Port/api/health"
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    } catch {
        return $false
    }
}

function Get-FlowListener {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Start-FlowServer {
    $python = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        throw "Missing venv python: $python"
    }

    $runtime = Join-Path $PSScriptRoot "windows_runtime.ps1"
    if (Test-Path $runtime) {
        . $runtime
        if ([string]::IsNullOrWhiteSpace($env:PLAYWRIGHT_BROWSERS_PATH)) {
            $dataRoot = Get-PreferredDataRoot
            $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $dataRoot "pw-flow"
        }
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $stdoutLog = Join-Path $logsDir "flow-web-$Port.$stamp.out.log"
    $stderrLog = Join-Path $logsDir "flow-web-$Port.$stamp.err.log"
    $serverArgs = @(
        "-m",
        "uvicorn",
        "flow_web.main:app",
        "--host",
        $AppHost,
        "--port",
        "$Port"
    )

    $process = Start-Process `
        -FilePath $python `
        -ArgumentList $serverArgs `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru

    Write-WatchdogLog "Started Flow web on http://$AppHost`:$Port, PID $($process.Id)."
    return $process
}

$deadline = if ([string]::IsNullOrWhiteSpace($Until)) {
    (Get-Date).AddMonths(1)
} else {
    ([datetimeoffset]::Parse($Until)).LocalDateTime
}

Set-Content -LiteralPath $pidFile -Value $PID -Encoding UTF8
Write-WatchdogLog "Watchdog started for http://$AppHost`:$Port until $($deadline.ToString("s")); PID $PID."

$child = $null
$openedBrowser = $false
$sleepSeconds = [Math]::Max(5, $HealthIntervalSeconds)

while ((Get-Date) -lt $deadline) {
    if ($child -and $child.HasExited) {
        Write-WatchdogLog "Flow web process PID $($child.Id) exited with code $($child.ExitCode)."
        $child = $null
    }

    if (Test-FlowHealth) {
        if ($OpenBrowser -and -not $openedBrowser) {
            Start-Process "http://$AppHost`:$Port"
            $openedBrowser = $true
            Write-WatchdogLog "Opened browser for http://$AppHost`:$Port."
        }
        Start-Sleep -Seconds $sleepSeconds
        continue
    }

    $listener = Get-FlowListener
    if ($listener) {
        Write-WatchdogLog "Port $Port is listening on PID $($listener.OwningProcess), but health check failed."
        Start-Sleep -Seconds $sleepSeconds
        continue
    }

    try {
        $child = Start-FlowServer
    } catch {
        Write-WatchdogLog "ERROR starting Flow web: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds 10
}

Write-WatchdogLog "Watchdog reached deadline $($deadline.ToString("s")) and stopped monitoring."
