param(
    [string]$AppHost = "127.0.0.1",
    [int]$Port = 1506,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$starter = Join-Path $PSScriptRoot "start_flow_web_background.ps1"
if (-not (Test-Path $starter)) {
    throw "Missing starter script: $starter"
}

$startupDir = [Environment]::GetFolderPath("Startup")
if ([string]::IsNullOrWhiteSpace($startupDir)) {
    throw "Cannot resolve current user's Startup folder."
}

New-Item -ItemType Directory -Force -Path $startupDir | Out-Null

$cmdPath = Join-Path $startupDir "HAVI Flow Tool Web.cmd"
$openBrowserArg = if ($OpenBrowser) { " -OpenBrowser" } else { "" }

$content = @"
@echo off
cd /d "$((Split-Path -Parent $PSScriptRoot))"
start "" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$starter" -AppHost "$AppHost" -Port "$Port" -StartupDelaySeconds 15$openBrowserArg
"@

Set-Content -Path $cmdPath -Value $content -Encoding ASCII

Write-Host "Installed Startup launcher:"
Write-Host $cmdPath
Write-Host "It will start Flow web at http://$AppHost`:$Port when this Windows user logs in."
