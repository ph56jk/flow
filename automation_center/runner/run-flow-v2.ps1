# Wrapper khởi động Flow v2 local trên host Windows (Scheduled Task).
# Flow chỉ lắng nghe 127.0.0.1 — không bao giờ expose ra Internet.

$ErrorActionPreference = 'Stop'

$RepoRoot = 'C:\HaviGroup\flow-v2'
$Python   = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$LogDir   = 'C:\HaviGroup\logs'

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location -LiteralPath $RepoRoot

$env:PYTHONUNBUFFERED = '1'
# Flow ghi log tieng Viet; console cp1252 se gay UnicodeEncodeError.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

& $Python -m uvicorn flow_web.main:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
