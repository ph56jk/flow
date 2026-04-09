$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Khong tim thay lenh 'py'. Hay cai Python 3.11 truoc."
}

py -3.11 -m venv .venv

$python = Join-Path $root ".venv\\Scripts\\python.exe"
if (-not (Test-Path $python)) {
    throw "Khong tao duoc virtualenv tai .venv."
}

& $python -m pip install --upgrade pip
& $python -m pip install -e .
& $python -m playwright install chromium

Write-Host "Da cai xong. Chay app bang: .\\scripts\\run_flow_web.ps1"
