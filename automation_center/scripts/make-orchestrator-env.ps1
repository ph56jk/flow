# Sinh runner\orchestrator.env NGAY TREN MAY TRUNG TAM.
#
# Ly do co script nay: ba gia tri (AUTOMATION_RUNNER_SECRET va cap Cloudflare
# Access Service Token) dung chung voi content-image-runner va da nam trong
# runner\.env cua may nay.  Chep tay nghia la chung di qua man hinh, clipboard
# va lich su lenh.  Script doc thang tu file cu, ghi thang sang file moi, va
# KHONG in bat ky gia tri nao ra stdout.
#
# Mac dinh script KHONG hoi gi ca: agent goi model qua Codex CLI da dang nhap
# san tren may nay, nen khong co khoa API nao phai cat o dau.  Script tu tim
# codex.exe va ghi duong dan tuyet doi vao CODEX_BIN -- Scheduled Task chay
# kieu S4U co PATH hep hon phien dang nhap.
#
# Muon di duong HTTP cua OpenAI thay vi CLI thi them -KhoaOpenAI: script hoi
# bang Read-Host -AsSecureString nen phim go khong hien len man hinh va khong
# vao lich su PowerShell.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File make-orchestrator-env.ps1
#
# ACL duoc sao chep nguyen tu runner\.env, nen file moi co dung mot pham vi
# doc nhu file cu chu khong phai mot pham vi tu doan.

param(
    # Ghi de file da co.  Mac dinh la khong.
    [switch] $Force,
    # Hoi OPENAI_API_KEY va di duong HTTP thay vi Codex CLI.
    [switch] $KhoaOpenAI
)

$ErrorActionPreference = 'Stop'

$RunnerDir = Join-Path 'C:\HaviGroup\flow-v2' 'automation_center\runner'
$Source    = Join-Path $RunnerDir '.env'
$Example   = Join-Path $RunnerDir 'orchestrator-runner.env.example'
$Target    = Join-Path $RunnerDir 'orchestrator.env'

if (-not (Test-Path $Source))  { throw "Thieu $Source -- khong co cho lay AUTOMATION_RUNNER_SECRET." }
if (-not (Test-Path $Example)) { throw "Thieu $Example." }
if ((Test-Path $Target) -and -not $Force) {
    throw "$Target da ton tai.  Chay lai voi -Force neu that su muon ghi de."
}

function Read-EnvMap([string] $Path) {
    $map = @{}
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith('#')) { continue }
        $split = $trimmed.IndexOf('=')
        if ($split -lt 1) { continue }
        $map[$trimmed.Substring(0, $split).Trim()] = $trimmed.Substring($split + 1).Trim()
    }
    return $map
}

$old = Read-EnvMap $Source

# Nhung khoa duoc muon lai tu .env cu.  AUTOMATION_RUNNER_KEY thi KHONG: dung
# chung key voi content-image-runner se khien hai runner cuop viec cua nhau.
#
# Chi AUTOMATION_RUNNER_SECRET la bat buoc.  Cap Access Service Token la tuy
# chon that su -- orchestrator_runner.py chi gan hai header ay khi ca hai deu co
# gia tri (dong 119), va neu Access chan thi no bao thang bang mot cau ro rang.
# Bat buoc chung o day nghia la chan nguoi dung vi mot thu ho khong can.
$BatBuoc = 'AUTOMATION_RUNNER_SECRET'
$TuyChon = @('CF_ACCESS_CLIENT_ID', 'CF_ACCESS_CLIENT_SECRET')

if ([string]::IsNullOrWhiteSpace($old[$BatBuoc])) {
    throw "runner\.env khong co gia tri cho $BatBuoc."
}

$moi = @{ $BatBuoc = $old[$BatBuoc] }

if ($KhoaOpenAI) {
    $secure = Read-Host -Prompt 'OPENAI_API_KEY (go xong bam Enter; man hinh khong hien)' -AsSecureString
    $openai = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    if ([string]::IsNullOrWhiteSpace($openai)) {
        throw 'De trong -- run-orchestrator-runner.ps1 se thoat voi ma 78.'
    }
    $moi['AGENT_MODEL_PROVIDER'] = 'openai'
    $moi['OPENAI_API_KEY']       = $openai
    $duongGoi = 'duong HTTP, khoa hoi truc tiep'
} else {
    # Codex phai co THAT o day chu khong phai 'chac la co': thieu no thi
    # run-orchestrator-runner.ps1 thoat 78 moi 5 phut va log chi noi mot dong.
    $codex = if (-not [string]::IsNullOrWhiteSpace($env:CODEX_BIN)) { $env:CODEX_BIN }
             else { (Get-Command codex -ErrorAction SilentlyContinue).Source }
    if ([string]::IsNullOrWhiteSpace($codex) -or -not (Test-Path -LiteralPath $codex)) {
        throw 'Khong tim thay codex CLI tren may nay. Cai no, hoac chay lai voi -KhoaOpenAI.'
    }
    $moi['AGENT_MODEL_PROVIDER'] = 'codex'
    $moi['CODEX_BIN']            = $codex
    $duongGoi = "Codex CLI tai $codex"
}
# Khoa tuy chon nao co gia tri thi chep sang; khong co thi de nguyen dong trong
# cua file mau, chu khong ghi de bang chuoi rong.
$daChep = @()
foreach ($ten in $TuyChon) {
    if (-not [string]::IsNullOrWhiteSpace($old[$ten])) {
        $moi[$ten] = $old[$ten]
        $daChep += $ten
    }
}

# Di tu file mau chu khong tu mot danh sach chep tay: them khoa moi vao mau thi
# file sinh ra co ngay, khong phai nho sua hai cho.
$ra = foreach ($line in Get-Content -LiteralPath $Example -Encoding UTF8) {
    $trimmed = $line.Trim()
    if ($trimmed.Length -eq 0 -or $trimmed.StartsWith('#')) { $line; continue }
    $split = $trimmed.IndexOf('=')
    if ($split -lt 1) { $line; continue }
    $name = $trimmed.Substring(0, $split).Trim()
    if ($moi.ContainsKey($name)) { "$name=$($moi[$name])" } else { $line }
}

# Khong BOM: run-orchestrator-runner.ps1 doc bang -Encoding UTF8 va mot BOM se
# dinh vao ten khoa dau tien, bien AUTOMATION_CENTER_URL thanh mot khoa la.
[IO.File]::WriteAllLines($Target, $ra, (New-Object Text.UTF8Encoding($false)))

# ACL y het file cu, khong tu doan mot bo quyen moi.
Set-Acl -Path $Target -AclObject (Get-Acl -Path $Source)

Write-Host "Da ghi $Target"
Write-Host "Muon lai tu .env: $((@($BatBuoc) + $daChep) -join ', ')"
Write-Host "Duong goi model: $duongGoi"
$bo = @($TuyChon | Where-Object { $daChep -notcontains $_ })
if ($bo.Count -gt 0) {
    Write-Host "Khong co trong .env nen de trong: $($bo -join ', ')"
    Write-Host "  (runner chi gan header Access khi ca hai deu co gia tri;"
    Write-Host "   neu Cloudflare Access chan thi log se noi thang ra)"
}
Write-Host "Kiem lai neu may nay khac may mau: AGENT_REPO_DIR, AGENT_TEST_COMMAND"
