# Restart sach Content Image Runner tren host Windows va in log dau tien.
#
# Phai giet tien trinh python con sot truoc khi xoa log: cmd.exe con giu handle
# nen Remove-Item that bai am tham va ta se doc nham log cu tuong la log moi.

$ErrorActionPreference = 'Stop'

$task = 'HaviGroup Content Image Runner'
$log  = 'C:\HaviGroup\logs\content-image-runner.log'

Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like '*content_image_runner.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

Remove-Item -LiteralPath $log -Force -ErrorAction SilentlyContinue

Start-ScheduledTask -TaskName $task
Start-Sleep -Seconds 25

Write-Host '--- log runner ---'
if (Test-Path $log) { Get-Content -LiteralPath $log -Tail 30 } else { Write-Host '(chua co log)' }

Write-Host ''
Write-Host '--- trang thai task ---'
Get-ScheduledTask -TaskName $task | Get-ScheduledTaskInfo |
    Select-Object TaskName, LastTaskResult, LastRunTime | Format-List
