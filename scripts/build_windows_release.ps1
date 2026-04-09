param(
    [string]$OutputDir = "",
    [string]$ZipPath = "",
    [switch]$SkipChromium,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $root "dist\flow-windows-portable"
}
if ([string]::IsNullOrWhiteSpace($ZipPath)) {
    $ZipPath = Join-Path $root "dist\flow-windows-release.zip"
}

if (-not $SkipBuild) {
    $buildArgs = @{
        OutputDir = $OutputDir
    }
    if ($SkipChromium) {
        $buildArgs["SkipChromium"] = $true
    }
    & (Join-Path $PSScriptRoot "build_windows_portable.ps1") @buildArgs
} elseif (-not (Test-Path $OutputDir)) {
    throw "Khong the SkipBuild vi portable output chua ton tai tai $OutputDir"
}

if (Test-Path $ZipPath) {
    Remove-Item -Path $ZipPath -Force
}

$zipParent = Split-Path -Parent $ZipPath
if (-not (Test-Path $zipParent)) {
    New-Item -ItemType Directory -Path $zipParent -Force | Out-Null
}

$tarExe = Get-Command tar.exe -ErrorAction SilentlyContinue
if ($tarExe) {
    Push-Location $OutputDir
    try {
        & $tarExe.Source -a -cf $ZipPath *
        if ($LASTEXITCODE -ne 0) {
            throw "tar.exe that bai voi exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
} else {
    Compress-Archive -Path (Join-Path $OutputDir "*") -DestinationPath $ZipPath -CompressionLevel Optimal
}

Write-Host "Da dong goi xong release zip tai: $ZipPath"
