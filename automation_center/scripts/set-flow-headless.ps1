# Bat/tat che do headless cua Flow v2 tren host Windows.
#
#   powershell -File set-flow-headless.ps1            # bat headless (mac dinh)
#   powershell -File set-flow-headless.ps1 -Off       # tat headless
#
# BAY: PUT /api/config dung lai AppConfig tu dau (service.py update_config), nen
# field nao khong gui se bi reset ve mac dinh.  Gui {"headless":true} khong thoi
# se XOA project_id vua chon.  Vi vay script doc config hien tai qua /api/state
# roi ghi lai nguyen ven, chi doi mot field.

param([switch]$Off)

$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8000'

$state = Invoke-RestMethod -Uri "$base/api/state" -TimeoutSec 20
$c = $state.config

if ([string]::IsNullOrWhiteSpace([string]$c.project_id)) {
    Write-Error 'project_id dang TRONG - hay dang nhap Google va chon Project truoc, neu khong ban chi dang khoa lai mot cau hinh rong.'
    exit 1
}

$target = -not $Off.IsPresent

$body = @{
    project_id           = [string]$c.project_id
    project_name         = [string]$c.project_name
    active_workflow_id   = [string]$c.active_workflow_id
    headless             = $target
    cdp_url              = [string]$c.cdp_url
    generation_timeout_s = [int]$c.generation_timeout_s
    poll_interval_s      = [double]$c.poll_interval_s
    output_dir           = [string]$c.output_dir
} | ConvertTo-Json

Invoke-RestMethod -Uri "$base/api/config" -Method Put -ContentType 'application/json' -Body $body -TimeoutSec 20 | Out-Null

$after = (Invoke-RestMethod -Uri "$base/api/state" -TimeoutSec 20).config
Write-Host ("headless   : {0}" -f $after.headless)
Write-Host ("project_id : {0}" -f $(if ([string]::IsNullOrWhiteSpace([string]$after.project_id)) { '(TRONG - HONG!)' } else { 'con nguyen' }))
