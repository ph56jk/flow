param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload,
    [switch]$PrepareOnly,
    [switch]$NoOpenBrowser,
    [string]$BrowserPath = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Test-Python311OrNewer {
    param([string]$PythonExe)
    if (-not $PythonExe) {
        return $false
    }
    try {
        $version = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if (-not $version) {
            return $false
        }
        $parts = $version.Trim().Split(".")
        return ([int]$parts[0] -gt 3) -or (([int]$parts[0] -eq 3) -and ([int]$parts[1] -ge 11))
    } catch {
        return $false
    }
}

if ([string]::IsNullOrWhiteSpace($BrowserPath)) {
    if (-not [string]::IsNullOrWhiteSpace($env:PLAYWRIGHT_BROWSERS_PATH)) {
        $BrowserPath = $env:PLAYWRIGHT_BROWSERS_PATH
    } else {
        $BrowserPath = "C:\pw-flow"
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
    throw "Khong tim thay Python 3.11+. Hay cai Python 3.11 roi chay lai."
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
    & $python -m pip install --upgrade pip
    & $python -m pip install -e .
    Set-Content -Path $installStamp -Value (Get-Date).ToString("o") -Encoding UTF8
}

$chromiumInstalled = $false
if (Test-Path $BrowserPath) {
    $chromiumInstalled = @(Get-ChildItem -Path $BrowserPath -Recurse -Include "chrome.exe","chrome","Chromium" -File -ErrorAction SilentlyContinue).Count -gt 0
}

if (-not $chromiumInstalled) {
    New-Item -ItemType Directory -Path $BrowserPath -Force | Out-Null
    & $python -m playwright install chromium
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
    $Host,
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
    } -ArgumentList "http://$Host`:$Port" | Out-Null
}

& $python @args
