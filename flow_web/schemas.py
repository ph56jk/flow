from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote, urlparse
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AppConfig(BaseModel):
    project_id: str = ""
    project_name: str = ""
    project_url: str = ""
    active_workflow_id: str = ""
    headless: bool = False
    cdp_url: str = ""
    generation_timeout_s: int = 300
    poll_interval_s: float = 5.0
    output_dir: str = ""


def _model_dump_payload(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    if hasattr(model, "dict"):
        return model.dict()
    return dict(model or {})


def normalize_project_id(project_value: str) -> str:
    raw = str(project_value or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    candidate = parsed.path or raw if parsed.scheme and parsed.netloc else raw
    if "/project/" in candidate:
        candidate = candidate.split("/project/", 1)[1]

    candidate = candidate.split("?", 1)[0].split("#", 1)[0].strip().strip("/")
    if "/" in candidate:
        candidate = candidate.split("/", 1)[0].strip()

    try:
        candidate = unquote(candidate)
    except Exception:
        pass

    return candidate


def canonical_project_url(project_value: str) -> str:
    project_id = normalize_project_id(project_value)
    if not project_id:
        return ""
    return f"https://labs.google/fx/tools/flow/project/{quote(project_id, safe='')}"


def normalized_app_config(config: Any) -> AppConfig:
    payload = _model_dump_payload(config)
    project_id = normalize_project_id(payload.get("project_id", "") or payload.get("project_url", ""))
    payload["project_id"] = project_id
    payload["project_url"] = canonical_project_url(project_id)
    payload["project_name"] = str(payload.get("project_name", "")).strip()
    payload["active_workflow_id"] = str(payload.get("active_workflow_id", "")).strip()
    payload["cdp_url"] = str(payload.get("cdp_url", "")).strip()
    payload["output_dir"] = str(payload.get("output_dir", "")).strip()
    return AppConfig(**payload)


class JobLog(BaseModel):
    at: str = Field(default_factory=utc_now)
    message: str


class JobArtifact(BaseModel):
    label: str = ""
    media_name: str = ""
    workflow_id: str = ""
    url: str = ""
    local_path: str = ""
    public_url: str = ""
    mime_type: str = ""
    prompt: str = ""
    dimensions: Dict[str, Any] = Field(default_factory=dict)


class JobRecoveryAction(BaseModel):
    id: str
    label: str
    description: str = ""


class JobErrorSnapshot(BaseModel):
    category: str = "unknown"
    label: str = ""
    title: str = ""
    message: str = ""
    is_known: bool = False
    actions: List[JobRecoveryAction] = Field(default_factory=list)


class JobRetrySnapshot(BaseModel):
    is_retry: bool = False
    source_job_id: str = ""
    source_job_title: str = ""
    source_job_type: str = ""
    source_job_status: str = ""
    source_job_created_at: str = ""


class JobReplayField(BaseModel):
    label: str = ""
    value: str = ""


class JobReplaySnapshot(BaseModel):
    available: bool = False
    reason: str = ""
    reason_label: str = ""
    summary: str = ""
    group_key: str = ""
    group_label: str = ""
    previous_status: str = ""
    previous_status_label: str = ""
    last_log_at: str = ""
    last_log_message: str = ""
    interrupted_at: str = ""
    prompt_excerpt: str = ""
    input_fields: List[JobReplayField] = Field(default_factory=list)
    recovery_input: Dict[str, Any] = Field(default_factory=dict)
    cleared_at: str = ""


class JobProgressHint(BaseModel):
    stage: str = ""
    detail: str = ""
    remote_status: str = ""
    updated_at: str = ""


class JobProgressMilestone(BaseModel):
    key: str = ""
    label: str = ""
    status: str = "pending"
    detail: str = ""
    at: str = ""


class JobProgressSnapshot(BaseModel):
    stage: str = ""
    stage_label: str = ""
    detail: str = ""
    is_active: bool = False
    is_terminal: bool = False
    last_signal_at: str = ""
    last_signal_message: str = ""
    milestones: List[JobProgressMilestone] = Field(default_factory=list)


class JobRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    type: str
    status: str = "queued"
    title: str = ""
    input: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[JobArtifact] = Field(default_factory=list)
    logs: List[JobLog] = Field(default_factory=list)
    error: str = ""
    error_snapshot: JobErrorSnapshot = Field(default_factory=JobErrorSnapshot)
    source_job_id: str = ""
    retry_snapshot: JobRetrySnapshot = Field(default_factory=JobRetrySnapshot)
    replay_snapshot: JobReplaySnapshot = Field(default_factory=JobReplaySnapshot)
    progress_hint: JobProgressHint = Field(default_factory=JobProgressHint)
    progress_snapshot: JobProgressSnapshot = Field(default_factory=JobProgressSnapshot)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class SkillRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    summary: str = ""
    skill_text: str = ""
    source_repo: str = ""
    source_path: str = ""
    source_url: str = ""
    is_builtin: bool = False
    type: str = "video"
    prompt: str = ""
    aspect: str = "landscape"
    count: int = 1
    reference_media_names: List[str] = Field(default_factory=list)
    media_id: str = ""
    workflow_id: str = ""
    motion: str = ""
    position: str = ""
    resolution: str = "1080p"
    mask_x: float = 0.5
    mask_y: float = 0.5
    brush_size: int = 40
    source_job_id: str = ""
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class PublicSkillSnapshot(BaseModel):
    id: str
    name: str = ""
    summary: str = ""
    source_repo: str = ""
    source_path: str = ""
    source_url: str = ""
    is_builtin: bool = False
    type: str = "video"
    prompt: str = ""
    aspect: str = "landscape"
    count: int = 1


class StateSnapshot(BaseModel):
    config: AppConfig = Field(default_factory=AppConfig)
    jobs: List[JobRecord] = Field(default_factory=list)
    skills: List[SkillRecord] = Field(default_factory=list)


class ConfigUpdateRequest(BaseModel):
    project_id: str = ""
    project_name: str = ""
    active_workflow_id: str = ""
    headless: bool = False
    cdp_url: str = ""
    generation_timeout_s: int = 300
    poll_interval_s: float = 5.0
    output_dir: str = ""


class CreateJobRequest(BaseModel):
    type: str
    prompt: str = ""
    title: str = ""
    timeout_s: int = 0
    source_job_id: str = ""
    aspect: str = "landscape"
    count: int = 1
    start_image_path: str = ""
    reference_media_names: List[str] = Field(default_factory=list)
    media_id: str = ""
    workflow_id: str = ""
    motion: str = ""
    position: str = ""
    resolution: str = "1080p"
    mask_x: float = 0.5
    mask_y: float = 0.5
    brush_size: int = 40


class DownloadRequest(BaseModel):
    artifact_index: int = 0


class ArtifactOpenRequest(BaseModel):
    artifact_index: int = 0
    target: str = "best"


class ReplayCleanupRequest(BaseModel):
    job_ids: List[str] = Field(default_factory=list)


class CleanupRequest(BaseModel):
    scope: str = ""


class SkillCreateRequest(BaseModel):
    name: str = ""
    summary: str = ""
    skill_text: str = ""
    source_repo: str = ""
    source_path: str = ""
    source_url: str = ""
    is_builtin: bool = False
    type: str = "video"
    prompt: str = ""
    aspect: str = "landscape"
    count: int = 1
    reference_media_names: List[str] = Field(default_factory=list)
    media_id: str = ""
    workflow_id: str = ""
    motion: str = ""
    position: str = ""
    resolution: str = "1080p"
    mask_x: float = 0.5
    mask_y: float = 0.5
    brush_size: int = 40
    source_job_id: str = ""


class SkillImportRequest(BaseModel):
    url: str = ""
    command: str = ""
    name: str = ""
    summary: str = ""
    skills: List[str] = Field(default_factory=list)


class PromptCreateRequest(BaseModel):
    mode: str = "video"
    brief: str = ""
    style: str = ""
    must_include: str = ""
    avoid: str = ""
    audience: str = ""
    aspect: str = ""


class PromptAssistantSnapshot(BaseModel):
    ready: bool = False
    configured: bool = False
    engine: str = "local"
    engine_label: str = ""
    model: str = ""
    skill_count: int = 0
    image_skill_count: int = 0
    video_skill_count: int = 0
    prompt_skill_count: int = 0
    source_url: str = ""
    headline: str = ""
    summary: str = ""
    sample_skill_names: List[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    file_name: str
    saved_path: str
    public_url: str


class AuthStatus(BaseModel):
    authenticated: bool = False


class ProjectEntry(BaseModel):
    id: str
    name: str = ""
    url: str = ""
    is_active: bool = False


class WorkspaceJobCounts(BaseModel):
    total: int = 0
    active: int = 0
    completed: int = 0
    failed: int = 0


class WorkspaceSnapshot(BaseModel):
    project_id: str = ""
    project_name: str = ""
    project_url: str = ""
    active_workflow_id: str = ""
    authenticated: bool = False
    saved_project_count: int = 0
    job_counts: WorkspaceJobCounts = Field(default_factory=WorkspaceJobCounts)


class InterruptedReplayItem(BaseModel):
    job_id: str
    title: str = ""
    job_type: str = ""
    job_type_label: str = ""
    summary: str = ""
    previous_status: str = ""
    previous_status_label: str = ""
    created_at: str = ""
    interrupted_at: str = ""
    last_log_at: str = ""
    last_log_message: str = ""
    prompt_excerpt: str = ""
    input_fields: List[JobReplayField] = Field(default_factory=list)
    can_retry: bool = False
    can_cleanup: bool = False


class InterruptedReplayGroup(BaseModel):
    key: str
    label: str = ""
    description: str = ""
    item_count: int = 0
    items: List[InterruptedReplayItem] = Field(default_factory=list)


class InterruptedReplayPack(BaseModel):
    has_items: bool = False
    total_items: int = 0
    groups: List[InterruptedReplayGroup] = Field(default_factory=list)
    cleanup_note: str = ""


class OutputShelfItem(BaseModel):
    job_id: str
    artifact_index: int = 0
    title: str = ""
    job_title: str = ""
    job_type: str = ""
    job_type_label: str = ""
    created_at: str = ""
    media_id: str = ""
    workflow_id: str = ""
    source_url: str = ""
    local_path: str = ""
    local_file_url: str = ""
    local_exists: bool = False
    preview_url: str = ""
    mime_type: str = ""
    prompt: str = ""
    dimensions: Dict[str, Any] = Field(default_factory=dict)


class OutputShelfSnapshot(BaseModel):
    has_items: bool = False
    total_items: int = 0
    job_count: int = 0
    summary: str = ""
    items: List[OutputShelfItem] = Field(default_factory=list)


class ProjectHealthSignal(BaseModel):
    key: str = ""
    tone: str = "neutral"
    label: str = ""
    detail: str = ""
    status_label: str = ""


class ProjectHealthTimelineEntry(BaseModel):
    key: str = ""
    tone: str = "neutral"
    title: str = ""
    detail: str = ""
    at: str = ""


class ProjectHealthSnapshot(BaseModel):
    visible: bool = False
    status_label: str = ""
    headline: str = ""
    summary: str = ""
    last_activity_at: str = ""
    trust_signals: List[ProjectHealthSignal] = Field(default_factory=list)
    timeline: List[ProjectHealthTimelineEntry] = Field(default_factory=list)


class CleanupItemSnapshot(BaseModel):
    key: str = ""
    label: str = ""
    detail: str = ""
    path_hint: str = ""
    bytes: int = 0
    status: str = "safe"
    status_label: str = ""


class CleanupGroupSnapshot(BaseModel):
    key: str = ""
    label: str = ""
    action_label: str = ""
    summary: str = ""
    empty_label: str = ""
    safe_count: int = 0
    safe_bytes: int = 0
    protected_count: int = 0
    protected_bytes: int = 0
    notes: List[str] = Field(default_factory=list)
    safe_items: List[CleanupItemSnapshot] = Field(default_factory=list)
    protected_items: List[CleanupItemSnapshot] = Field(default_factory=list)


class CleanupAssistantSnapshot(BaseModel):
    visible: bool = False
    headline: str = ""
    summary: str = ""
    total_safe_count: int = 0
    total_safe_bytes: int = 0
    protected_count: int = 0
    protected_bytes: int = 0
    groups: List[CleanupGroupSnapshot] = Field(default_factory=list)
