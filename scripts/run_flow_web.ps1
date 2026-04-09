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

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Script
    )

    & $Script
    if ($LASTEXITCODE -ne 0) {
        throw "$Label that bai voi exit code $LASTEXITCODE"
    }
}

function Test-IsWindows {
    return [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
}

function Get-PreferredDataRoot {
    if (-not (Test-IsWindows)) {
        return "C:"
    }
    $drives = [System.IO.DriveInfo]::GetDrives() |
        Where-Object { $_.DriveType -eq [System.IO.DriveType]::Fixed -and $_.IsReady } |
        Sort-Object AvailableFreeSpace -Descending

    foreach ($drive in $drives) {
        $rootPath = $drive.RootDirectory.FullName.TrimEnd("\")
        try {
            $probe = Join-Path $rootPath ".flow-write-test"
            New-Item -ItemType Directory -Path $probe -Force | Out-Null
            Remove-Item -Path $probe -Force -ErrorAction SilentlyContinue
            return $rootPath
        } catch {
            continue
        }
    }

    return "C:"
}

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

function Ensure-UvPortable {
    param([string]$DataRoot)

    $runtimeRoot = Join-Path $DataRoot "flow-runtime"
    $uvRoot = Join-Path $runtimeRoot "uv"
    $uvExe = Join-Path $uvRoot "uv.exe"
    if (Test-Path $uvExe) {
        return $uvExe
    }

    $uvZip = Join-Path $runtimeRoot "uv.zip"
    New-Item -ItemType Directory -Path $uvRoot -Force | Out-Null
    Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/0.11.2/uv-x86_64-pc-windows-msvc.zip" -OutFile $uvZip
    Expand-Archive -Force $uvZip $uvRoot
    Remove-Item -Path $uvZip -Force -ErrorAction SilentlyContinue

    if (-not (Test-Path $uvExe)) {
        throw "Khong tai duoc uv portable vao $uvRoot"
    }
    return $uvExe
}

function Ensure-PortablePython {
    param([string]$DataRoot)

    $runtimeRoot = Join-Path $DataRoot "flow-runtime"
    $pythonRoot = Join-Path $runtimeRoot "python"
    $cacheRoot = Join-Path $runtimeRoot "uv-cache"
    $uvExe = Ensure-UvPortable -DataRoot $DataRoot

    New-Item -ItemType Directory -Path $pythonRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $cacheRoot -Force | Out-Null

    $env:UV_CACHE_DIR = $cacheRoot
    $env:UV_PYTHON_INSTALL_DIR = $pythonRoot

    & $uvExe python install 3.11 | Out-Host

    $pythonExe = Get-ChildItem -Path $pythonRoot -Recurse -Filter "python.exe" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1 -ExpandProperty FullName

    if (-not (Test-Python311OrNewer $pythonExe)) {
        throw "Khong dung duoc Python portable tu uv tai $pythonRoot"
    }

    return $pythonExe
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

$chromiumInstalled = $false
if (Test-Path $BrowserPath) {
    $chromiumInstalled = @(Get-ChildItem -Path $BrowserPath -Recurse -Include "chrome.exe","chrome","Chromium" -File -ErrorAction SilentlyContinue).Count -gt 0
}

if (-not $chromiumInstalled) {
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
