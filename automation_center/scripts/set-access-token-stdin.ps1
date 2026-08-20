# Nhan cap Cloudflare Access Service Token qua stdin va ghi vao runner\.env,
# sau do khoi dong lai runner va doc log de xac nhan.
#
# stdin phai gom dung 2 dong:
#   dong 1: CF_ACCESS_CLIENT_ID      (dang <uuid>.access)
#   dong 2: CF_ACCESS_CLIENT_SECRET
#
# Gia tri khong bao gio xuat hien tren command line (tranh lo qua danh sach tien
# trinh), khong in ra stdout va khong vao lich su shell.
#
# Dung tu may Mac:
#   printf '%s\n%s\n' "$CLIENT_ID" "$CLIENT_SECRET" \
#     | ssh hvg-pc "powershell -NoProfile -ExecutionPolicy Bypass -File C:\HaviGroup\flow-v2\automation_center\scripts\set-access-token-stdin.ps1"

$ErrorActionPreference = 'Stop'

$lines = [Console]::In.ReadToEnd() -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
if ($lines.Count -lt 2) {
    Write-Error 'Can dung 2 dong tren stdin: client id roi client secret.'
    exit 1
}
$clientId     = $lines[0]
$clientSecret = $lines[1]

# Client ID cua Access Service Token luon ket thuc bang ".access"; kiem tra som
# de khong ghi nham thu tu hai dong roi phai debug qua log runner.
if ($clientId -notmatch '\.access$') {
    Write-Error 'Dong 1 khong giong Client ID cua Service Token (phai ket thuc bang ".access").'
    exit 1
}

$envFile = 'C:\HaviGroup\flow-v2\automation_center\runner\.env'
if (-not (Test-Path $envFile)) {
    Write-Error "Thieu $envFile"
    exit 1
}

$pairs = @{
    'CF_ACCESS_CLIENT_ID'     = $clientId
    'CF_ACCESS_CLIENT_SECRET' = $clientSecret
}

$out = foreach ($line in (Get-Content -LiteralPath $envFile -Encoding UTF8)) {
    $matched = $null
    foreach ($key in $pairs.Keys) {
        if ($line -match "^$key=") { $matched = $key; break }
    }
    if ($matched) {
        "$matched=$($pairs[$matched])"
        $pairs.Remove($matched)
    } else {
        $line
    }
}
# Key nao chua co san trong file thi them vao cuoi.
foreach ($key in @($pairs.Keys)) { $out = @($out) + "$key=$($pairs[$key])" }
$out | Set-Content -LiteralPath $envFile -Encoding UTF8

# Ghi lai file lam mat ACL ke thua rieng -> siet lai.
$me = "$env:COMPUTERNAME\$env:USERNAME"
& icacls $envFile /inheritance:r | Out-Null
& icacls $envFile /grant:r "${me}:(R,W)" | Out-Null
& icacls $envFile /grant:r 'SYSTEM:(F)' | Out-Null

Write-Host "Da ghi CF_ACCESS_CLIENT_ID ($($clientId.Length) ky tu) va CF_ACCESS_CLIENT_SECRET ($($clientSecret.Length) ky tu)."

# Restart sach: dung task roi giet python con sot, neu khong file log van bi giu
# va ta se doc nham log cu tuong la log moi.
$task = 'HaviGroup Content Image Runner'
Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like '*content_image_runner.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

$log = 'C:\HaviGroup\logs\content-image-runner.log'
Remove-Item -LiteralPath $log -Force -ErrorAction SilentlyContinue

Start-ScheduledTask -TaskName $task
Start-Sleep -Seconds 20

Write-Host ''
Write-Host '--- log runner (20s dau) ---'
if (Test-Path $log) { Get-Content -LiteralPath $log -Tail 30 } else { Write-Host '(chua co log)' }
