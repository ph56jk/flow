param(
    [string]$AppHost = "127.0.0.1",
    [int]$Port = 1506,
    [int]$StartupDelaySeconds = 0,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$logsDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$startupLog = Join-Path $logsDir "flow-web.startup.$stamp.log"

function Write-StartupLog {
    param([string]$Message)

    $line = "{0} {1}" -f (Get-Date).ToString("s"), $Message
    Add-Content -LiteralPath $startupLog -Value $line -Encoding UTF8
}

function Test-FlowHealth {
    try {
        $url = "http://$AppHost`:$Port/api/health"
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 3 -UseBasicParsing
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    } catch {
        return $false
    }
}

Write-StartupLog "Startup launcher begin for http://$AppHost`:$Port."

if ($StartupDelaySeconds -gt 0) {
    Write-StartupLog "Waiting $StartupDelaySeconds seconds before start."
    Start-Sleep -Seconds $StartupDelaySeconds
}

$healthy = Test-FlowHealth
if ($healthy) {
    Write-StartupLog "Flow web is already healthy."
    if ($OpenBrowser) {
        Start-Process "http://$AppHost`:$Port"
    }
    exit 0
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    Write-StartupLog "Port is already listening on PID $($listener.OwningProcess), but health check did not pass."
    if ($OpenBrowser) {
        Start-Process "http://$AppHost`:$Port"
    }
    exit 0
}

$runner = Join-Path $PSScriptRoot "run_flow_web.ps1"
$stdoutLog = Join-Path $logsDir "flow-web.autostart.$stamp.out.log"
$stderrLog = Join-Path $logsDir "flow-web.autostart.$stamp.err.log"
$python = Join-Path $root ".venv\Scripts\python.exe"

try {
    $runtime = Join-Path $PSScriptRoot "windows_runtime.ps1"
    if (Test-Path $runtime) {
        . $runtime
        if ([string]::IsNullOrWhiteSpace($env:PLAYWRIGHT_BROWSERS_PATH)) {
            $dataRoot = Get-PreferredDataRoot
            $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $dataRoot "pw-flow"
        }
        Write-StartupLog "PLAYWRIGHT_BROWSERS_PATH=$env:PLAYWRIGHT_BROWSERS_PATH"
    }

    if (Test-Path $python) {
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

        Write-StartupLog "Started uvicorn directly, PID $($process.Id)."
    } else {
        $runnerArgs = @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $runner,
            "-AppHost",
            $AppHost,
            "-Port",
            "$Port"
        )

        if (-not $OpenBrowser) {
            $runnerArgs += "-NoOpenBrowser"
        }

        $process = Start-Process `
            -FilePath "powershell.exe" `
            -ArgumentList $runnerArgs `
            -WorkingDirectory $root `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog `
            -PassThru

        Write-StartupLog "Started run_flow_web.ps1 fallback, PID $($process.Id)."
    }

    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 1
        if (Test-FlowHealth) {
            Write-StartupLog "Flow web health check passed."
            if ($OpenBrowser) {
                Start-Process "http://$AppHost`:$Port"
            }
            exit 0
        }

        if ($process.HasExited) {
            Write-StartupLog "Started process exited early with code $($process.ExitCode)."
            break
        }
    }

    if (Test-Path $stderrLog) {
        $tail = Get-Content -LiteralPath $stderrLog -Tail 20 -ErrorAction SilentlyContinue
        if ($tail) {
            Write-StartupLog "stderr tail:"
            foreach ($line in $tail) {
                Write-StartupLog $line
            }
        }
    }

    throw "Flow web did not become healthy on http://$AppHost`:$Port."
} catch {
    Write-StartupLog "ERROR: $($_.Exception.Message)"
    throw
}
