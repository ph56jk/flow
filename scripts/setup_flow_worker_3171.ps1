param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$workerRoot = Join-Path $root "data\workers\3171"
$workerProfiles = Join-Path $workerRoot "flow-profiles"
$workerEnv = Join-Path $root ".env.worker-3171.local"
$sourceEnv = Join-Path $root ".env.local"

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Key
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        return ""
    }
    $matched = Get-Content -LiteralPath $Path | Where-Object {
        $_ -match "^\s*$([regex]::Escape($Key))\s*="
    } | Select-Object -Last 1
    if (-not $matched) {
        return ""
    }
    return (($matched -split "=", 2)[1]).Trim().Trim('"').Trim("'")
}

if (-not (Test-Path -LiteralPath $sourceEnv)) {
    throw "Khong tim thay .env.local cua Flow chinh."
}

$existingProfileDirs = Get-EnvValue -Path $workerEnv -Key "FLOW_CHROME_PROFILE_DIRS"
$existingProfileProjects = Get-EnvValue -Path $workerEnv -Key "FLOW_CHROME_PROFILE_PROJECTS"
$workerProjectId = Get-EnvValue -Path $workerEnv -Key "ERP_PROJECT_ID"
if ([string]::IsNullOrWhiteSpace($workerProjectId)) {
    $workerProjectId = Get-EnvValue -Path $sourceEnv -Key "ERP_PROJECT_ID"
}
$workerStatus = Get-EnvValue -Path $workerEnv -Key "ERP_STATUS_ID"

New-Item -ItemType Directory -Path $workerRoot, $workerProfiles -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $workerRoot "uploads"), (Join-Path $workerRoot "downloads") -Force | Out-Null

$excludedEnvKeys = @(
    "ERP_PROJECT_ID",
    "ERP_TASK_ID",
    "ERP_STATUS_ID",
    "FLOW_PUBLIC_URL",
    "FLOW_DATA_DIR",
    "FLOW_ENV_FILE",
    "FLOW_WORKER_NAME",
    "FLOW_CHROME_PROFILE_DIRS",
    "FLOW_PROFILE_DIRS",
    "GOOGLE_FLOW_PROFILE_DIRS",
    "FLOW_CHROME_PROFILE_PROJECTS",
    "FLOW_PROFILE_PROJECTS",
    "GOOGLE_FLOW_PROFILE_PROJECTS"
)
$workerEnvLines = @(
    "# Worker 3171. Generated from .env.local; do not commit.",
    "# Flow v2 is restricted to PROJ-0049; assign a source status and Flow browser profiles below."
)
foreach ($line in Get-Content -LiteralPath $sourceEnv) {
    if ($line -match "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=") {
        if ($Matches[1] -in $excludedEnvKeys) {
            continue
        }
    }
    $workerEnvLines += $line
}
$workerEnvLines += @(
    "",
    "ERP_PROJECT_ID=$workerProjectId",
    "ERP_TASK_ID=",
    "ERP_STATUS_ID=$workerStatus",
    "FLOW_CHROME_PROFILE_DIRS=$existingProfileDirs",
    "FLOW_CHROME_PROFILE_PROJECTS=$existingProfileProjects"
)
Set-Content -LiteralPath $workerEnv -Value $workerEnvLines -Encoding UTF8

$statePath = Join-Path $workerRoot "state.json"
if (-not (Test-Path -LiteralPath $statePath)) {
    $sourceStatePath = Join-Path $root "data\state.json"
    $skills = @()
    if (Test-Path -LiteralPath $sourceStatePath) {
        $sourceState = Get-Content -LiteralPath $sourceStatePath -Raw | ConvertFrom-Json
        $skills = @($sourceState.skills)
    }
    $state = [ordered]@{
        config = [ordered]@{
            project_id = ""
            project_name = "Worker 3"
            project_url = ""
            active_workflow_id = ""
            headless = $false
            cdp_url = ""
            generation_timeout_s = 300
            poll_interval_s = 5.0
            output_dir = ""
        }
        erp_config = [ordered]@{
            api_key = ""
            api_secret = ""
            base_url = "https://erp.havigroup.llc"
            project_id = $workerProjectId
            task_id = ""
            status = $workerStatus
            updated_at = ""
        }
        integration_config = [ordered]@{
            gemini_api_key = ""
            gemini_model = "gemini-2.5-flash"
            telegram_bot_token = ""
            telegram_chat_id = ""
            playwright_browsers_path = ""
            updated_at = ""
        }
        flow_profile_quota_blocked_until = @{}
        flow_profile_agent_retry_error_counts = @{}
        jobs = @()
        skills = $skills
    }
    $state | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $statePath -Encoding UTF8
}

Write-Host "Worker 3171 setup xong. Cau hinh account va project nam trong .env.worker-3171.local."
