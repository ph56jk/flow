# Wrapper khởi động Listing 2 ERP Runner trên host Windows (Scheduled Task).
#
# Bí mật chỉ nằm trong runner\listing2-erp.env (ACL giới hạn cho chủ máy, đã gitignore).
# Script không in bất kỳ giá trị nào ra stdout/stderr nên log không chứa secret.
#
# File .env riêng, KHÔNG dùng chung với content-image-runner: hai runner khác
# AUTOMATION_RUNNER_KEY, dùng chung một file sẽ khiến runner này heartbeat
# nhầm key và cướp việc của runner kia.

$ErrorActionPreference = 'Stop'

$RepoRoot = 'C:\HaviGroup\flow-v2'
$EnvFile  = Join-Path $RepoRoot 'automation_center\runner\listing2-erp.env'
$Python   = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Runner   = Join-Path $RepoRoot 'automation_center\runner\listing2_erp_runner.py'

if (-not (Test-Path $EnvFile)) {
    Write-Error "Thiếu file cấu hình runner: $EnvFile"
    exit 78
}

# Nạp KEY=VALUE vào môi trường tiến trình, bỏ qua chú thích và dòng trống.
foreach ($line in Get-Content -LiteralPath $EnvFile -Encoding UTF8) {
    $trimmed = $line.Trim()
    if ($trimmed.Length -eq 0 -or $trimmed.StartsWith('#')) { continue }
    $split = $trimmed.IndexOf('=')
    if ($split -lt 1) { continue }
    $name  = $trimmed.Substring(0, $split).Trim()
    $value = $trimmed.Substring($split + 1).Trim()
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}

if ([string]::IsNullOrWhiteSpace($env:AUTOMATION_RUNNER_SECRET)) {
    Write-Error "AUTOMATION_RUNNER_SECRET chưa được đặt trong $EnvFile"
    exit 78
}
if ($env:AUTOMATION_RUNNER_KEY -ne 'listing2-erp-runner') {
    Write-Error "AUTOMATION_RUNNER_KEY phải là 'listing2-erp-runner' trong $EnvFile"
    exit 78
}

$env:PYTHONUNBUFFERED = '1'
# Console Windows mac dinh la cp1252; runner in thong bao tieng Viet nen se
# crash voi UnicodeEncodeError neu khong bat che do UTF-8.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

& $Python $Runner
exit $LASTEXITCODE
