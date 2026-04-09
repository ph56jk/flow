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

function Find-LatestPythonExe {
    param([string]$PythonRoot)
    if (-not (Test-Path $PythonRoot)) {
        return $null
    }
    return Get-ChildItem -Path $PythonRoot -Recurse -Filter "python.exe" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1 -ExpandProperty FullName
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

    $pythonExe = Find-LatestPythonExe -PythonRoot $pythonRoot
    if (-not (Test-Python311OrNewer $pythonExe)) {
        throw "Khong dung duoc Python portable tu uv tai $pythonRoot"
    }

    return $pythonExe
}

function Test-PlaywrightChromiumInstalled {
    param([string]$BrowserPath)
    if (-not (Test-Path $BrowserPath)) {
        return $false
    }
    return @(Get-ChildItem -Path $BrowserPath -Recurse -Include "chrome.exe", "chrome", "Chromium" -File -ErrorAction SilentlyContinue).Count -gt 0
}

