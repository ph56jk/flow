# Đăng ký Flow v2, Content Image Runner và Agent điều phối thành Scheduled Task
# trên host Windows.
#
#   - Tự khởi động khi người dùng đăng nhập (Flow cần phiên GUI để chạy Chrome).
#   - Tự khởi động lại khi crash.
#   - Không chứa secret; secret nằm trong runner\.env với ACL giới hạn.
#
# Chạy bằng PowerShell của chính tài khoản sẽ host runner:
#   powershell -NoProfile -ExecutionPolicy Bypass -File install-windows-services.ps1
#
# Thêm một task vào máy đang chạy thì đừng đăng ký lại cả ba: mỗi lần đăng ký
# là một lần Unregister rồi Register, tức là dừng thật một dịch vụ đang phục
# vụ để đổi lấy đúng một dòng cấu hình y hệt cũ.  Dùng -Only:
#
#   ... -File install-windows-services.ps1 -Only 'HaviGroup Orchestrator Runner'

param(
    # Rỗng = đăng ký tất cả.  Tên phải khớp nguyên văn tên task bên dưới.
    [string[]] $Only = @()
)

$ErrorActionPreference = 'Stop'

$RepoRoot   = 'C:\HaviGroup\flow-v2'
$RunnerDir  = Join-Path $RepoRoot 'automation_center\runner'
$LogDir     = 'C:\HaviGroup\logs'
# Máy này là workgroup, nên $env:USERDOMAIN trả "WORKGROUP" chứ không phải
# tên máy — Scheduled Task sẽ không phân giải được tài khoản.  Dùng COMPUTERNAME.
$UserId     = "$env:COMPUTERNAME\$env:USERNAME"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Register-HvgTask {
    param(
        [Parameter(Mandatory)][string] $TaskName,
        [Parameter(Mandatory)][string] $ScriptPath,
        [Parameter(Mandatory)][string] $LogName
    )

    if ($Only.Count -gt 0 -and $Only -notcontains $TaskName) {
        Write-Host "Bỏ qua (không có trong -Only): $TaskName"
        return
    }

    if (-not (Test-Path $ScriptPath)) { throw "Thiếu script: $ScriptPath" }

    # Bọc qua cmd.exe để gom stdout/stderr vào một file log duy nhất.
    $inner = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
    $logPath = Join-Path $LogDir $LogName
    $argument = "/c $inner >> `"$logPath`" 2>&1"

    $action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $argument -WorkingDirectory $RepoRoot

    # Trigger lặp 5 phút — đây mới là thứ dựng lại tiến trình đã chết.
    #
    # `RestartCount` bên dưới KHÔNG làm việc đó. Đo tay ngày 2026-08-20: giết
    # uvicorn của Flow v2 thì Task Scheduler ghi Event 102 "successfully
    # finished" với return code 4294967295, task về `Ready`, `NextRunTime`
    # trống, và nằm im vô hạn. Windows chỉ coi là thất bại khi task không khởi
    # động được, chứ không phải khi tiến trình con thoát với mã lỗi. Chỉ có hai
    # trigger boot/logon thì một cú crash lúc 2h sáng nghĩa là chết tới sáng.
    #
    # `MultipleInstances IgnoreNew` bên dưới là thứ khiến việc này an toàn: tick
    # rơi vào lúc task đang chạy thì bị bỏ qua, không có chuyện chạy hai bản.
    $repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
        -RepetitionInterval (New-TimeSpan -Minutes 5)
    # Duration rỗng = lặp vô hạn. Không dùng [TimeSpan]::MaxValue: nó sinh ra
    # P99999999DT23H59M59S và Task Scheduler từ chối nguyên cả XML.
    $repeat.Repetition.Duration = ''

    # Boot: chạy khi máy khởi động, không cần ai đăng nhập. Logon: dựng lại sau
    # khi có người lỡ tay dừng task.
    $triggers = @(
        (New-ScheduledTaskTrigger -AtStartup),
        (New-ScheduledTaskTrigger -AtLogOn -User $UserId),
        $repeat
    )
    # RestartCount chỉ cứu được trường hợp task không khởi động nổi. Tiến trình
    # chết giữa chừng là việc của $repeat ở trên.
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
        -MultipleInstances IgnoreNew
    # S4U: chạy dưới tài khoản này kể cả khi không có ai đăng nhập, và KHÔNG
    # phải lưu mật khẩu ở bất cứ đâu.  Flow chạy Chrome headless nên không cần
    # desktop session — chỉ lần đăng nhập Google đầu tiên mới cần GUI.
    $principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType S4U -RunLevel Highest

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers `
        -Settings $settings -Principal $principal | Out-Null
    Write-Host "Đã đăng ký task: $TaskName"
}

Register-HvgTask -TaskName 'HaviGroup Flow v2' `
    -ScriptPath (Join-Path $RunnerDir 'run-flow-v2.ps1') -LogName 'flow-v2.log'

Register-HvgTask -TaskName 'HaviGroup Content Image Runner' `
    -ScriptPath (Join-Path $RunnerDir 'run-content-image-runner.ps1') -LogName 'content-image-runner.log'

# Agent điều phối: cùng một khuôn S4U / boot + logon / lặp 5 phút như hai task
# kia.  Nó không mở trình duyệt nên không vướng chuyện Session 0.  Bản repo mà
# nó sửa code KHÔNG phải bản này — đó là $env:AGENT_REPO_DIR trong
# orchestrator.env, và run-orchestrator-runner.ps1 từ chối chạy nếu hai đường
# dẫn trùng nhau.
Register-HvgTask -TaskName 'HaviGroup Orchestrator Runner' `
    -ScriptPath (Join-Path $RunnerDir 'run-orchestrator-runner.ps1') -LogName 'orchestrator-runner.log'

Write-Host ''
Write-Host 'Khởi động ngay:'
Write-Host '  Start-ScheduledTask -TaskName "HaviGroup Flow v2"'
Write-Host '  Start-ScheduledTask -TaskName "HaviGroup Content Image Runner"'
Write-Host '  Start-ScheduledTask -TaskName "HaviGroup Orchestrator Runner"'
Write-Host ''
Write-Host 'Runner sẽ thoát với mã 78 cho tới khi runner\.env có đủ secret.'
Write-Host 'Agent điều phối cần thêm OPENAI_API_KEY và AGENT_REPO_DIR trong orchestrator.env.'
