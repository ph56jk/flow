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


class TrelloConfig(BaseModel):
    api_key: str = ""
    token: str = ""
    board_id: str = ""
    card_id: str = ""
    list_id: str = ""
    upload_mode: str = "file"
    set_cover: bool = True
    upscale_to_2k: bool = True
    updated_at: str = ""


class EtsyConfig(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    user_id: str = ""
    shop_id: str = ""
    taxonomy_id: str = ""
    shipping_profile_id: str = ""
    return_policy_id: str = ""
    readiness_state_id: str = ""
    quantity: int = 1
    price: str = "9.99"
    who_made: str = "i_did"
    when_made: str = "made_to_order"
    is_supply: bool = False
    should_auto_renew: bool = False
    updated_at: str = ""


class EtsyAccount(BaseModel):
    # One additional Etsy account in the multi-account fleet. The DEFAULT account
    # (slug == "") is NOT stored here — it is the existing global TrelloConfig +
    # EtsyConfig, so legacy single-account state keeps working untouched. Entries
    # in this list are ONLY the extra accounts (shop2, shop3, …), each with its
    # own Trello board (image/info source) and its own Etsy shop.
    slug: str = ""
    label: str = ""
    trello_board_id: str = ""
    trello_list_id: str = ""
    etsy_shop_id: str = ""
    enabled: bool = True
    updated_at: str = ""


class IntegrationConfig(BaseModel):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_image_model: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    playwright_browsers_path: str = ""
    updated_at: str = ""


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
    return f"https://labs.google/fx/vi/tools/flow/project/{quote(project_id, safe='')}"


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
    trello_config: TrelloConfig = Field(default_factory=TrelloConfig)
    etsy_config: EtsyConfig = Field(default_factory=EtsyConfig)
    etsy_accounts: List[EtsyAccount] = Field(default_factory=list)
    integration_config: IntegrationConfig = Field(default_factory=IntegrationConfig)
    flow_profile_quota_blocked_until: Dict[str, float] = Field(default_factory=dict)
    flow_profile_agent_retry_error_counts: Dict[str, int] = Field(default_factory=dict)
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


class TrelloConfigUpdateRequest(BaseModel):
    api_key: str = ""
    token: str = ""
    board_id: str = ""
    card_id: str = ""
    list_id: str = ""
    upload_mode: str = "file"
    set_cover: bool = True
    upscale_to_2k: bool = True
    clear_credentials: bool = False
    persist_to_env: bool = False  # also write to .env.local so creds survive state resets


class EtsyConfigUpdateRequest(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    user_id: str = ""
    shop_id: str = ""
    taxonomy_id: str = ""
    shipping_profile_id: str = ""
    return_policy_id: str = ""
    readiness_state_id: str = ""
    quantity: int = 1
    price: str = "9.99"
    who_made: str = "i_did"
    when_made: str = "made_to_order"
    is_supply: bool = False
    should_auto_renew: bool = False
    clear_credentials: bool = False


class EtsyAccountUpsertRequest(BaseModel):
    slug: str = ""
    label: str = ""
    trello_board_id: str = ""
    trello_list_id: str = ""
    etsy_shop_id: str = ""
    enabled: bool = True


class EtsyAccountDeleteRequest(BaseModel):
    slug: str = ""


class ResetReadyTrelloRequest(BaseModel):
    trello_board_id: str = ""
    trello_list_id: str = ""


class EtsySectionSyncRequest(BaseModel):
    trello_board_id: str = ""
    trello_list_id: str = ""
    include_list_ids: List[str] = Field(default_factory=list)
    include_list_names: List[str] = Field(default_factory=list)
    exclude_list_names: List[str] = Field(default_factory=list)
    dry_run: bool = True
    create_missing: bool = False
    tracking_only: bool = False
    replace_tracking: bool = False
    max_sections: int = 100


class IntegrationConfigUpdateRequest(BaseModel):
    gemini_api_key: str = ""
    gemini_model: str = ""
    gemini_image_model: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    playwright_browsers_path: str = ""
    clear_gemini_api_key: bool = False
    clear_telegram_bot_token: bool = False


class AutomationModuleRequest(BaseModel):
    id: str = ""
    type: str = "custom"
    title: str = ""
    detail: str = ""
    enabled: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)


class AutomationEdgeRequest(BaseModel):
    source: str = ""
    target: str = ""
    condition: str = "success"


class AutomationGraphRequest(BaseModel):
    version: int = 1
    modules: List[AutomationModuleRequest] = Field(default_factory=list)
    edges: List[AutomationEdgeRequest] = Field(default_factory=list)
    selected_module_id: str = ""


class EtsyVariationValueRequest(BaseModel):
    value: str = ""
    price: str = ""
    quantity: int = 0
    is_enabled: bool = True


class EtsyVariationRequest(BaseModel):
    property_name: str = ""
    property_id: int = 0
    scale_id: int = 0
    values: List[EtsyVariationValueRequest] = Field(default_factory=list)


class EtsyAttributeRequest(BaseModel):
    property_id: int = 0
    scale_id: int = 0
    value_ids: List[int] = Field(default_factory=list)
    values: List[str] = Field(default_factory=list)


class CreateJobRequest(BaseModel):
    type: str
    prompt: str = ""
    title: str = ""
    timeout_s: int = 0
    source_job_id: str = ""
    model: str = ""
    image_engine: str = "google_flow"
    aspect: str = "landscape"
    count: int = 1
    start_image_path: str = ""
    reference_image_paths: List[str] = Field(default_factory=list)
    reference_image_roles: List[str] = Field(default_factory=list)
    reference_media_names: List[str] = Field(default_factory=list)
    media_id: str = ""
    workflow_id: str = ""
    telegram_chat_id: str = ""
    telegram_enabled: bool = True
    trello_enabled: bool = True
    etsy_enabled: bool = False
    amazon_enabled: bool = False
    flow_agent_enabled: bool = True
    flow_agent_auto_approve: bool = True
    automation_graph: AutomationGraphRequest = Field(default_factory=AutomationGraphRequest)
    trello_board_id: str = ""
    trello_card_id: str = ""
    trello_list_id: str = ""
    trello_attachment_ids: List[str] = Field(default_factory=list)
    trello_source_card_id: str = ""
    trello_source_attachment_ids: List[str] = Field(default_factory=list)
    trello_set_cover: bool = True
    etsy_listing_title: str = ""
    etsy_listing_description: str = ""
    etsy_listing_tags: List[str] = Field(default_factory=list)
    etsy_listing_materials: List[str] = Field(default_factory=list)
    etsy_browser_copy_enabled: bool = False
    etsy_account_id: str = ""
    etsy_template_listing_url: str = ""
    etsy_template_listing_id: str = ""
    etsy_section_name: str = ""
    etsy_listing_sku: str = ""
    etsy_vm_image_dir: str = ""
    etsy_keep_color_chart: bool = True
    etsy_delete_existing_images: bool = True
    etsy_price: str = ""
    etsy_quantity: int = 0
    etsy_taxonomy_id: str = ""
    etsy_shipping_profile_id: str = ""
    etsy_return_policy_id: str = ""
    etsy_readiness_state_id: str = ""
    etsy_publish: bool = False
    etsy_variations: List[EtsyVariationRequest] = Field(default_factory=list)
    etsy_attributes: List[EtsyAttributeRequest] = Field(default_factory=list)
    amazon_browser_copy_enabled: bool = False
    amazon_account_id: str = ""
    amazon_template_listing_url: str = ""
    amazon_template_listing_id: str = ""
    amazon_listing_title: str = ""
    amazon_listing_description: str = ""
    amazon_listing_sku: str = ""
    amazon_product_type: str = ""
    amazon_vm_image_dir: str = ""
    amazon_delete_existing_images: bool = True
    amazon_price: str = ""
    amazon_quantity: int = 0
    amazon_publish: bool = False
    prompt_source_row: int = 0
    prompt_product: str = ""
    prompt_product_key: str = ""
    prompt_index: str = ""
    prompt_notes: str = ""
    motion: str = ""
    position: str = ""
    resolution: str = "1080p"
    mask_x: float = 0.5
    mask_y: float = 0.5
    brush_size: int = 40


class PromptBatchItemRequest(BaseModel):
    row: int = 0
    active: bool = True
    used: bool = False
    prompt: str = ""
    product: str = ""
    product_key: str = ""
    product_name: str = ""
    index: str = ""
    notes: str = ""
    trello_card_id: str = ""
    trello_list_id: str = ""
    trello_attachment_ids: List[str] = Field(default_factory=list)
    trello_source_card_id: str = ""
    trello_source_attachment_ids: List[str] = Field(default_factory=list)


class PromptBatchRequest(BaseModel):
    job: CreateJobRequest = Field(default_factory=lambda: CreateJobRequest(type="image"))
    items: List[PromptBatchItemRequest] = Field(default_factory=list)
    title: str = ""
    limit: int = 40
    auto_trello: bool = False
    create_etsy_draft: bool = False
    etsy_only: bool = False
    run_until_empty: bool = False
    continuous: bool = False
    poll_interval_s: int = 30


class ExtensionAutoTrelloPlanRequest(BaseModel):
    batch: PromptBatchRequest = Field(default_factory=PromptBatchRequest)


class ExtensionAutoTrelloImageRequest(BaseModel):
    data_url: str = ""
    url: str = ""
    name: str = ""
    mime_type: str = ""


class ExtensionAutoTrelloArchiveRequest(BaseModel):
    job: CreateJobRequest = Field(default_factory=lambda: CreateJobRequest(type="image"))
    item: Dict[str, Any] = Field(default_factory=dict)
    images: List[ExtensionAutoTrelloImageRequest] = Field(default_factory=list)
    extension_result: Dict[str, Any] = Field(default_factory=dict)


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


class StoryboardPlanRequest(BaseModel):
    script: str = ""
    style: str = ""
    must_include: str = ""
    avoid: str = ""
    audience: str = ""
    aspect: str = "landscape"
    scene_count: int = 0


class UserAssistantRequest(BaseModel):
    question: str = ""
    context: str = ""


class FlowOperatorRequest(BaseModel):
    instruction: str = ""
    context: str = ""
    run_mode: str = "plan"


class MasterBotRequest(BaseModel):
    instruction: str = ""
    context: str = ""
    run_mode: str = "plan"
    auto_trello: bool = False
    continuous: bool = False
    limit: int = 0
    create_etsy_draft: bool = False


class StoryboardScene(BaseModel):
    index: int = 1
    title: str = ""
    beat: str = ""
    image_prompt: str = ""
    continuity: str = ""


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
