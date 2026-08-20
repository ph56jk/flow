# Chuan bi phien dang nhap Google cho Flow v2.
#
# PHAI chay trong cua so PowerShell tren desktop that (DeskIn / man hinh may).
# KHONG chay qua SSH: SSH tren Windows nam o Session 0, va Flow chan Session 0
# tai _assert_windows_interactive_browser_session (flow_web/service.py:6804).
#
# Script tu kiem tra dieu do truoc khi lam gi, roi:
#   1. dung Scheduled Task 'HaviGroup Flow v2' (dang chay o Session 0)
#   2. giet tien trinh Flow con sot (neu khong se ket port 8000)
#   3. chay Flow ngay trong phien nay, o foreground

$ErrorActionPreference = 'Stop'

$me = Get-CimInstance Win32_Process -Filter ("ProcessId = $PID")
if ($me.SessionId -eq 0) {
    Write-Host ''
    Write-Host 'DUNG LAI: cua so nay dang o Session 0 (SSH hoac tac vu nen).' -ForegroundColor Red
    Write-Host 'Dang nhap Google se bi Flow tu choi voi loi HTTP 400.'
    Write-Host 'Hay mo PowerShell trực tiep tren desktop qua DeskIn roi chay lai.'
    Write-Host ''
    exit 1
}

Write-Host ("OK - dang o Session {0} (co desktop)." -f $me.SessionId) -ForegroundColor Green

Stop-ScheduledTask -TaskName 'HaviGroup Flow v2' -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like '*uvicorn*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3

Write-Host ''
Write-Host '=======================================================' -ForegroundColor Cyan
Write-Host ' Flow dang khoi dong trong phien co desktop.'
Write-Host ''
Write-Host ' Viec cua ban:'
Write-Host '   1. Mo trinh duyet tren PC: http://127.0.0.1:8000'
Write-Host '   2. Dang nhap Google'
Write-Host '   3. Chon Project ID'
Write-Host '   4. Bao lai - phan con lai lam qua SSH, KHONG dong cua so nay.'
Write-Host '=======================================================' -ForegroundColor Cyan
Write-Host ''

& powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\HaviGroup\flow-v2\automation_center\runner\run-flow-v2.ps1'
