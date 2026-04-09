param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\\Scripts\\python.exe"
if (-not (Test-Path $python)) {
    throw "Chua co .venv. Hay chay .\\scripts\\setup_windows.ps1 truoc."
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

& $python @args
