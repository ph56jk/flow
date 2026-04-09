param(
    [string]$OutputDir = "",
    [switch]$SkipChromium,
    [switch]$KeepExistingOutput
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. (Join-Path $PSScriptRoot "windows_runtime.ps1")

function Invoke-RobocopyMirror {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination,
        [string[]]$ExcludeDirs = @(),
        [string[]]$ExcludeFiles = @()
    )

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null

    $args = @(
        $Source,
        $Destination,
        "/MIR",
        "/R:1",
        "/W:1",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP"
    )

    if ($ExcludeDirs.Count -gt 0) {
        $args += "/XD"
        $args += $ExcludeDirs
    }
    if ($ExcludeFiles.Count -gt 0) {
        $args += "/XF"
        $args += $ExcludeFiles
    }

    & robocopy @args | Out-Host
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy that bai voi exit code $LASTEXITCODE"
    }
}

function Get-ProjectDependencies {
    param([string]$ProjectRoot)

    $pyprojectPath = Join-Path $ProjectRoot "pyproject.toml"
    if (-not (Test-Path $pyprojectPath)) {
        throw "Khong tim thay pyproject.toml tai $ProjectRoot"
    }

    $deps = @()
    $insideBlock = $false
    foreach ($line in Get-Content -Path $pyprojectPath) {
        $trimmed = $line.Trim()
        if (-not $insideBlock) {
            if ($trimmed -eq "dependencies = [") {
                $insideBlock = $true
            }
            continue
        }

        if ($trimmed -eq "]") {
            break
        }

        if ($trimmed.StartsWith('"') -or $trimmed.StartsWith("'")) {
            $deps += $trimmed.TrimEnd(",").Trim('"').Trim("'")
        }
    }

    if ($deps.Count -eq 0) {
        throw "Khong doc duoc dependency tu pyproject.toml"
    }
    return $deps
}

if (-not (Test-IsWindows)) {
    throw "Script nay chi dung de build portable tren Windows."
}

$distRoot = Join-Path $root "dist"
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $distRoot "flow-windows-portable"
}

if ((Test-Path $OutputDir) -and (-not $KeepExistingOutput)) {
    Remove-Item -Path $OutputDir -Recurse -Force
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$dataRoot = Get-PreferredDataRoot
$portablePythonExe = Ensure-PortablePython -DataRoot $dataRoot
$portablePythonRoot = Split-Path -Parent (Split-Path -Parent $portablePythonExe)

$runtimeRoot = Join-Path $OutputDir ".portable-runtime"
$bundlePythonRoot = Join-Path $runtimeRoot "python"
$bundleSitePackages = Join-Path $runtimeRoot "site-packages"
$bundleBrowserPath = Join-Path $runtimeRoot "pw-browsers"
$emptyDataRoot = Join-Path $OutputDir "data"

$excludeDirs = @(
    ".git",
    ".venv",
    "dist",
    "data",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".local",
    ".codex",
    ".beads",
    ".beads-server",
    ".ralph-tui",
    ".ralph-output",
    "_bmad-output",
    "__pycache__"
)
$excludeFiles = @(
    ".env.local",
    "*.pyc",
    "*.pyo",
    "*.log"
)

Invoke-RobocopyMirror -Source $root -Destination $OutputDir -ExcludeDirs $excludeDirs -ExcludeFiles $excludeFiles

Invoke-RobocopyMirror -Source $portablePythonRoot -Destination $bundlePythonRoot

New-Item -ItemType Directory -Path $bundleSitePackages -Force | Out-Null
New-Item -ItemType Directory -Path $bundleBrowserPath -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $emptyDataRoot "uploads") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $emptyDataRoot "downloads") -Force | Out-Null

$deps = Get-ProjectDependencies -ProjectRoot $root

Invoke-Checked -Label "pip install portable deps" -Script {
    & $portablePythonExe -m pip install --break-system-packages --upgrade --target $bundleSitePackages @deps
}

if (-not $SkipChromium) {
    $sourceBrowserPath = $env:PLAYWRIGHT_BROWSERS_PATH
    if ([string]::IsNullOrWhiteSpace($sourceBrowserPath)) {
        $sourceBrowserPath = Join-Path $dataRoot "pw-flow"
    }
    if ((Test-Path $sourceBrowserPath) -and (Test-PlaywrightChromiumInstalled -BrowserPath $sourceBrowserPath)) {
        Invoke-RobocopyMirror -Source $sourceBrowserPath -Destination $bundleBrowserPath
    } else {
        $env:PLAYWRIGHT_BROWSERS_PATH = $bundleBrowserPath
        Invoke-Checked -Label "playwright install portable chromium" -Script {
            & $portablePythonExe -m playwright install chromium
        }
    }
}

$launcherCmd = @'
@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\run_flow_web_portable.ps1"
'@
Set-Content -Path (Join-Path $OutputDir "Flow Web UI.cmd") -Value $launcherCmd -Encoding ASCII

$readme = @"
Flow Web UI - Windows Portable

1. Giai nen thu muc nay vao o dia con trong.
2. Double click file 'Flow Web UI.cmd'.
3. App se mo tai http://127.0.0.1:8000

Ban nay da kem san:
- Python portable
- dependency Python
- Chromium cho Playwright

Khong can tai lai Internet cho lan chay dau, tru khi chinh code va tu build lai bundle.
"@
Set-Content -Path (Join-Path $OutputDir "PORTABLE-README.txt") -Value $readme -Encoding UTF8

Write-Host "Da build xong Windows portable tai: $OutputDir"
