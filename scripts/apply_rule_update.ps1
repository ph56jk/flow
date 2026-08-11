param(
    [string]$PackagePath = "",
    [string]$AppHost = "127.0.0.1",
    [int]$Port = 3169,
    [int]$PollSeconds = 5,
    [int]$MaxWaitMinutes = 180,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$allowedFiles = @(
    "flow_web/shot_rules.py",
    "flow_web/service.py"
)
$stopRequestsSent = New-Object 'System.Collections.Generic.HashSet[string]'
$watchdogResume = @()

function Write-Step {
    param([string]$Message)
    Write-Host "[Flow rules] $Message" -ForegroundColor Cyan
}

function Get-ApiState {
    try {
        return Invoke-RestMethod -Uri "http://$AppHost`:$Port/api/state" -TimeoutSec 10
    } catch {
        return $null
    }
}

function Get-ActiveJobs {
    param($State)
    if ($null -eq $State) {
        return @()
    }
    return @(
        $State.jobs | Where-Object {
            $_.status -in @("running", "queued", "pending", "polling")
        }
    )
}

function Request-AutoStop {
    param($Jobs)
    foreach ($job in @($Jobs)) {
        if ($job.type -ne "batch_image") {
            continue
        }
        $result = $job.result
        if (($null -ne $result -and $result.stop_requested) -or $stopRequestsSent.Contains([string]$job.id)) {
            continue
        }
        try {
            Invoke-RestMethod `
                -Method Post `
                -Uri "http://$AppHost`:$Port/api/jobs/$($job.id)/stop" `
                -ContentType "application/json" `
                -Body "{}" `
                -TimeoutSec 10 | Out-Null
            $null = $stopRequestsSent.Add([string]$job.id)
            Write-Step "Da yeu cau Auto dung sau tac vu hien tai: $($job.id)."
        } catch {
            Write-Warning "Khong gui duoc lenh dung Auto $($job.id): $($_.Exception.Message)"
        }
    }
}

function Resolve-UpdatePackage {
    if (-not [string]::IsNullOrWhiteSpace($PackagePath)) {
        $resolved = Resolve-Path -LiteralPath $PackagePath -ErrorAction Stop
        return $resolved.Path
    }

    $candidates = @()
    $searchDirs = @($root, (Join-Path $root "updates"))
    foreach ($dir in $searchDirs) {
        if (-not (Test-Path -LiteralPath $dir)) {
            continue
        }
        $candidates += Get-ChildItem -LiteralPath $dir -Filter "flow-rule-update-*.zip" -File -ErrorAction SilentlyContinue
    }
    $selected = $candidates | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($null -eq $selected) {
        throw "Khong tim thay flow-rule-update-*.zip. Dat goi update canh Cap-nhat-rule.cmd roi chay lai."
    }
    return $selected.FullName
}

function Assert-SafeZipEntries {
    param([string]$ZipPath)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        foreach ($entry in $archive.Entries) {
            $name = [string]$entry.FullName
            $normalized = $name.Replace("\", "/")
            if (
                [string]::IsNullOrWhiteSpace($normalized) -or
                $normalized.StartsWith("/") -or
                $normalized.Contains(":") -or
                @($normalized.Split("/") | Where-Object { $_ -eq ".." }).Count -gt 0
            ) {
                throw "Goi update co duong dan khong an toan: $name"
            }
        }
    } finally {
        $archive.Dispose()
    }
}

function Stop-FlowServer {
    $healthy = $null -ne (Get-ApiState)
    if (-not $healthy) {
        return
    }
    $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Khong dung duoc server tren port $Port de cap nhat rule."
}

function Stop-FlowWatchdogs {
    $watchdogScript = Join-Path $PSScriptRoot "keep_flow_web_open_month.ps1"
    if (-not (Test-Path -LiteralPath $watchdogScript)) {
        return
    }
    $processes = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $command = [string]$_.CommandLine
        $command.IndexOf($watchdogScript, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and
        $command -match "(?i)-Port\s+$Port(?:\s|$)"
    })
    foreach ($process in $processes) {
        $command = [string]$process.CommandLine
        $until = ""
        $interval = 30
        if ($command -match '(?i)-Until\s+"([^"]+)"') {
            $until = $Matches[1]
        } elseif ($command -match '(?i)-Until\s+([^\s]+)') {
            $until = $Matches[1]
        }
        if ($command -match '(?i)-HealthIntervalSeconds\s+(\d+)') {
            $interval = [int]$Matches[1]
        }
        $script:watchdogResume += [pscustomobject]@{
            until = $until
            interval = $interval
            open_browser = ($command -match '(?i)(?:^|\s)-OpenBrowser(?:\s|$)')
        }
        Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
        Write-Step "Da tam dung watchdog PID $($process.ProcessId) de cap nhat an toan."
    }
}

function Start-FlowWatchdogs {
    if ($NoRestart -or $watchdogResume.Count -eq 0) {
        return $false
    }
    $watchdogScript = Join-Path $PSScriptRoot "keep_flow_web_open_month.ps1"
    foreach ($config in $watchdogResume) {
        $arguments = @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $watchdogScript,
            "-AppHost", $AppHost, "-Port", "$Port",
            "-HealthIntervalSeconds", "$($config.interval)"
        )
        if (-not [string]::IsNullOrWhiteSpace([string]$config.until)) {
            $arguments += @("-Until", [string]$config.until)
        }
        if ($config.open_browser) {
            $arguments += "-OpenBrowser"
        }
        Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden
    }
    Write-Step "Da bat lai watchdog voi thoi han cu."
    return $true
}

function Start-FlowServer {
    if ($NoRestart) {
        return
    }
    if (Start-FlowWatchdogs) {
        return
    }
    $portableLauncher = Join-Path $root "Flow v2.cmd"
    if (Test-Path -LiteralPath $portableLauncher) {
        Start-Process -FilePath $portableLauncher -WorkingDirectory $root
    } else {
        $runner = Join-Path $PSScriptRoot "run_flow_web.ps1"
        Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $runner,
            "-AppHost", $AppHost, "-Port", "$Port"
        ) -WorkingDirectory $root
    }
    Write-Step "Da mo lai Flow v2 tai port $Port."
}

$package = Resolve-UpdatePackage
Write-Step "Goi cap nhat: $package"
Assert-SafeZipEntries -ZipPath $package

$workRoot = Join-Path $root ".rule-update-work"
$workDir = Join-Path $workRoot ([guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $workDir -Force | Out-Null

try {
    Expand-Archive -LiteralPath $package -DestinationPath $workDir -Force
    $manifestPath = Join-Path $workDir "rule-update.json"
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw "Goi update thieu rule-update.json."
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ([string]$manifest.format -ne "flow-rule-update-v1") {
        throw "Format goi update khong duoc ho tro."
    }
    $entries = @($manifest.files)
    if ($entries.Count -eq 0) {
        throw "Goi update khong co file nao."
    }

    foreach ($entry in $entries) {
        $relative = ([string]$entry.path).Replace("\", "/").TrimStart("/")
        if ($relative -notin $allowedFiles) {
            throw "Goi rule khong duoc phep thay file: $relative"
        }
        $source = Join-Path $workDir ("payload\" + $relative.Replace("/", "\"))
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Goi update thieu payload: $relative"
        }
        $actualHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        if ($actualHash -ne ([string]$entry.sha256).ToUpperInvariant()) {
            throw "Checksum khong khop: $relative"
        }
        $target = Join-Path $root $relative.Replace("/", "\")
        if (-not (Test-Path -LiteralPath $target)) {
            throw "Ban Flow hien tai thieu file dich: $relative"
        }
    }

    $installedPath = Join-Path $root ".rule-update-installed.json"
    if (Test-Path -LiteralPath $installedPath) {
        try {
            $installed = Get-Content -LiteralPath $installedPath -Raw | ConvertFrom-Json
            if ([string]$installed.version -eq [string]$manifest.version) {
                $allCurrent = $true
                foreach ($entry in $entries) {
                    $relative = ([string]$entry.path).Replace("\", "/").TrimStart("/")
                    $target = Join-Path $root $relative.Replace("/", "\")
                    $targetHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
                    if ($targetHash -ne ([string]$entry.sha256).ToUpperInvariant()) {
                        $allCurrent = $false
                        break
                    }
                }
                if ($allCurrent) {
                    Write-Step "Rule $($manifest.version) da duoc cai tu truoc. Khong can restart tool."
                    return
                }
            }
        } catch {
            Write-Warning "Khong doc duoc lich su update cu; se kiem tra va cap nhat binh thuong."
        }
    }

    $state = Get-ApiState
    if ($null -ne $state) {
        $active = Get-ActiveJobs -State $state
        Request-AutoStop -Jobs $active
        $deadline = (Get-Date).AddMinutes([Math]::Max(1, $MaxWaitMinutes))
        while ($active.Count -gt 0) {
            if ((Get-Date) -ge $deadline) {
                throw "Het thoi gian cho job ket thuc. Chua cap nhat file nao."
            }
            $labels = ($active | ForEach-Object { "$($_.status): $($_.title)" }) -join "; "
            Write-Step "Dang cho $($active.Count) job ket thuc: $labels"
            Start-Sleep -Seconds ([Math]::Max(2, $PollSeconds))
            $state = Get-ApiState
            if ($null -eq $state) {
                throw "Mat ket noi voi tool trong khi dang cho job. Chua cap nhat file nao."
            }
            $active = Get-ActiveJobs -State $state
            Request-AutoStop -Jobs $active
        }
    }

    Write-Step "Khong con job dang chay. Bat dau sao luu va cap nhat."
    Stop-FlowWatchdogs
    Stop-FlowServer

    $safeVersion = ([string]$manifest.version) -replace "[^A-Za-z0-9._-]", "_"
    if ([string]::IsNullOrWhiteSpace($safeVersion)) {
        $safeVersion = Get-Date -Format "yyyyMMdd-HHmmss"
    }
    $backupDir = Join-Path $root ".rule-update-backups\$(Get-Date -Format 'yyyyMMdd-HHmmss')-$safeVersion"
    foreach ($entry in $entries) {
        $relative = ([string]$entry.path).Replace("\", "/").TrimStart("/")
        $target = Join-Path $root $relative.Replace("/", "\")
        $backup = Join-Path $backupDir $relative.Replace("/", "\")
        if (Test-Path -LiteralPath $target) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
            Copy-Item -LiteralPath $target -Destination $backup -Force
        }
    }

    try {
        foreach ($entry in $entries) {
            $relative = ([string]$entry.path).Replace("\", "/").TrimStart("/")
            $source = Join-Path $workDir ("payload\" + $relative.Replace("/", "\"))
            $target = Join-Path $root $relative.Replace("/", "\")
            Copy-Item -LiteralPath $source -Destination $target -Force
            $targetHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
            if ($targetHash -ne ([string]$entry.sha256).ToUpperInvariant()) {
                throw "Xac minh file sau khi cap nhat that bai: $relative"
            }
        }
    } catch {
        Write-Warning "Cap nhat bi loi. Dang phuc hoi cac file cu tu backup."
        foreach ($entry in $entries) {
            $relative = ([string]$entry.path).Replace("\", "/").TrimStart("/")
            $backup = Join-Path $backupDir $relative.Replace("/", "\")
            $target = Join-Path $root $relative.Replace("/", "\")
            if (Test-Path -LiteralPath $backup) {
                Copy-Item -LiteralPath $backup -Destination $target -Force
            }
        }
        Start-FlowServer
        throw
    }

    $installedRecord = @{
        version = [string]$manifest.version
        installed_at = (Get-Date).ToString("o")
        package = Split-Path -Leaf $package
        backup_dir = $backupDir
        files = $entries
    } | ConvertTo-Json -Depth 6
    Set-Content -LiteralPath $installedPath -Value $installedRecord -Encoding UTF8
    Write-Step "Da cap nhat rule $($manifest.version). Backup: $backupDir"

    Start-FlowServer
} finally {
    if (Test-Path -LiteralPath $workDir) {
        Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
