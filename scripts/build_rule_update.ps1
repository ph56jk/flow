param(
    [string]$Version = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = Get-Date -Format "yyyyMMdd-HHmmss"
}
$safeVersion = $Version -replace "[^A-Za-z0-9._-]", "_"
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $root "dist\rule-updates"
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$files = @(
    "flow_web/shot_rules.py",
    "flow_web/service.py"
)
$workDir = Join-Path ([System.IO.Path]::GetTempPath()) ("flow-rule-update-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $workDir -Force | Out-Null

try {
    $manifestFiles = @()
    foreach ($relative in $files) {
        $source = Join-Path $root $relative.Replace("/", "\")
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Khong tim thay file rule: $relative"
        }
        $target = Join-Path $workDir ("payload\" + $relative.Replace("/", "\"))
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Force
        $manifestFiles += @{
            path = $relative
            sha256 = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
        }
    }

    $manifest = @{
        format = "flow-rule-update-v1"
        version = $Version
        created_at = (Get-Date).ToString("o")
        files = $manifestFiles
    } | ConvertTo-Json -Depth 6
    Set-Content -LiteralPath (Join-Path $workDir "rule-update.json") -Value $manifest -Encoding UTF8

    $zipPath = Join-Path $OutputDir "flow-rule-update-$safeVersion.zip"
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -Path (Join-Path $workDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Host "Da tao goi cap nhat rule: $zipPath"
} finally {
    if (Test-Path -LiteralPath $workDir) {
        Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
