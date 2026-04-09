param(
    [string]$AppHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoOpenBrowser
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. (Join-Path $PSScriptRoot "windows_runtime.ps1")

$runtimeRoot = Join-Path $root ".portable-runtime"
$pythonRoot = Join-Path $runtimeRoot "python"
$sitePackages = Join-Path $runtimeRoot "site-packages"
$browserPath = Join-Path $runtimeRoot "pw-browsers"
$python = Find-LatestPythonExe -PythonRoot $pythonRoot

if (-not (Test-Path $runtimeRoot)) {
    throw "Khong tim thay .portable-runtime. Hay dung ban portable/release day du."
}
if (-not $python) {
    throw "Khong tim thay Python portable trong .portable-runtime\\python."
}
if (-not (Test-Path $sitePackages)) {
    throw "Khong tim thay .portable-runtime\\site-packages. Ban portable nay chua du dependency."
}
if (-not (Test-PlaywrightChromiumInstalled -BrowserPath $browserPath)) {
    throw "Khong tim thay Chromium portable trong .portable-runtime\\pw-browsers."
}

$existingPythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
if ([string]::IsNullOrWhiteSpace($existingPythonPath)) {
    $env:PYTHONPATH = "$sitePackages;$root"
} else {
    $env:PYTHONPATH = "$sitePackages;$root;$existingPythonPath"
}
$env:PLAYWRIGHT_BROWSERS_PATH = $browserPath
$env:PYTHONUTF8 = "1"

$args = @(
    "-m",
    "uvicorn",
    "flow_web.main:app",
    "--host",
    $AppHost,
    "--port",
    "$Port"
)

if (-not $NoOpenBrowser) {
    Start-Job -ScriptBlock {
        param($AppUrl)
        Start-Sleep -Seconds 2
        Start-Process $AppUrl
    } -ArgumentList "http://$AppHost`:$Port" | Out-Null
}

& $python @args
