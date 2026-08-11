param(
    [string]$TaskName = "HAVI Flow Tool Web AutoStart",
    [string]$AppHost = "127.0.0.1",
    [int]$Port = 1506,
    [string]$DailyAt = "07:00",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$starter = Join-Path $PSScriptRoot "start_flow_web_background.ps1"
$powershell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not (Test-Path $starter)) {
    throw "Missing starter script: $starter"
}

$taskArgs = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-WindowStyle",
    "Hidden",
    "-File",
    "`"$starter`"",
    "-AppHost",
    $AppHost,
    "-Port",
    "$Port",
    "-StartupDelaySeconds",
    "15"
)

if ($OpenBrowser) {
    $taskArgs += "-OpenBrowser"
}

$action = New-ScheduledTaskAction `
    -Execute $powershell `
    -Argument ($taskArgs -join " ") `
    -WorkingDirectory $root

$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
try {
    $logonTrigger.Delay = "PT20S"
} catch {
    # Older Windows builds may not expose Delay on this object.
}

$dailyTrigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($DailyAt, "HH:mm", $null))

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($logonTrigger, $dailyTrigger) `
    -Settings $settings `
    -Principal $principal `
    -Description "Starts the HAVI Flow local web server on logon and each morning." `
    -Force `
    -ErrorAction Stop | Out-Null

Write-Host "Installed scheduled task: $TaskName"
Write-Host "It will start Flow web at http://$AppHost`:$Port on logon and daily at $DailyAt."
