param(
    [string]$AppHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload,
    [switch]$PrepareOnly,
    [switch]$NoOpenBrowser,
    [string]$BrowserPath = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
. (Join-Path $PSScriptRoot "windows_runtime.ps1")

$currentSessionId = (Get-Process -Id $PID).SessionId
if ($currentSessionId -eq 0 -and -not $PrepareOnly) {
    Write-Warning "Flow Web UI dang chay trong Session 0 (thuong la SSH, task nen hoac service). Kieu nay app van len duoc, nhung cua so dang nhap Google Flow se khong hien tren desktop. Hay mo script nay truc tiep tren man hinh Windows de dang nhap."
}

$dataRoot = Get-PreferredDataRoot

if ([string]::IsNullOrWhiteSpace($BrowserPath)) {
    if (-not [string]::IsNullOrWhiteSpace($env:PLAYWRIGHT_BROWSERS_PATH)) {
        $BrowserPath = $env:PLAYWRIGHT_BROWSERS_PATH
    } else {
        $BrowserPath = Join-Path $dataRoot "pw-flow"
    }
}
$env:PLAYWRIGHT_BROWSERS_PATH = $BrowserPath

$venvPython = Join-Path $root ".venv\\Scripts\\python.exe"
$bootstrapPython = $null

if (Test-Path $venvPython) {
    $bootstrapPython = $venvPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $bootstrapPython = "py311"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    if (Test-Python311OrNewer "python") {
        $bootstrapPython = "python"
    }
}

if (-not $bootstrapPython) {
    if (Test-IsWindows) {
        $bootstrapPython = Ensure-PortablePython -DataRoot $dataRoot
    } else {
        throw "Khong tim thay Python 3.11+. Hay cai Python 3.11 roi chay lai."
    }
}

if (-not (Test-Path $venvPython)) {
    if ($bootstrapPython -eq "py311") {
        & py -3.11 -m venv .venv
    } else {
        & $bootstrapPython -m venv .venv
    }
}

$python = $venvPython
if (-not (Test-Path $python)) {
    throw "Khong tao duoc .venv tai du an."
}

$installStamp = Join-Path $root ".venv\\.flow_install_stamp"
$needsInstall = (-not (Test-Path $installStamp)) -or ((Get-Item (Join-Path $root "pyproject.toml")).LastWriteTimeUtc -gt (Get-Item $installStamp).LastWriteTimeUtc)

if ($needsInstall) {
    Invoke-Checked -Label "pip upgrade" -Script { & $python -m pip install --upgrade pip }
    Invoke-Checked -Label "pip install" -Script { & $python -m pip install -e . }
    Set-Content -Path $installStamp -Value (Get-Date).ToString("o") -Encoding UTF8
}

if (-not (Test-PlaywrightChromiumInstalled -BrowserPath $BrowserPath)) {
    New-Item -ItemType Directory -Path $BrowserPath -Force | Out-Null
    Invoke-Checked -Label "playwright install" -Script { & $python -m playwright install chromium }
}

if ($PrepareOnly) {
    Write-Host "Da setup xong. Mo app bang: .\\scripts\\run_flow_web.ps1"
    exit 0
}

$args = @(
    "-m",
    "uvicorn",
    "flow_web.main:app",
    "--host",
    $AppHost,
    "--port",
    "$Port"
)

if ($Reload) {
    $args += "--reload"
}

if (-not $NoOpenBrowser) {
    Start-Job -ScriptBlock {
        param($AppUrl)
        Start-Sleep -Seconds 2
        Start-Process $AppUrl
    } -ArgumentList "http://$AppHost`:$Port" | Out-Null
}

& $python @args
