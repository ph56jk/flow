# Nhan RUNNER_SHARED_SECRET qua stdin va ghi vao runner\.env tren host Windows.
#
# Gia tri khong bao gio xuat hien tren command line (tranh lo qua danh sach tien
# trinh), khong in ra stdout va khong vao lich su shell.
#
# Dung tu may Mac:
#   grep '^AUTOMATION_RUNNER_SECRET=' runner/.env | cut -d= -f2- \
#     | ssh hvg-pc "powershell -NoProfile -ExecutionPolicy Bypass -File C:\HaviGroup\flow-v2\automation_center\scripts\set-runner-secret-stdin.ps1"

$ErrorActionPreference = 'Stop'

$secret = [Console]::In.ReadToEnd().Trim()
if ([string]::IsNullOrWhiteSpace($secret)) {
    Write-Error 'Khong nhan duoc secret tu stdin.'
    exit 1
}

$envFile = 'C:\HaviGroup\flow-v2\automation_center\runner\.env'
if (-not (Test-Path $envFile)) {
    Write-Error "Thieu $envFile"
    exit 1
}

$found = $false
$out = foreach ($line in (Get-Content -LiteralPath $envFile -Encoding UTF8)) {
    if ($line -match '^AUTOMATION_RUNNER_SECRET=') {
        $found = $true
        "AUTOMATION_RUNNER_SECRET=$secret"
    } else {
        $line
    }
}
if (-not $found) { $out = @($out) + "AUTOMATION_RUNNER_SECRET=$secret" }
$out | Set-Content -LiteralPath $envFile -Encoding UTF8

# Ghi lai file lam mat ACL ke thua rieng -> siet lai.
$me = "$env:COMPUTERNAME\$env:USERNAME"
& icacls $envFile /inheritance:r | Out-Null
& icacls $envFile /grant:r "${me}:(R,W)" | Out-Null
& icacls $envFile /grant:r 'SYSTEM:(F)' | Out-Null

Write-Host "Da ghi secret ($($secret.Length) ky tu) vao $envFile"
