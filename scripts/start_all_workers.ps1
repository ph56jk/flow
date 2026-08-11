param(
    [switch]$NoOpenBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

function Start-WorkerLauncher {
    param(
        [string]$ScriptName,
        [string[]]$Arguments
    )

    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    $argumentList = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        ('"{0}"' -f $scriptPath)
    ) + $Arguments

    Start-Process `
        -FilePath $powershell `
        -ArgumentList $argumentList `
        -WorkingDirectory $root `
        -WindowStyle Hidden | Out-Null
}

$primaryArguments = @("-Port", "3169")
if (-not $NoOpenBrowser) {
    $primaryArguments += "-OpenBrowser"
}
Start-WorkerLauncher -ScriptName "start_flow_web_background.ps1" -Arguments $primaryArguments

$secondaryArguments = @()
if ($NoOpenBrowser) {
    $secondaryArguments += "-NoOpenBrowser"
}
Start-WorkerLauncher -ScriptName "start_flow_worker_3170.ps1" -Arguments $secondaryArguments
Start-WorkerLauncher -ScriptName "start_flow_worker_3171.ps1" -Arguments $secondaryArguments
