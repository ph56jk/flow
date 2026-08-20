# Dat PC trung tam ve che do chay co dinh 24/7.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File set-always-on.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File set-always-on.ps1 -DryRun
#
# Lop Scheduled Task da dung san tu install-windows-services.ps1 (S4U, trigger
# AtStartup + AtLogOn, RestartCount 999).  Nghia la phan mem da tu song lai sau
# reboot va sau crash.  Cai chua duoc xu ly la ban than cai may: ngay
# 2026-08-15 ca hai runner ngung heartbeat luc 01:00Z va Tailscale bao PC
# "offline, last seen 1d ago" - may tat hoac ngu, khong phai runner chet.
#
# Script chi cham vao nguon dien, card mang, dich vu Tailscale va trang thai
# task.  Khong cham vao secret, khong cham vao code, khong cai dat gi moi.
#
# KHONG lam duoc tu day (phai vao BIOS tan noi):
#   Restore on AC Power Loss = Power On
# Thieu muc do thi mat dien xong may nam im, moi thu ben duoi thanh vo nghia.

param([switch]$DryRun)

$ErrorActionPreference = 'Stop'

$script:changed = 0
$script:missing = 0

function Say-Ok      { param($m) Write-Host "  [OK]    $m" }
function Say-Changed { param($m) Write-Host "  [DA SUA] $m"; $script:changed++ }
function Say-Missing { param($m) Write-Host "  [THIEU]  $m"; $script:missing++ }
function Say-Note    { param($m) Write-Host "  [!]      $m" }

function Invoke-Change {
    param([string] $What, [scriptblock] $Action)
    if ($DryRun) { Say-Note "DryRun - bo qua: $What"; return }
    & $Action
    Say-Changed $What
}

# powercfg, HKLM, Set-Service va Set-NetAdapterPowerManagement deu can quyen
# Administrator.  Chan ngay tu dau thay vi de script chet giua chung, luc do
# mot nua thiet lap da doi con mot nua chua.
if (-not $DryRun) {
    $me = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $me.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Phai chay bang PowerShell Run as Administrator (hoac dung -DryRun de chi xem).'
    }
}

# powercfg /query in ra ca khoi; chi so AC nam o dong
#   Current AC Power Setting Index: 0x00000000
# Tach rieng phan doc chuoi ra khoi phan goi powercfg de con test duoc.  Tra ve
# $null khi khong doc duoc, de bao "khong kiem duoc" thay vi bao nham la da dat
# dung.  Dung Int64 vi 0xffffffff tran Int32.
function Read-AcIndex {
    param([string[]] $Lines)
    # Bat dung so ngay sau dau hai cham cua dong AC.  Khong tach theo dau hai
    # cham roi lay phan tu cuoi: dong DC nam ngay duoi, chi can hai dong dinh
    # vao nhau la lay nham gia tri cua DC ma van ra mot so trong nhu that.
    foreach ($line in $Lines) {
        if ($line -match 'Current AC Power Setting Index:\s*(0x)?([0-9a-fA-F]+)') {
            try { return [Convert]::ToInt64($Matches[2], 16) } catch { return $null }
        }
    }
    return $null
}

function Get-AcIndex {
    param([string] $SubGuid, [string] $SettingGuid)
    try {
        return Read-AcIndex (powercfg /query SCHEME_CURRENT $SubGuid $SettingGuid 2>$null)
    } catch { return $null }
}

$SUB_SLEEP    = '238c9fa8-0aad-41ed-83f4-97be242c8f20'
$STANDBYIDLE  = '29f6c1db-86da-48c5-9fdb-f2b67b1f44da'
$HIBERNATEIDLE = '9d7815a6-7ee4-497e-8888-515a05f02364'

Write-Host '== Nguon dien =='

# Mot may chu khong duoc ngu, khong duoc tat o cung, khong duoc ngu dong.
foreach ($pair in @(
    @{ Arg = 'standby-timeout-ac';   Ten = 'khong bao gio ngu' },
    @{ Arg = 'hibernate-timeout-ac'; Ten = 'khong bao gio ngu dong' },
    @{ Arg = 'disk-timeout-ac';      Ten = 'khong tat o cung' },
    @{ Arg = 'monitor-timeout-ac';   Ten = 'khong tat man hinh' }
)) {
    Invoke-Change "$($pair.Ten) (powercfg /change $($pair.Arg) 0)" { powercfg /change $pair.Arg 0 | Out-Null }
}

# hibernate off tat luon Fast Startup va giai phong hiberfil.sys - dang quy vi o
# C: chi con ~23 GB.  Nhung tren may CO PIN thi tat ngu dong la mat du lieu khi
# het pin, nen chi lam khi chac chan day la may ban.
$battery = @(Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue)
if ($battery.Count -gt 0) {
    Say-Note 'May co pin - BO QUA "powercfg /hibernate off" (tat ngu dong tren may pin la mat du lieu khi can pin).'
} else {
    Invoke-Change 'tat ngu dong va Fast Startup (powercfg /hibernate off)' { powercfg /hibernate off | Out-Null }
}

# Fast Startup con mot cong tac rieng trong registry.  Tat no la de sau khi mat
# dien, may khoi dong "sach" chu khong khoi phuc lai mot phien Session 0 cu.
$powerKey = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power'
$hiberboot = (Get-ItemProperty -Path $powerKey -Name HiberbootEnabled -ErrorAction SilentlyContinue).HiberbootEnabled
if ($hiberboot -eq 0) {
    Say-Ok 'Fast Startup da tat (HiberbootEnabled = 0)'
} else {
    Invoke-Change 'tat Fast Startup (HiberbootEnabled = 0)' {
        Set-ItemProperty -Path $powerKey -Name HiberbootEnabled -Value 0 -Type DWord
    }
}

$standby = Get-AcIndex $SUB_SLEEP $STANDBYIDLE
$hib     = Get-AcIndex $SUB_SLEEP $HIBERNATEIDLE
if ($null -eq $standby) { Say-Note 'Khong doc duoc chi so sleep de kiem tra lai.' }
elseif ($standby -eq 0 -and ($null -eq $hib -or $hib -eq 0)) { Say-Ok 'Kiem lai: sleep va hibernate deu = 0 (khong bao gio)' }
else { Say-Missing "Kiem lai: sleep = $standby, hibernate = $hib - dang khac 0, may van se tu ngu." }

Write-Host ''
Write-Host '== Card mang =='

# Windows duoc phep tat card mang de tiet kiem dien.  Card tat thi Tailscale mat
# va SSH vao may cung mat, dung luc can vao xem tai sao no im.
try {
    $adapters = @(Get-NetAdapter -Physical -ErrorAction Stop | Where-Object { $_.Status -eq 'Up' })
    if ($adapters.Count -eq 0) { Say-Missing 'Khong thay card mang nao dang Up.' }
    foreach ($adapter in $adapters) {
        $power = Get-NetAdapterPowerManagement -Name $adapter.Name -ErrorAction SilentlyContinue
        if ($null -eq $power) { Say-Note "$($adapter.Name): card khong ho tro cau hinh nguon, bo qua."; continue }
        if ($power.AllowComputerToTurnOffDevice -eq 'Disabled' -or $power.AllowComputerToTurnOffDevice -eq 'Unsupported') {
            Say-Ok "$($adapter.Name): Windows khong duoc phep tat card nay"
        } else {
            Invoke-Change "$($adapter.Name): cam Windows tat card de tiet kiem dien" {
                Set-NetAdapterPowerManagement -Name $adapter.Name -AllowComputerToTurnOffDevice Disabled
            }
        }
    }
} catch {
    Say-Note "Khong kiem duoc card mang: $($_.Exception.Message)"
}

Write-Host ''
Write-Host '== Tailscale =='

# Tailscale phai la dich vu chay tu dong: no la duong duy nhat de vao may khi
# khong co ai dang nhap.  Neu no chi chay khi co nguoi login thi sau reboot may
# song ma ta van khong vao duoc.
$tailscale = Get-Service -Name 'Tailscale' -ErrorAction SilentlyContinue
if ($null -eq $tailscale) {
    Say-Missing 'Khong thay dich vu Tailscale - kiem tra lai ban cai.'
} else {
    if ($tailscale.StartType -eq 'Automatic') {
        Say-Ok 'Dich vu Tailscale khoi dong tu dong'
    } else {
        Invoke-Change "Tailscale: doi StartupType tu $($tailscale.StartType) sang Automatic" {
            Set-Service -Name 'Tailscale' -StartupType Automatic
        }
    }
    if ($tailscale.Status -eq 'Running') {
        Say-Ok 'Dich vu Tailscale dang chay'
    } else {
        Invoke-Change 'Tailscale: khoi dong dich vu' { Start-Service -Name 'Tailscale' }
    }
}

Write-Host ''
Write-Host '== Scheduled Task =='

# Khong dang ky task moi o day - do la viec cua install-windows-services.ps1.
# Cho nay chi soi lai ba dieu kien khien task that su tu chay lai sau reboot.
$expected = @(
    'HaviGroup Flow v2',
    'HaviGroup Content Image Runner',
    'HaviGroup Listing2 ERP Runner',
    'HaviGroup Orchestrator Runner'
)
foreach ($name in $expected) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($null -eq $task) { Say-Missing "$name - chua dang ky"; continue }

    $wasOff = $task.State -eq 'Disabled'
    if ($wasOff) {
        # -DryRun khong bat gi ca, nen van con la mot muc phai xu ly.
        if ($DryRun) { Say-Missing "$name - dang Disabled" }
        else { Invoke-Change "$name - dang Disabled, bat lai" { Enable-ScheduledTask -TaskName $name | Out-Null } }
    }

    $hasBoot = @($task.Triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskBootTrigger' }).Count -gt 0
    $isS4U   = $task.Principal.LogonType -eq 'S4U'
    $info    = Get-ScheduledTaskInfo -TaskName $name

    # 0x41301 = dang chay, 0x41303 = chua tung chay.
    $running = $info.LastTaskResult -eq 267009
    $never   = $info.LastTaskResult -eq 267011

    if (-not $hasBoot) { Say-Missing "$name - THIEU trigger AtStartup, se khong tu chay sau khi mat dien" }
    if (-not $isS4U)   { Say-Missing "$name - LogonType la $($task.Principal.LogonType), khong phai S4U: se khong chay khi khong ai dang nhap" }
    if ($never)        { Say-Missing "$name - chua tung chay (LastTaskResult 0x41303)" }

    if ($hasBoot -and $isS4U -and -not $never -and -not $wasOff) {
        $tail = if ($running) { 'dang chay' } else { "lan chay cuoi $($info.LastRunTime)" }
        Say-Ok "$name - AtStartup + S4U, $tail"
    }
}

Write-Host ''
Write-Host '== O dia =='

$drive = Get-PSDrive -Name C
$freeGb = [math]::Round($drive.Free / 1GB, 1)
if ($freeGb -lt 15) {
    Say-Missing "C: chi con $freeGb GB - Chrome profile va anh tai ve se an het. Don truoc khi chay dai ngay."
} elseif ($freeGb -lt 30) {
    Say-Note "C: con $freeGb GB - du chay nhung nen theo doi."
} else {
    Say-Ok "C: con $freeGb GB"
}

Write-Host ''
Write-Host '== Con lai phai lam tay =='
Write-Host '  1. BIOS: Restore on AC Power Loss = Power On.  Windows khong dat duoc muc nay.'
Write-Host '     Mat dien xong ma thieu no thi may nam im va moi thu tren deu vo nghia.'
Write-Host '  2. Reboot thu mot lan, roi tu Mac kiem lai bang:  zsh scripts/check-runner-host.sh'
Write-Host '     Chay duoc het ma khong ai dang nhap vao PC thi moi goi la chay co dinh.'
Write-Host ''

if ($DryRun) {
    Write-Host "DryRun: khong doi gi.  $script:missing muc can xu ly."
} else {
    Write-Host "Xong: da sua $script:changed muc, con $script:missing muc can xu ly tay."
}
if ($script:missing -gt 0) { exit 1 }
