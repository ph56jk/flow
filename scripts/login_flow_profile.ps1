param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileDir,
    [Parameter(Mandatory = $true)]
    [string]$ProjectUrl,
    [string]$Label = "Flow profile"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if ($ProjectUrl -notmatch '^https://labs\.google/fx/(?:vi/)?tools/flow/project/[0-9a-f-]+(?:\?.*)?$') {
    throw "ProjectUrl khong phai URL Google Flow hop le."
}

$expandedProfile = [Environment]::ExpandEnvironmentVariables($ProfileDir)
if (-not [System.IO.Path]::IsPathRooted($expandedProfile)) {
    $expandedProfile = Join-Path $root $expandedProfile
}
New-Item -ItemType Directory -Path $expandedProfile -Force | Out-Null
$resolvedProfile = (Resolve-Path -LiteralPath $expandedProfile).Path

$browserRoots = @(
    $env:PLAYWRIGHT_BROWSERS_PATH
    (Join-Path $env:LOCALAPPDATA "ms-playwright")
    "C:\pw-flow"
    "D:\pw-flow"
    "E:\pw-flow"
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path -LiteralPath $_) }

$browser = $browserRoots | ForEach-Object {
    Get-ChildItem -LiteralPath $_ -Recurse -File -Filter "chrome.exe" -ErrorAction SilentlyContinue
} |
    Where-Object { $_.FullName -match "chrome-win64\\chrome\.exe$" } |
    Sort-Object FullName -Descending |
    Select-Object -First 1

if ($null -eq $browser) {
    $browser = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe"
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1 | ForEach-Object { Get-Item -LiteralPath $_ }
}
if ($null -eq $browser) {
    throw "Khong tim thay Chromium/Chrome de dang nhap Flow."
}

$arguments = '--user-data-dir="{0}" --no-first-run --no-default-browser-check "{1}"' -f $resolvedProfile, $ProjectUrl
Start-Process -FilePath $browser.FullName -ArgumentList $arguments -WorkingDirectory $root
Write-Host "Da mo $Label. Dang nhap Google trong cua so vua mo, sau do mo duoc project Flow."
