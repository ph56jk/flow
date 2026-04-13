from __future__ import annotations

import asyncio
import ctypes
import json
import logging
import os
import random
import re
import shlex
import shutil
import subprocess
import time
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Dict, List

from fastapi import HTTPException, UploadFile

from .messages import humanize_flow_error
from .paths import DOWNLOADS_DIR, UPLOADS_DIR, ensure_app_dirs
from .schemas import (
    AppConfig,
    ArtifactOpenRequest,
    AuthStatus,
    CleanupAssistantSnapshot,
    CleanupGroupSnapshot,
    CleanupItemSnapshot,
    CleanupRequest,
    ConfigUpdateRequest,
    CreateJobRequest,
    DownloadRequest,
    InterruptedReplayGroup,
    InterruptedReplayItem,
    InterruptedReplayPack,
    JobArtifact,
    ProjectHealthSignal,
    ProjectHealthSnapshot,
    ProjectHealthTimelineEntry,
    JobRecord,
    JobRetrySnapshot,
    OutputShelfItem,
    OutputShelfSnapshot,
    PromptAssistantSnapshot,
    PromptCreateRequest,
    ProjectEntry,
    ReplayCleanupRequest,
    PublicSkillSnapshot,
    SkillCreateRequest,
    SkillImportRequest,
    SkillRecord,
    WorkspaceJobCounts,
    WorkspaceSnapshot,
    canonical_project_url,
    normalize_project_id,
    normalized_app_config,
)
from .store import StateStore


def _model_dump(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def _parse_iso_datetime(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class FlowWebService:
    MAX_OUTPUT_SHELF_ITEMS = 6
    PROJECT_HEALTH_TIMELINE_LIMIT = 4
    PROJECT_HEALTH_RECENCY_DAYS = 14
    CLEANUP_PREVIEW_LIMIT = 3
    CLEANUP_UPLOAD_GRACE_HOURS = 2
    CLEANUP_DOWNLOAD_RETENTION_DAYS = 7
    CLEANUP_HISTORY_RETENTION_DAYS = 14
    SKILL_TEXT_EXTENSIONS = {".sh", ".md", ".txt", ".skill", ".cfg", ".ini", ".env"}
    MEDIA_SKILL_REPO = "inference-sh/skills"
    MEDIA_SKILL_SOURCE_URL = "https://github.com/inference-sh/skills"
    MEDIA_SKILL_PATH_PATTERN = re.compile(r"^.+/SKILL\.md$", re.IGNORECASE)
    GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"
    GEMINI_TIMEOUT_S = 30
    DEFAULT_VIDEO_MODEL = "Veo 3.1 - Fast"
    DEFAULT_IMAGE_MODEL = "NARWHAL"
    IMAGE_MODEL_LABELS = {
        "NARWHAL": "Nano Banana 2",
        "IMAGEN_3": "Imagen 3",
    }
    IMAGE_MODEL_EDIT_VALUES = {
        "NARWHAL": "GEM_PIX_2",
        "IMAGEN_3": "IMAGEN_3",
    }
    VIDEO_MODEL_DISPLAY_ALIASES = {
        "veo 3.1 - fast": "Veo 3.1 - Fast",
        "veo 3.1 fast": "Veo 3.1 - Fast",
        "veo 3.1 - quality": "Veo 3.1 - Quality",
        "veo 3.1 quality": "Veo 3.1 - Quality",
        "veo 2 - fast": "Veo 2 - Fast",
        "veo 2 fast": "Veo 2 - Fast",
        "veo 2 - quality": "Veo 2 - Quality",
        "veo 2 quality": "Veo 2 - Quality",
        "veo 3.1 - fast [lower priority]": "Veo 3.1 - Fast [Lower Priority]",
    }
    IMAGE_MODEL_ALIASES = {
        "narwhal": "NARWHAL",
        "gem_pix_2": "NARWHAL",
        "nano banana": "NARWHAL",
        "nano banana 2": "NARWHAL",
        "imagen 3": "IMAGEN_3",
        "imagen3": "IMAGEN_3",
        "imagen_3": "IMAGEN_3",
    }
    REFERENCE_IMAGE_ROLES = ("base", "logo", "product", "reference")
    REFERENCE_IMAGE_ROLE_LABELS = {
        "base": "ảnh chính",
        "logo": "logo",
        "product": "sản phẩm",
        "reference": "tham chiếu",
    }
    PROMPT_SKILL_PREFIXES = (
        "guides/design/",
        "guides/photo/",
        "guides/prompting/",
        "guides/video/",
        "tools/image/",
        "tools/video/",
    )
    SUPPORTED_SKILL_TYPES = {
        "video",
        "image",
        "extend",
        "upscale",
        "camera_motion",
        "camera_position",
        "insert",
        "remove",
    }
    _FLOW_RUNTIME_PATCHED = False

    def __init__(self, store: StateStore) -> None:
        ensure_app_dirs()
        self.store = store
        self._tasks: Dict[str, asyncio.Task] = {}
        self._browser_session_lock = asyncio.Lock()
        self._shared_browser: Any | None = None

    async def close(self) -> None:
        async with self._browser_session_lock:
            await self._close_shared_browser()

    def get_state(self) -> Dict[str, Any]:
        snapshot = self.store.snapshot()
        return {
            "config": _model_dump(self._normalized_config(snapshot.config)),
            "jobs": snapshot.jobs,
            "skills": [self._public_skill_payload(skill) for skill in snapshot.skills],
        }

    def get_state_payload(self) -> Dict[str, Any]:
        base_state = self.get_state()
        snapshot = self.store.snapshot()
        auth = self.get_auth_status()
        projects = self.list_projects()
        workspace = self._workspace_snapshot(base_state["config"], auth, base_state["jobs"], projects)
        output_shelf = self._build_output_shelf(base_state["jobs"])
        replay_pack = self._build_replay_pack(base_state["jobs"])
        cleanup_assistant, _ = self._build_cleanup_assistant(base_state["config"], base_state["jobs"], output_shelf)
        return {
            **base_state,
            "projects": projects,
            "auth": auth,
            "workspace": workspace,
            "output_shelf": output_shelf,
            "replay_pack": replay_pack,
            "cleanup_assistant": cleanup_assistant,
            "project_health": self._build_project_health(base_state["config"], auth, base_state["jobs"], projects),
            "prompt_assistant": self._prompt_assistant_snapshot(snapshot.skills),
        }

    def _public_skill_payload(self, skill: SkillRecord) -> Dict[str, Any]:
        snapshot = PublicSkillSnapshot(
            id=skill.id,
            name=skill.name,
            summary=skill.summary,
            source_repo=skill.source_repo,
            source_path=skill.source_path,
            source_url=skill.source_url,
            is_builtin=skill.is_builtin,
            type=skill.type,
            prompt=skill.prompt,
            aspect=skill.aspect,
            count=skill.count,
        )
        return _model_dump(snapshot)

    async def update_config(self, request: ConfigUpdateRequest) -> AppConfig:
        project_id = self._normalize_project_id(request.project_id)
        config = AppConfig(
            project_id=project_id,
            project_name=request.project_name.strip(),
            project_url=self._project_url(project_id),
            active_workflow_id=request.active_workflow_id.strip(),
            headless=request.headless,
            cdp_url=request.cdp_url.strip(),
            generation_timeout_s=max(30, request.generation_timeout_s),
            poll_interval_s=max(1.0, request.poll_interval_s),
            output_dir=request.output_dir.strip(),
        )
        await self.store.replace_config(config)
        config = self._normalized_config(config)
        self._sync_project_to_flow_storage(config)
        return config

    def get_auth_status(self) -> AuthStatus:
        _, is_authenticated, _, _, _ = self._flow_modules()
        authenticated = False
        try:
            authenticated = bool(is_authenticated())
        except Exception:
            authenticated = False
        if not authenticated:
            authenticated = self._flow_profile_has_auth_cookies()
        return AuthStatus(authenticated=authenticated)

    def _flow_profile_has_auth_cookies(self) -> bool:
        try:
            from flow._storage import PROFILE_DIR
        except Exception:
            return False

        profile_dir = Path(PROFILE_DIR)
        candidates = [
            profile_dir / "Default" / "Cookies",
            profile_dir / "Default" / "Network" / "Cookies",
        ]
        for candidate in candidates:
            try:
                if candidate.exists() and candidate.stat().st_size > 0:
                    return True
            except OSError:
                continue
        return False

    async def logout_flow(self) -> Dict[str, Any]:
        snapshot = self.store.snapshot()
        config = self._normalized_config(snapshot.config)
        active_jobs = [job for job in snapshot.jobs if job.status in {"queued", "running", "polling"}]

        if active_jobs:
            raise HTTPException(
                status_code=409,
                detail="Đang có tác vụ chạy. Hãy chờ xong rồi đăng xuất Google Flow để tránh ngắt phiên giữa chừng.",
            )

        if config.cdp_url:
            raise HTTPException(
                status_code=400,
                detail="Phiên này đang dùng Chrome ngoài qua CDP. Hãy đăng xuất trực tiếp trong trình duyệt Chrome đó.",
            )

        from flow._storage import PROFILE_DIR, ensure_dirs

        profile_dir = Path(PROFILE_DIR)
        cookies_path = profile_dir / "Default" / "Cookies"
        had_session = cookies_path.exists() and cookies_path.stat().st_size > 0

        try:
            await self.close()
            if profile_dir.exists():
                shutil.rmtree(profile_dir)
            ensure_dirs()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Không thể xóa phiên Google Flow hiện tại. Nếu còn cửa sổ Chromium của Flow đang mở, hãy đóng nó rồi thử lại.",
            ) from exc

        return {
            "ok": True,
            "had_session": had_session,
            "auth": _model_dump(self.get_auth_status()),
        }

    async def open_flow_login_surface(self) -> Dict[str, Any]:
        self._assert_windows_interactive_browser_session("đăng nhập Google Flow")
        async with self._browser_session_lock:
            browser = await self._ensure_shared_browser()
            page = await self._open_login_flow_page(browser)
        return {
            "ok": True,
            "url": str(getattr(page, "url", "") or "https://labs.google/fx/vi/tools/flow"),
        }

    async def open_flow_project_surface(self) -> Dict[str, Any]:
        self._assert_windows_interactive_browser_session("mở project Google Flow")
        config = self._normalized_config(self.store.snapshot().config)
        target_url = self._project_url(config.project_id) if config.project_id else "https://labs.google/fx/vi/tools/flow"
        async with self._browser_session_lock:
            browser = await self._ensure_shared_browser()
            if config.project_id:
                await self._repair_placeholder_flow_tabs(browser, target_url)
                page = await self._acquire_fresh_flow_page(browser, target_url)
                await self._ensure_valid_flow_project_page(page, target_url)
                try:
                    await page.bring_to_front()
                except Exception:
                    pass
                await self._foreground_native_flow_window()
            else:
                page = await self._open_login_flow_page(browser)
        return {
            "ok": True,
            "url": str(getattr(page, "url", "") or target_url),
        }

    def list_projects(self) -> List[ProjectEntry]:
        _, _, load_projects, get_active_project, _ = self._flow_modules()
        projects = load_projects()
        active_id, _ = get_active_project()
        normalized_projects, changed = self._normalize_projects_payload(projects)
        normalized_active_id = self._normalize_project_id(active_id or "")

        if normalized_active_id and normalized_active_id not in normalized_projects:
            config = self._normalized_config(self.store.snapshot().config)
            normalized_projects[normalized_active_id] = {
                "name": config.project_name or "web-ui",
                "url": self._project_url(normalized_active_id),
            }
            changed = True

        if changed or normalized_active_id != (active_id or ""):
            self._save_project_registry(normalized_projects, normalized_active_id)

        return [
            ProjectEntry(
                id=project_id,
                name=payload.get("name", ""),
                url=payload.get("url", ""),
                is_active=project_id == normalized_active_id,
            )
            for project_id, payload in normalized_projects.items()
        ]

    def _workspace_snapshot(
        self,
        config: Dict[str, Any] | AppConfig,
        auth: AuthStatus,
        jobs: List[JobRecord],
        projects: List[ProjectEntry],
    ) -> WorkspaceSnapshot:
        normalized_config = self._normalized_config(config)
        active_jobs = sum(1 for job in jobs if job.status in {"queued", "running", "polling"})
        completed_jobs = sum(1 for job in jobs if job.status == "completed")
        failed_jobs = sum(1 for job in jobs if job.status in {"failed", "interrupted"})
        return WorkspaceSnapshot(
            project_id=normalized_config.project_id,
            project_name=normalized_config.project_name,
            project_url=normalized_config.project_url,
            active_workflow_id=normalized_config.active_workflow_id,
            authenticated=auth.authenticated,
            saved_project_count=len(projects),
            job_counts=WorkspaceJobCounts(
                total=len(jobs),
                active=active_jobs,
                completed=completed_jobs,
                failed=failed_jobs,
            ),
        )

    def _build_project_health(
        self,
        config: Dict[str, Any] | AppConfig,
        auth: AuthStatus,
        jobs: List[JobRecord],
        projects: List[ProjectEntry],
    ) -> ProjectHealthSnapshot:
        normalized_config = self._normalized_config(config)
        sorted_jobs = self._sorted_jobs_by_activity(jobs)
        last_activity_at = next((self._job_activity_at(job) for job in sorted_jobs if self._job_activity_at(job)), "")

        if not any([normalized_config.project_id, normalized_config.active_workflow_id, auth.authenticated, sorted_jobs]):
            return ProjectHealthSnapshot()

        signals = [
            self._build_project_signal(normalized_config, projects),
            self._build_auth_signal(auth, sorted_jobs),
            self._build_workflow_signal(normalized_config, sorted_jobs),
            self._build_local_artifact_signal(sorted_jobs),
        ]
        recent_jobs = self._recent_jobs(sorted_jobs, days=self.PROJECT_HEALTH_RECENCY_DAYS)
        timeline = self._build_project_health_timeline(normalized_config, auth, recent_jobs, sorted_jobs)
        status_label, headline, summary = self._project_health_overview(normalized_config, auth, signals, timeline)

        return ProjectHealthSnapshot(
            visible=True,
            status_label=status_label,
            headline=headline,
            summary=summary,
            last_activity_at=last_activity_at,
            trust_signals=signals,
            timeline=timeline,
        )

    def _build_project_signal(self, config: AppConfig, projects: List[ProjectEntry]) -> ProjectHealthSignal:
        project_id = str(config.project_id or "").strip()
        if not project_id:
            return ProjectHealthSignal(
                key="project",
                tone="warning",
                label="Chưa có project",
                detail="Workspace hiện chưa giữ mã project chuẩn, nên app chưa thể kết luận môi trường có sẵn để chạy tiếp.",
                status_label="Thiếu",
            )

        project_name = str(config.project_name or project_id).strip() or project_id
        if any(project.id == project_id for project in projects):
            detail = f"Project {project_name} đang được lưu chuẩn và vẫn xuất hiện trong thư viện project đã lưu."
        else:
            detail = f"Project {project_name} đang được lưu chuẩn trong workspace hiện tại."

        return ProjectHealthSignal(
            key="project",
            tone="positive",
            label="Project hợp lệ",
            detail=detail,
            status_label="Ổn",
        )

    def _build_auth_signal(self, auth: AuthStatus, jobs: List[JobRecord]) -> ProjectHealthSignal:
        latest_success = next((job for job in jobs if job.type == "login" and job.status == "completed"), None)
        latest_failure = next((job for job in jobs if job.type == "login" and job.status in {"failed", "interrupted"}), None)

        if auth.authenticated:
            detail = "Phiên Google Flow hiện còn hiệu lực, nên có thể chạy tiếp mà không phải đăng nhập lại ngay."
            if latest_success is not None:
                detail = "App vẫn nhận diện được phiên Google Flow từ lần đăng nhập gần nhất."
            return ProjectHealthSignal(
                key="auth",
                tone="positive",
                label="Đăng nhập còn hiệu lực",
                detail=detail,
                status_label="Ổn",
            )

        if latest_failure is not None:
            return ProjectHealthSignal(
                key="auth",
                tone="warning",
                label="Đăng nhập cần làm mới",
                detail="Có dấu hiệu phiên Flow vừa lỗi hoặc bị ngắt. Nên mở lại đăng nhập trước khi chạy tiếp.",
                status_label="Chú ý",
            )

        if latest_success is not None:
            return ProjectHealthSignal(
                key="auth",
                tone="watch",
                label="Đăng nhập cần làm mới",
                detail="App còn nhớ lần đăng nhập thành công gần đây, nhưng phiên Flow hiện tại không còn được nhận diện.",
                status_label="Nhắc lại",
            )

        return ProjectHealthSignal(
            key="auth",
            tone="warning",
            label="Chưa đăng nhập",
            detail="Workspace chưa có phiên Google Flow sẵn sàng, nên các tác vụ mới sẽ bị chặn cho tới khi đăng nhập.",
            status_label="Thiếu",
        )

    def _build_workflow_signal(self, config: AppConfig, jobs: List[JobRecord]) -> ProjectHealthSignal:
        active_workflow_id = str(config.active_workflow_id or "").strip()
        recent_workflow_id = self._recent_workflow_id(jobs)
        if active_workflow_id:
            detail = f"Workflow mặc định {active_workflow_id} đang được ghim cho các lần chỉnh sửa tiếp theo."
            if recent_workflow_id and recent_workflow_id != active_workflow_id:
                detail = (
                    f"Workflow mặc định {active_workflow_id} đang được ghim; lịch sử gần đây cũng đã có workflow để quay lại nhanh."
                )
            return ProjectHealthSignal(
                key="workflow",
                tone="positive",
                label="Workflow có sẵn",
                detail=detail,
                status_label="Ổn",
            )

        if recent_workflow_id:
            return ProjectHealthSignal(
                key="workflow",
                tone="watch",
                label="Workflow đang để trống",
                detail=(
                    f"Lịch sử gần đây vẫn có workflow {recent_workflow_id}, nhưng workspace hiện chưa ghim workflow mặc định nào."
                ),
                status_label="Nhắc lại",
            )

        return ProjectHealthSignal(
            key="workflow",
            tone="watch",
            label="Workflow đang để trống",
            detail="Tạo mới vẫn chạy được, nhưng form sửa sẽ ít ngữ cảnh hơn cho tới khi lưu một workflow mặc định.",
            status_label="Tùy chọn",
        )

    def _build_local_artifact_signal(self, jobs: List[JobRecord]) -> ProjectHealthSignal:
        status = self._local_artifact_status(jobs)
        available_count = status["available"]
        missing_count = status["missing"]
        remote_count = status["remote_only"]

        if available_count:
            tone = "watch" if missing_count else "positive"
            detail = f"{available_count} artifact local gần đây vẫn còn mở được trên máy."
            if missing_count:
                detail = f"{available_count} artifact local còn mở được, nhưng {missing_count} tệp khác đã không còn trên máy."
            return ProjectHealthSignal(
                key="artifact",
                tone=tone,
                label="Artifact local còn tồn tại",
                detail=detail,
                status_label="Ổn" if tone == "positive" else "Cần xem",
            )

        if missing_count:
            return ProjectHealthSignal(
                key="artifact",
                tone="warning",
                label="Artifact local đã mất",
                detail=f"Có {missing_count} artifact từng được lưu local nhưng file hiện không còn trên máy.",
                status_label="Chú ý",
            )

        if remote_count:
            return ProjectHealthSignal(
                key="artifact",
                tone="watch",
                label="Chưa có artifact local",
                detail="Lịch sử gần đây đã có kết quả hoàn tất, nhưng hiện mới thấy link gốc chứ chưa có file local trên máy.",
                status_label="Tùy chọn",
            )

        return ProjectHealthSignal(
            key="artifact",
            tone="neutral",
            label="Chưa có artifact local",
            detail="Khi lưu kết quả về máy, app sẽ theo dõi tình trạng file local ngay tại đây.",
            status_label="Nền",
        )

    def _build_project_health_timeline(
        self,
        config: AppConfig,
        auth: AuthStatus,
        recent_jobs: List[JobRecord],
        all_jobs: List[JobRecord],
    ) -> List[ProjectHealthTimelineEntry]:
        if not recent_jobs:
            last_activity_at = next((self._job_activity_at(job) for job in all_jobs if self._job_activity_at(job)), "")
            if not last_activity_at:
                return []
            return [
                ProjectHealthTimelineEntry(
                    key="stale-history",
                    tone="neutral",
                    title="Chưa có hoạt động đủ gần",
                    detail=(
                        f"Lịch sử vẫn còn lưu nhưng đã cũ hơn {self.PROJECT_HEALTH_RECENCY_DAYS} ngày, nên trust signals bên trên đáng tin hơn timeline."
                    ),
                    at=last_activity_at,
                )
            ]

        entries = [
            self._build_login_timeline_entry(auth, recent_jobs),
            self._build_timeout_timeline_entry(recent_jobs),
            self._build_workflow_timeline_entry(config, recent_jobs),
            self._build_interrupted_timeline_entry(recent_jobs),
            self._build_local_artifact_timeline_entry(recent_jobs),
        ]
        timeline = [entry for entry in entries if entry is not None]
        if not timeline:
            success_entry = self._build_recent_success_timeline_entry(recent_jobs)
            if success_entry is not None:
                timeline.append(success_entry)

        timeline.sort(key=lambda item: item.at or "", reverse=True)
        return timeline[: self.PROJECT_HEALTH_TIMELINE_LIMIT]

    def _build_login_timeline_entry(
        self,
        auth: AuthStatus,
        recent_jobs: List[JobRecord],
    ) -> ProjectHealthTimelineEntry | None:
        recent_login_jobs = [job for job in recent_jobs if job.type == "login"]
        latest_success = next((job for job in recent_login_jobs if job.status == "completed"), None)
        latest_failure = next((job for job in recent_login_jobs if job.status in {"failed", "interrupted"}), None)

        if auth.authenticated and latest_success is not None:
            return ProjectHealthTimelineEntry(
                key="login-ok",
                tone="positive",
                title="Login ổn",
                detail="Lần đăng nhập gần nhất vẫn còn nền tốt để quay lại chạy tiếp mà không phải thiết lập lại từ đầu.",
                at=self._job_activity_at(latest_success),
            )

        if auth.authenticated and recent_login_jobs:
            return ProjectHealthTimelineEntry(
                key="login-ok",
                tone="positive",
                title="Login ổn",
                detail="App vẫn đang nhìn thấy phiên Google Flow hoạt động bình thường trong project hiện tại.",
                at=self._job_activity_at(recent_login_jobs[0]),
            )

        if latest_failure is not None:
            return ProjectHealthTimelineEntry(
                key="login-refresh",
                tone="warning",
                title="Đăng nhập cần làm mới",
                detail="Timeline gần đây cho thấy phiên Flow đã bị lỗi hoặc bị ngắt, nên đăng nhập lại trước khi chạy các tác vụ mới.",
                at=self._job_activity_at(latest_failure),
            )

        if latest_success is not None:
            return ProjectHealthTimelineEntry(
                key="login-refresh",
                tone="watch",
                title="Phiên đăng nhập cần làm mới",
                detail="App còn nhớ lần đăng nhập thành công gần đây, nhưng hiện không còn nhìn thấy phiên Flow còn hiệu lực.",
                at=self._job_activity_at(latest_success),
            )

        return None

    def _build_timeout_timeline_entry(self, recent_jobs: List[JobRecord]) -> ProjectHealthTimelineEntry | None:
        timeout_jobs = [
            job
            for job in recent_jobs
            if str(getattr(getattr(job, "error_snapshot", None), "category", "") or "").strip() == "timeout"
        ]
        if not timeout_jobs:
            return None

        ordered = list(reversed(timeout_jobs))
        timeout_values = [self._job_timeout_limit(job) for job in ordered if self._job_timeout_limit(job) > 0]
        latest_job = timeout_jobs[0]
        latest_timeout = self._job_timeout_limit(latest_job)
        if len(timeout_values) >= 2 and timeout_values[-1] > min(timeout_values[:-1]):
            return ProjectHealthTimelineEntry(
                key="timeout-trend",
                tone="warning",
                title="Timeout tăng",
                detail=(
                    f"Các lần lỗi gần đây đã tăng timeout từ {min(timeout_values)}s lên {timeout_values[-1]}s nhưng vẫn có job chạm trần."
                ),
                at=self._job_activity_at(latest_job),
            )

        if len(timeout_jobs) >= 2:
            return ProjectHealthTimelineEntry(
                key="timeout-repeat",
                tone="warning",
                title="Timeout lặp lại",
                detail=(
                    f"Đã có {len(timeout_jobs)} job gần đây cùng chạm giới hạn thời gian chờ. Nên tăng timeout hoặc rút gọn payload trước."
                ),
                at=self._job_activity_at(latest_job),
            )

        return ProjectHealthTimelineEntry(
            key="timeout-single",
            tone="watch",
            title="Có timeout gần đây",
            detail=(
                f"Job gần nhất đã chạm giới hạn {latest_timeout}s. Nếu tiếp tục tác vụ dài, nên tăng timeout trước khi chạy lại."
                if latest_timeout > 0
                else "Job gần nhất đã chạm giới hạn thời gian chờ. Nếu tiếp tục tác vụ dài, nên tăng timeout trước khi chạy lại."
            ),
            at=self._job_activity_at(latest_job),
        )

    def _build_workflow_timeline_entry(
        self,
        config: AppConfig,
        recent_jobs: List[JobRecord],
    ) -> ProjectHealthTimelineEntry | None:
        active_workflow_id = str(config.active_workflow_id or "").strip()
        if active_workflow_id:
            return None

        recent_workflow_id = self._recent_workflow_id(recent_jobs)
        relevant_jobs = [job for job in recent_jobs if job.type != "login"]
        if not relevant_jobs:
            return None

        detail = "Việc tạo mới không bị chặn, nhưng form sửa sẽ không tự điền workflow cho tới khi lưu lại workflow mặc định."
        if recent_workflow_id:
            detail = (
                f"Lịch sử gần đây từng dùng workflow {recent_workflow_id}, nhưng workspace hiện vẫn để trống workflow mặc định."
            )

        return ProjectHealthTimelineEntry(
            key="workflow-empty",
            tone="watch",
            title="Workflow đang để trống",
            detail=detail,
            at=self._job_activity_at(relevant_jobs[0]),
        )

    def _build_interrupted_timeline_entry(self, recent_jobs: List[JobRecord]) -> ProjectHealthTimelineEntry | None:
        interrupted_jobs = [job for job in recent_jobs if job.status == "interrupted"]
        if not interrupted_jobs:
            return None

        latest_job = interrupted_jobs[0]
        count = len(interrupted_jobs)
        return ProjectHealthTimelineEntry(
            key="interrupted-jobs",
            tone="warning",
            title="Có job bị ngắt",
            detail=(
                f"Có {count} job bị ngắt trong timeline gần đây. Replay pack đã giữ input recovery để mở retry nhanh."
            ),
            at=self._job_activity_at(latest_job),
        )

    def _build_local_artifact_timeline_entry(self, recent_jobs: List[JobRecord]) -> ProjectHealthTimelineEntry | None:
        status = self._local_artifact_status(recent_jobs)
        if not status["missing"]:
            return None

        return ProjectHealthTimelineEntry(
            key="artifact-missing",
            tone="watch",
            title="Có artifact local cần kiểm tra",
            detail=f"{status['missing']} tệp local trong lịch sử gần đây đã không còn trên máy, nên output shelf có thể thiếu bản mở nhanh.",
            at=status["latest_local_at"],
        )

    def _build_recent_success_timeline_entry(self, recent_jobs: List[JobRecord]) -> ProjectHealthTimelineEntry | None:
        latest_completed = next((job for job in recent_jobs if job.type != "login" and job.status == "completed"), None)
        if latest_completed is None:
            latest_completed = next((job for job in recent_jobs if job.status == "completed"), None)
        if latest_completed is None:
            return None

        title = latest_completed.title or self._job_type_label(latest_completed.type)
        return ProjectHealthTimelineEntry(
            key="recent-success",
            tone="positive",
            title="Hoạt động gần đây chạy ổn",
            detail=f"Lần chạy gần nhất của {title.lower()} đã hoàn tất, nên project này vẫn có nền tốt để tiếp tục.",
            at=self._job_activity_at(latest_completed),
        )

    def _project_health_overview(
        self,
        config: AppConfig,
        auth: AuthStatus,
        signals: List[ProjectHealthSignal],
        timeline: List[ProjectHealthTimelineEntry],
    ) -> tuple[str, str, str]:
        signal_by_key = {signal.key: signal for signal in signals}
        has_project = str(config.project_id or "").strip() != ""
        has_workflow = str(config.active_workflow_id or "").strip() != ""
        auth_ok = bool(auth.authenticated)
        has_warning_timeline = any(entry.tone in {"watch", "warning"} for entry in timeline)
        local_signal = signal_by_key.get("artifact")

        if has_project and auth_ok and not has_warning_timeline:
            status_label = "Có thể chạy tiếp"
            headline = "Workspace hiện tại đủ nền để tiếp tục công việc mà không cần thiết lập lại."
        elif has_project and not auth_ok:
            status_label = "Cần làm mới đăng nhập"
            headline = "Project vẫn còn đó, nhưng phiên Google Flow cần được làm mới trước khi chạy tiếp."
        elif not has_project:
            status_label = "Cần lưu project"
            headline = "App chưa có project hợp lệ để nối lại công việc gần đây."
        else:
            status_label = "Nên kiểm tra nhanh"
            headline = "Có vài dấu hiệu nên rà lại trước khi chạy tiếp."

        summary_bits = [
            "Project đang được lưu chuẩn." if has_project else "Project chưa được lưu.",
            "Đăng nhập còn hiệu lực." if auth_ok else "Đăng nhập cần làm mới.",
            "Workflow mặc định đã có sẵn." if has_workflow else "Workflow mặc định đang để trống.",
        ]
        if local_signal is not None:
            if local_signal.label == "Artifact local còn tồn tại":
                summary_bits.append("Artifact local vẫn còn trên máy.")
            elif local_signal.label == "Artifact local đã mất":
                summary_bits.append("Artifact local cần được kiểm tra lại.")
        if any(entry.key.startswith("timeout") for entry in timeline):
            summary_bits.append("Timeline gần đây có dấu hiệu timeout.")
        if any(entry.key == "interrupted-jobs" for entry in timeline):
            summary_bits.append("Replay pack đang giữ các job bị ngắt.")

        return status_label, headline, " ".join(summary_bits[:5])

    def _sorted_jobs_by_activity(self, jobs: List[JobRecord]) -> List[JobRecord]:
        return sorted(jobs, key=lambda job: self._job_activity_datetime(job) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    def _recent_jobs(self, jobs: List[JobRecord], *, days: int) -> List[JobRecord]:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=max(1, int(days or 1)))
        recent: List[JobRecord] = []
        for job in jobs:
            at = self._job_activity_datetime(job)
            if at is None or at < threshold:
                continue
            recent.append(job)
        return recent

    def _recent_workflow_id(self, jobs: List[JobRecord]) -> str:
        for job in jobs:
            job_input = job.input if isinstance(job.input, dict) else {}
            workflow_id = str(job_input.get("workflow_id", "") or "").strip()
            if workflow_id:
                return workflow_id
            for artifact in job.artifacts:
                artifact_workflow_id = str(getattr(artifact, "workflow_id", "") or "").strip()
                if artifact_workflow_id:
                    return artifact_workflow_id
        return ""

    def _local_artifact_status(self, jobs: List[JobRecord]) -> Dict[str, Any]:
        available = 0
        missing = 0
        remote_only = 0
        latest_local_at = ""

        for job in jobs:
            activity_at = self._job_activity_at(job)
            for artifact in job.artifacts:
                local_path = str(getattr(artifact, "local_path", "") or "").strip()
                if local_path:
                    if activity_at and activity_at > latest_local_at:
                        latest_local_at = activity_at
                    if self._artifact_local_exists(local_path):
                        available += 1
                    else:
                        missing += 1
                    continue

                if str(getattr(artifact, "url", "") or "").strip() or str(getattr(artifact, "public_url", "") or "").strip():
                    remote_only += 1

        return {
            "available": available,
            "missing": missing,
            "remote_only": remote_only,
            "latest_local_at": latest_local_at,
        }

    def _job_timeout_limit(self, job: JobRecord) -> int:
        job_input = job.input if isinstance(job.input, dict) else {}
        try:
            timeout_s = int(job_input.get("timeout_s") or 0)
        except (TypeError, ValueError):
            timeout_s = 0
        if timeout_s > 0:
            return timeout_s

        candidates = [
            str(job.error or "").strip(),
            str(getattr(getattr(job, "error_snapshot", None), "message", "") or "").strip(),
        ]
        for candidate in candidates:
            match = re.search(r"(?P<seconds>\d+)\s*(?:giây|s)\b", candidate, re.IGNORECASE)
            if match:
                try:
                    return max(0, int(match.group("seconds")))
                except (TypeError, ValueError):
                    continue
        return 0

    def _job_activity_at(self, job: JobRecord) -> str:
        return str(job.updated_at or job.created_at or "").strip()

    def _job_activity_datetime(self, job: JobRecord) -> datetime | None:
        return _parse_iso_datetime(self._job_activity_at(job))

    def _build_replay_pack(self, jobs: List[JobRecord]) -> InterruptedReplayPack:
        order = {"auth": 0, "video": 1, "image": 2, "edit": 3, "other": 4}
        grouped: Dict[str, InterruptedReplayGroup] = {}

        for job in jobs:
            snapshot = getattr(job, "replay_snapshot", None)
            if job.status != "interrupted" or snapshot is None or not snapshot.available or snapshot.cleared_at:
                continue

            group_key = str(snapshot.group_key or "edit").strip() or "edit"
            group_meta = self._replay_group_meta(group_key)
            group = grouped.get(group_key)
            if group is None:
                group = InterruptedReplayGroup(
                    key=group_key,
                    label=group_meta["label"],
                    description=group_meta["description"],
                )
                grouped[group_key] = group

            group.items.append(
                InterruptedReplayItem(
                    job_id=job.id,
                    title=job.title or self._job_type_label(job.type),
                    job_type=job.type,
                    job_type_label=self._job_type_label(job.type),
                    summary=snapshot.summary,
                    previous_status=snapshot.previous_status,
                    previous_status_label=snapshot.previous_status_label,
                    created_at=job.created_at,
                    interrupted_at=snapshot.interrupted_at or job.updated_at,
                    last_log_at=snapshot.last_log_at,
                    last_log_message=snapshot.last_log_message,
                    prompt_excerpt=snapshot.prompt_excerpt,
                    input_fields=list(snapshot.input_fields or []),
                    can_retry=job.type in self.SUPPORTED_SKILL_TYPES,
                    can_cleanup=True,
                )
            )

        if not grouped:
            return InterruptedReplayPack()

        groups = sorted(grouped.values(), key=lambda item: order.get(item.key, 99))
        for group in groups:
            group.items.sort(key=lambda item: (item.interrupted_at or item.created_at or ""), reverse=True)
            group.item_count = len(group.items)

        total_items = sum(group.item_count for group in groups)
        return InterruptedReplayPack(
            has_items=bool(total_items),
            total_items=total_items,
            groups=groups,
            cleanup_note="Dọn metadata recovery chỉ gỡ replay pack khỏi khu interrupted work. Log, history và mọi artifact local đã lưu vẫn được giữ nguyên.",
        )

    async def get_credits(self) -> Dict[str, Any]:
        async def _go(client: Any) -> Dict[str, Any]:
            credits = await client.get_credits()
            return {
                "credits": getattr(credits, "credits", 0),
                "tier": getattr(credits, "tier", ""),
                "sku": getattr(credits, "sku", ""),
                "service_tier": getattr(credits, "service_tier", ""),
            }

        return await self._with_client(_go)

    async def get_workflows(self) -> List[Dict[str, Any]]:
        async def _go(client: Any) -> List[Dict[str, Any]]:
            workflows = await client.get_workflows()
            return [
                {
                    "name": getattr(workflow, "name", ""),
                    "display_name": getattr(workflow, "display_name", ""),
                    "create_time": getattr(workflow, "create_time", ""),
                    "primary_media_id": getattr(workflow, "primary_media_id", ""),
                    "batch_id": getattr(workflow, "batch_id", ""),
                    "project_id": getattr(workflow, "project_id", ""),
                }
                for workflow in workflows
            ]

        return await self._with_client(_go)

    async def get_model_config(self) -> Dict[str, Any]:
        async def _go(client: Any) -> Dict[str, Any]:
            return await client.get_model_config()

        return await self._with_client(_go)

    async def save_upload(self, upload: UploadFile) -> Dict[str, str]:
        ensure_app_dirs()
        file_name = Path(upload.filename or "upload.bin").name
        target = UPLOADS_DIR / file_name
        stem = target.stem
        suffix = target.suffix
        counter = 1
        while target.exists():
            target = UPLOADS_DIR / f"{stem}-{counter}{suffix}"
            counter += 1
        with target.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        upload.file.close()
        return {
            "file_name": target.name,
            "saved_path": str(target),
            "public_url": f"/files/uploads/{target.name}",
        }

    async def enqueue_login(self) -> JobRecord:
        job = JobRecord(type="login", status="queued", title="Đăng nhập Google Flow")
        await self.store.add_job(job)
        try:
            page = await self._launch_login_browser(job.id)
        except HTTPException:
            raise
        except Exception as exc:
            detail = self._flow_error_detail(exc)
            await self.store.patch_job(job.id, status="failed", error=detail)
            await self.store.append_log(job.id, f"Đăng nhập thất bại: {detail}")
            raise HTTPException(
                status_code=self._flow_error_status(exc),
                detail=detail,
            ) from exc
        self._tasks[job.id] = asyncio.create_task(self._wait_for_login_completion(job.id, page))
        return job

    async def enqueue_job(self, request: CreateJobRequest) -> JobRecord:
        config = self._normalized_config(self.store.snapshot().config)
        if not config.project_id:
            raise HTTPException(status_code=400, detail="Vui lòng lưu mã project trước.")
        request = self._resolve_job_request(request, config)
        self._validate_job_request(request)
        source_job = self._resolve_retry_source(request.source_job_id, request.type)

        title = request.title.strip() or self._default_title(request)
        job = JobRecord(
            type=request.type,
            status="queued",
            title=title,
            input=_model_dump(request),
            source_job_id=request.source_job_id,
            retry_snapshot=self._build_retry_snapshot(source_job),
        )
        await self.store.add_job(job)
        if source_job is not None:
            await self.store.append_log(
                job.id,
                f"Đã clone payload từ job {source_job.id[:8]} để tạo lần chạy lại mới.",
            )
        self._tasks[job.id] = asyncio.create_task(self._run_flow_job(job.id, request))
        return job

    async def create_skill(self, request: SkillCreateRequest) -> SkillRecord:
        fields_set = self._fields_set(request)
        parsed = self._parse_skill_text(request.skill_text) if request.skill_text.strip() else {}

        name = self._pick_skill_value(fields_set, "name", request.name, parsed.get("name", ""))
        if not name:
            name = self._suggest_skill_name(
                self._pick_skill_value(fields_set, "type", request.type, parsed.get("type", "video")) or "video",
                self._pick_skill_value(fields_set, "prompt", request.prompt, parsed.get("prompt", "")),
            )

        skill_type = self._pick_skill_value(fields_set, "type", request.type, parsed.get("type", "video")) or "video"
        if skill_type not in self.SUPPORTED_SKILL_TYPES:
            raise HTTPException(status_code=400, detail="Loại kỹ năng này chưa được hỗ trợ.")

        skill = SkillRecord(
            name=name,
            summary=self._pick_skill_value(fields_set, "summary", request.summary, parsed.get("summary", "")),
            skill_text=request.skill_text.strip(),
            source_repo=self._pick_skill_value(fields_set, "source_repo", request.source_repo, ""),
            source_path=self._pick_skill_value(fields_set, "source_path", request.source_path, ""),
            source_url=self._pick_skill_value(fields_set, "source_url", request.source_url, ""),
            is_builtin=bool(self._pick_skill_value(fields_set, "is_builtin", request.is_builtin, False)),
            type=skill_type,
            prompt=self._pick_skill_value(fields_set, "prompt", request.prompt, parsed.get("prompt", "")),
            aspect=self._pick_skill_value(fields_set, "aspect", request.aspect, parsed.get("aspect", "landscape")) or "landscape",
            count=max(1, min(4, int(self._pick_skill_value(fields_set, "count", request.count, parsed.get("count", 1)) or 1))),
            reference_media_names=self._normalize_reference_media_names(
                self._pick_skill_list(fields_set, "reference_media_names", request.reference_media_names, parsed.get("reference_media_names", []))
            ),
            media_id=self._pick_skill_value(fields_set, "media_id", request.media_id, parsed.get("media_id", "")),
            workflow_id=self._pick_skill_value(fields_set, "workflow_id", request.workflow_id, parsed.get("workflow_id", "")),
            motion=self._pick_skill_value(fields_set, "motion", request.motion, parsed.get("motion", "")),
            position=self._pick_skill_value(fields_set, "position", request.position, parsed.get("position", "")),
            resolution=self._pick_skill_value(fields_set, "resolution", request.resolution, parsed.get("resolution", "1080p")) or "1080p",
            mask_x=min(1.0, max(0.0, float(self._pick_skill_value(fields_set, "mask_x", request.mask_x, parsed.get("mask_x", 0.5)) or 0.5))),
            mask_y=min(1.0, max(0.0, float(self._pick_skill_value(fields_set, "mask_y", request.mask_y, parsed.get("mask_y", 0.5)) or 0.5))),
            brush_size=max(5, min(100, int(self._pick_skill_value(fields_set, "brush_size", request.brush_size, parsed.get("brush_size", 40)) or 40))),
            source_job_id=self._pick_skill_value(fields_set, "source_job_id", request.source_job_id, parsed.get("source_job_id", "")),
        )
        await self.store.add_skill(skill)
        return skill

    async def ensure_media_skill_library(self) -> Dict[str, Any]:
        snapshot = self.store.snapshot()
        if snapshot.skills and all(skill.is_builtin and skill.source_repo == self.MEDIA_SKILL_REPO for skill in snapshot.skills):
            has_prompting_guides = any("/prompting/" in str(skill.source_path or "").lower() for skill in snapshot.skills)
            if has_prompting_guides:
                return {
                    "items": [self._public_skill_payload(skill) for skill in snapshot.skills],
                    "imported_count": len(snapshot.skills),
                    "mode": "cached",
                    "source_url": self.MEDIA_SKILL_SOURCE_URL,
                }
        return await self.sync_media_skills()

    def _prompt_assistant_snapshot(self, skills: List[SkillRecord]) -> Dict[str, Any]:
        relevant = self._prompt_relevant_skills(skills)
        image_count = sum(1 for skill in relevant if self._skill_targets_mode(skill, "image"))
        video_count = sum(1 for skill in relevant if self._skill_targets_mode(skill, "video"))
        prompting_count = sum(1 for skill in relevant if "/prompting/" in str(skill.source_path or "").lower())
        engine = self._prompt_ai_engine()
        if relevant and engine["configured"]:
            headline = "AI viết prompt đang dùng Gemini."
            summary = f"Đang dùng {engine['model']} cùng {len(relevant)} skill để viết prompt dài, rõ và sát ý cho ảnh/video."
        elif relevant:
            headline = "AI viết prompt đang dùng bộ máy nội bộ."
            summary = f"Đã nạp {len(relevant)} skill để mở rộng prompt chi tiết hơn. Có thể thêm GEMINI_API_KEY để bật Gemini thật."
        elif engine["configured"]:
            headline = "Gemini đã sẵn sàng."
            summary = "Gemini đã bật, còn kho skill viết prompt đang được chuẩn bị."
        else:
            headline = "AI viết prompt đang chờ đồng bộ skill."
            summary = "Chưa có kho skill để viết prompt. Có thể thêm GEMINI_API_KEY để bật Gemini sau."
        snapshot = PromptAssistantSnapshot(
            ready=bool(relevant),
            configured=engine["configured"],
            engine=engine["engine"],
            engine_label=engine["engine_label"],
            model=engine["model"],
            skill_count=len(relevant),
            image_skill_count=image_count,
            video_skill_count=video_count,
            prompt_skill_count=prompting_count,
            source_url=self.MEDIA_SKILL_SOURCE_URL,
            headline=headline,
            summary=summary,
            sample_skill_names=[skill.name for skill in relevant[:6]],
        )
        return _model_dump(snapshot)

    def _prompt_ai_engine(self) -> Dict[str, Any]:
        model = self._gemini_model()
        if self._gemini_api_key():
            return {
                "configured": True,
                "engine": "gemini",
                "engine_label": "Gemini",
                "model": model,
            }
        return {
            "configured": False,
            "engine": "local",
            "engine_label": "Nội bộ",
            "model": "",
        }

    def _gemini_api_key(self) -> str:
        for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"):
            value = str(os.getenv(key_name, "")).strip()
            if value:
                return value
        return ""

    def _gemini_model(self) -> str:
        raw = str(os.getenv("GEMINI_MODEL", self.GEMINI_DEFAULT_MODEL)).strip()
        sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "", raw)
        return sanitized or self.GEMINI_DEFAULT_MODEL

    def _prompt_skill_bucket(self, skill: SkillRecord) -> str:
        path = str(skill.source_path or "").lower().strip()
        name = str(skill.name or "").lower().strip()

        if path.startswith("guides/prompting/") or "prompt" in name:
            return "prompting"
        if path.startswith("guides/video/") or path.startswith("tools/video/"):
            return "video"
        if path.startswith("guides/photo/") or path.startswith("tools/image/"):
            return "image"
        if path.startswith("guides/design/"):
            return "design"
        return "other"

    def _prompt_relevant_skills(self, skills: List[SkillRecord]) -> List[SkillRecord]:
        selected: List[SkillRecord] = []
        for skill in skills:
            path = str(skill.source_path or "").lower()
            name = str(skill.name or "").lower()
            if any(path.startswith(prefix) for prefix in self.PROMPT_SKILL_PREFIXES):
                selected.append(skill)
                continue
            if any(
                token in name
                for token in (
                    "prompt",
                    "image",
                    "video",
                    "photo",
                    "storyboard",
                    "veo",
                    "thumbnail",
                    "design",
                    "marketing",
                    "avatar",
                    "landing",
                    "cover",
                    "screenshot",
                    "logo",
                )
            ):
                selected.append(skill)
        return selected

    def _skill_targets_mode(self, skill: SkillRecord, mode: str) -> bool:
        path = str(skill.source_path or "").lower()
        name = str(skill.name or "").lower()
        bucket = self._prompt_skill_bucket(skill)
        if bucket == "prompting":
            return True
        if mode == "image":
            if bucket in {"image", "design"}:
                return True
            return any(
                token in path or token in name
                for token in ("image", "photo", "thumbnail", "og-image", "design", "cover", "logo", "landing", "screenshot")
            )
        if bucket == "video":
            return True
        return any(
            token in path or token in name
            for token in ("video", "veo", "storyboard", "avatar", "marketing", "explainer", "talking-head", "remotion")
        )

    def _prompt_tokens(self, value: str) -> List[str]:
        lowered = self._normalize_skill_token(value or "")
        tokens = [token for token in re.split(r"[^a-z0-9]+", lowered) if len(token) >= 3]
        stop_words = {"cho", "cua", "the", "and", "with", "this", "that", "from", "tren", "duoi", "mot", "nhung", "video", "image", "prompt"}
        return [token for token in tokens if token not in stop_words]

    def _select_prompt_skills(self, mode: str, brief: str, style: str = "", must_include: str = "") -> List[SkillRecord]:
        relevant = self._prompt_relevant_skills(self.store.snapshot().skills)
        if not relevant:
            return []

        query_tokens = set(self._prompt_tokens(" ".join([brief, style, must_include])))
        scored: List[tuple[int, SkillRecord]] = []
        for skill in relevant:
            score = 0
            path = str(skill.source_path or "").lower()
            combined = " ".join([skill.name, skill.summary, skill.source_path, skill.skill_text[:800]])
            normalized = self._normalize_skill_token(combined)
            bucket = self._prompt_skill_bucket(skill)

            if self._skill_targets_mode(skill, mode):
                score += 6
            if bucket == "prompting":
                score += 5
            if mode == "image" and bucket == "design":
                score += 4
            if mode == "image" and any(token in path for token in ("thumbnail", "og-image", "product-photography", "book-cover", "landing-page", "app-store")):
                score += 4
            if mode == "video" and any(token in path for token in ("google-veo", "ai-video-generation", "video-prompting-guide", "storyboard")):
                score += 5
            if mode == "video" and any(token in path for token in ("explainer-video-guide", "talking-head-production", "video-ad-specs", "ai-marketing-videos")):
                score += 4
            if mode == "image" and any(token in path for token in ("ai-image-generation", "product-photography", "photo", "nano-banana")):
                score += 5
            overlap = sum(1 for token in query_tokens if token in normalized)
            score += min(overlap, 8)
            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda item: (-item[0], item[1].name.lower()))
        return [skill for _, skill in scored[:6]]

    def _style_fragments_from_skills(self, mode: str, skills: List[SkillRecord]) -> List[str]:
        fragments: List[str] = []
        for skill in skills:
            path = str(skill.source_path or "").lower()
            if mode == "video":
                if "prompt-engineering" in path:
                    fragments.extend(["clear subject-action-environment", "specific visual language"])
                if "video-prompting-guide" in path:
                    fragments.extend(["cinematic framing", "clear shot design", "controlled lighting"])
                if "google-veo" in path:
                    fragments.extend(["natural motion", "coherent subject consistency", "high fidelity detail"])
                if "storyboard-creation" in path:
                    fragments.extend(["clear visual beats", "readable action progression"])
                if "ai-marketing-videos" in path:
                    fragments.extend(["polished commercial look", "brand-safe composition"])
                if "explainer-video-guide" in path:
                    fragments.extend(["clear narrative progression", "easy-to-read scene intent"])
                if "talking-head-production" in path:
                    fragments.extend(["natural presenter framing", "clean eye-line composition"])
                if "video-ad-specs" in path:
                    fragments.extend(["strong hook in first seconds", "short-form ad pacing"])
            else:
                if "prompt-engineering" in path:
                    fragments.extend(["specific subject description", "clear visual hierarchy"])
                if "ai-image-generation" in path:
                    fragments.extend(["photorealistic detail", "clean composition"])
                if "product-photography" in path:
                    fragments.extend(["premium product photography", "studio reflections", "commercial polish"])
                if "nano-banana" in path or "qwen-image" in path or "flux-image" in path:
                    fragments.extend(["sharp subject detail", "rich texture rendering"])
                if "og-image-design" in path:
                    fragments.extend(["strong focal hierarchy"])
                if "youtube-thumbnail-design" in path:
                    fragments.extend(["high-contrast focal subject", "immediate visual read"])
                if "book-cover-design" in path:
                    fragments.extend(["hero-led cover composition", "dramatic visual focus"])
                if "landing-page-design" in path or "app-store-screenshots" in path:
                    fragments.extend(["clean commercial presentation", "clear feature-first composition"])
                if "logo-design-guide" in path:
                    fragments.extend(["iconic silhouette", "simple memorable shapes"])
        seen: set[str] = set()
        unique: List[str] = []
        for item in fragments:
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            unique.append(item)
        return unique[:6]

    def _video_shot_hint(self, brief: str, style: str) -> str:
        text = self._normalize_skill_token(f"{brief} {style}")
        if any(token in text for token in ("product", "san_pham", "watch", "phone", "chuoi")):
            return "Cinematic product hero shot"
        if any(token in text for token in ("city", "thanh_pho", "landscape", "canh_quan", "room", "phong")):
            return "Wide cinematic establishing shot"
        if any(token in text for token in ("person", "human", "nguoi", "piano", "cat", "meo", "dog", "cho")):
            return "Medium cinematic shot"
        return "Cinematic medium-wide shot"

    def _image_framing_hint(self, brief: str, style: str) -> str:
        text = self._normalize_skill_token(f"{brief} {style}")
        if any(token in text for token in ("product", "san_pham", "bottle", "watch", "phone", "food", "chuoi")):
            return "Commercial product hero shot"
        if any(token in text for token in ("portrait", "face", "nguoi", "person", "fashion")):
            return "Editorial portrait composition"
        return "Detailed hero composition"

    def _lighting_hint(self, brief: str, style: str) -> str:
        text = self._normalize_skill_token(f"{brief} {style}")
        if any(token in text for token in ("night", "dem", "neon", "cyber", "futuristic")):
            return "neon cinematic lighting"
        if any(token in text for token in ("sunset", "hoang_hon", "golden", "warm", "am")):
            return "warm golden hour lighting"
        if any(token in text for token in ("dark", "toi", "dramatic", "moody")):
            return "dramatic low-key lighting"
        if any(token in text for token in ("studio", "san_pham", "product")):
            return "soft studio lighting"
        return "soft natural lighting"

    def _mood_hint(self, brief: str, style: str) -> str:
        text = self._normalize_skill_token(f"{brief} {style}")
        if any(token in text for token in ("luxury", "premium", "sang_trong", "elegant", "editorial")):
            return "premium refined mood"
        if any(token in text for token in ("dark", "toi", "dramatic", "moody", "thriller")):
            return "dramatic moody atmosphere"
        if any(token in text for token in ("cute", "de_thuong", "playful", "fun", "happy")):
            return "playful friendly mood"
        if any(token in text for token in ("battle", "fight", "samurai", "action", "epic")):
            return "tense high-energy atmosphere"
        return "cinematic polished atmosphere"

    def _video_camera_hint(self, brief: str, style: str) -> str:
        text = self._normalize_skill_token(f"{brief} {style}")
        if any(token in text for token in ("product", "san_pham", "watch", "phone", "bottle")):
            return "hero product framing with a slow dolly-in, controlled parallax, and crisp focus transitions"
        if any(token in text for token in ("fight", "battle", "samurai", "action", "combat")):
            return "dynamic cinematic coverage with a low-angle hero frame, readable action geography, and subtle camera drift"
        if any(token in text for token in ("portrait", "person", "human", "nguoi", "piano", "cat", "meo", "dog", "cho")):
            return "medium cinematic framing with a natural lens feel, gentle push-in, and clear subject separation"
        return "cinematic framing with layered depth, subtle movement, and a strong focal path through the frame"

    def _video_detail_fragments(self, brief: str, style: str) -> List[str]:
        text = self._normalize_skill_token(f"{brief} {style}")
        details = [
            "clear subject, action, and environment relationship",
            "layered foreground midground and background depth",
            "cohesive color palette with believable contrast",
            "consistent subject identity across the full clip",
            "high texture fidelity and realistic material response",
            "clean frame edges with strong focal hierarchy",
            "polished cinematic color grading",
            "each moment should feel usable as a hero frame",
        ]
        if any(token in text for token in ("person", "human", "nguoi", "portrait", "face")):
            details.extend([
                "natural facial expression and believable anatomy",
                "subtle secondary motion in hair, fabric, and small gestures",
            ])
        if any(token in text for token in ("water", "ocean", "river", "pond", "lake", "koi")):
            details.extend([
                "realistic water caustics, ripples, and reflected highlights",
                "smooth underwater or surface-adjacent motion with convincing fluid behavior",
            ])
        if any(token in text for token in ("battle", "fight", "samurai", "action", "combat")):
            details.extend([
                "clear action beats with readable staging",
                "impactful motion arcs, debris, cloth movement, and environmental reaction",
            ])
        return details[:10]

    def _image_detail_fragments(self, brief: str, style: str) -> List[str]:
        text = self._normalize_skill_token(f"{brief} {style}")
        details = [
            "clean subject separation from the background",
            "high micro-detail and believable material texture",
            "refined highlights, shadows, and edge contrast",
            "strong focal hierarchy with uncluttered composition",
            "realistic depth and dimensionality",
            "polished commercial-grade finish",
        ]
        if any(token in text for token in ("product", "san_pham", "watch", "phone", "bottle", "headphone", "tai_nghe")):
            details.extend([
                "premium product presentation with controlled reflections",
                "precise surface definition on metal, glass, plastic, or fabric",
            ])
        if any(token in text for token in ("portrait", "person", "human", "nguoi", "fashion", "face")):
            details.extend([
                "sharp eye focus and flattering facial structure",
                "natural skin texture without waxy rendering",
            ])
        return details[:8]

    def _aspect_phrase(self, aspect: str, mode: str) -> str:
        normalized = str(aspect or "").strip().lower()
        if normalized == "portrait":
            return "vertical 9:16 framing" if mode == "video" else "vertical 9:16 composition"
        if normalized == "square":
            return "square 1:1 composition"
        return "wide 16:9 framing" if mode == "video" else "wide 16:9 composition"

    def _compose_prompt_draft(self, request: PromptCreateRequest, skills: List[SkillRecord]) -> str:
        mode = self._parse_skill_type(request.mode)
        brief = request.brief.strip()
        style = request.style.strip()
        must_include = request.must_include.strip()
        avoid = request.avoid.strip()
        audience = request.audience.strip()
        aspect = request.aspect.strip() or ("square" if mode == "image" else "landscape")
        fragments = self._style_fragments_from_skills(mode, skills)
        lighting = self._lighting_hint(brief, style)
        mood = self._mood_hint(brief, style)
        aspect_phrase = self._aspect_phrase(aspect, mode)

        if mode == "video":
            opening = self._video_shot_hint(brief, style)
            parts = [
                opening,
                brief,
                f"visual style {style}" if style else "cinematic premium visual treatment",
                f"lighting is {lighting}",
                f"mood is {mood}",
                aspect_phrase,
                self._video_camera_hint(brief, style),
                "smooth realistic motion with stable temporal consistency",
                "professional cinematography with believable depth of field",
            ]
            parts.extend(self._video_detail_fragments(brief, style))
        else:
            opening = self._image_framing_hint(brief, style)
            parts = [
                opening,
                brief,
                f"visual style {style}" if style else "polished premium still-image treatment",
                f"lighting is {lighting}",
                f"mood is {mood}",
                aspect_phrase,
                "photorealistic detail with controlled composition",
                "clear hero subject with strong visual hierarchy",
            ]
            parts.extend(self._image_detail_fragments(brief, style))

        if must_include:
            parts.append(f"must include {must_include}")
        if audience:
            parts.append(f"optimized for {audience}")
        parts.extend(fragments)
        prompt = ", ".join([part.strip() for part in parts if part and part.strip()])
        if avoid:
            prompt = f"{prompt}. Avoid {avoid.strip()}."
        return prompt.strip()

    def _gemini_skill_guidance(self, skills: List[SkillRecord]) -> str:
        lines: List[str] = []
        for skill in skills[:6]:
            summary = str(skill.summary or "").strip()
            if not summary:
                summary = str(skill.source_path or "").strip()
            if not summary:
                summary = "Không có mô tả ngắn."
            lines.append(f"- {skill.name}: {summary}")
        return "\n".join(lines)

    def _clean_prompt_text(self, value: str) -> str:
        text = str(value or "").strip()
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = re.sub(r"^(final prompt|prompt)\s*:\s*", "", text, flags=re.IGNORECASE)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = " ".join(lines).strip()
        return cleaned.strip("\"' ")

    def _extract_gemini_text(self, payload: Dict[str, Any]) -> str:
        candidates = payload.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content") or {}
            for part in content.get("parts") or []:
                text = self._clean_prompt_text(part.get("text") or "")
                if text:
                    return text
        return ""

    def _ensure_prompt_detail(self, prompt: str, baseline: str, mode: str) -> tuple[str, bool]:
        candidate = self._clean_prompt_text(prompt)
        fallback = self._clean_prompt_text(baseline)
        minimum_chars = 220 if mode == "video" else 180
        signal_count = sum(candidate.count(token) for token in (",", ".", ";", ":"))

        if candidate and len(candidate) >= minimum_chars and signal_count >= 4:
            return candidate, False

        if not fallback:
            return candidate, False

        if not candidate or len(candidate) < int(minimum_chars * 0.6) or signal_count < 2:
            merged = fallback
        elif candidate.lower() not in fallback.lower():
            merged = f"{candidate}. {fallback}"
        else:
            merged = fallback

        merged = re.sub(r"\s+", " ", merged).strip()
        max_chars = 900 if mode == "video" else 720
        if len(merged) > max_chars:
            clipped = merged[:max_chars]
            last_stop = max(clipped.rfind("."), clipped.rfind(";"), clipped.rfind(","))
            if last_stop > int(minimum_chars * 0.6):
                merged = clipped[:last_stop].rstrip(" ,.;") + "."
            else:
                merged = clipped.rstrip(" ,.;") + "."
        return merged, merged != candidate

    def _gemini_prompt_request(self, request: PromptCreateRequest, skills: List[SkillRecord], baseline: str) -> Dict[str, Any]:
        mode = self._parse_skill_type(request.mode)
        aspect = request.aspect.strip() or ("square" if mode == "image" else "landscape")
        guidance = self._gemini_skill_guidance(skills) or "- Không có skill đặc biệt, chỉ cần viết prompt rõ ràng."
        prompt_text = "\n".join(
            [
                "Bạn là chuyên gia viết prompt cho Google Flow.",
                "Hãy trả về duy nhất một prompt hoàn chỉnh, không markdown, không giải thích, không gạch đầu dòng.",
                "Viết cùng ngôn ngữ với brief gốc của người dùng.",
                "Prompt phải cực kỳ chi tiết, production-ready, giàu hình ảnh và có thể dán chạy ngay.",
                f"Chế độ: {mode}",
                f"Tỉ lệ: {aspect}",
                f"Ý chính người dùng: {request.brief.strip()}",
                f"Phong cách: {request.style.strip() or 'Không ghi rõ'}",
                f"Phải có: {request.must_include.strip() or 'Không ghi rõ'}",
                f"Tránh: {request.avoid.strip() or 'Không ghi rõ'}",
                f"Dành cho ai: {request.audience.strip() or 'Không ghi rõ'}",
                "Hướng dẫn rút ra từ kho skill:",
                guidance,
                "Bản nháp nội bộ hiện có để cải thiện thêm:",
                baseline,
                "Nếu là video, hãy làm rõ chủ thể, hành động, bối cảnh, lớp không gian, camera, nhịp chuyển động, ánh sáng, chất liệu, continuity, và cảm giác dựng hình.",
                "Nếu là ảnh, hãy làm rõ chủ thể, bố cục, góc máy, ánh sáng, bảng màu, vật liệu/chất liệu, chiều sâu, và điểm nhấn thị giác.",
                "Nếu người dùng chưa nói đủ, hãy tự bổ sung các chi tiết hỗ trợ hợp lý nhưng không đổi ý chính.",
                "Không xưng hô với người dùng trong prompt. Không nhắc tới việc bạn là AI. Không viết kiểu meta.",
                "Ưu tiên một prompt dày thông tin, cô đọng nhưng nhiều tín hiệu thị giác, thường dài khoảng 90 đến 180 từ.",
            ]
        )
        return {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt_text,
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.85,
                "topP": 0.95,
                "maxOutputTokens": 768,
            },
        }

    def _generate_prompt_with_gemini(self, request: PromptCreateRequest, skills: List[SkillRecord], baseline: str) -> str:
        api_key = self._gemini_api_key()
        if not api_key:
            raise RuntimeError("Chưa cấu hình GEMINI_API_KEY.")

        model = self._gemini_model()
        payload = self._gemini_prompt_request(request, skills, baseline)
        url = self.GEMINI_API_URL_TEMPLATE.format(model=quote(model, safe="._-"))
        request_obj = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        try:
            with urlopen(request_obj, timeout=self.GEMINI_TIMEOUT_S) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
                message = str(error_payload.get("error", {}).get("message", "")).strip()
            except Exception:
                message = ""
            raise RuntimeError(message or f"Gemini API trả về HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError(f"Không gọi được Gemini: {exc.reason}") from exc

        prompt = self._extract_gemini_text(body)
        if not prompt:
            raise RuntimeError("Gemini không trả về prompt text.")
        return prompt

    async def generate_prompt_draft(self, request: PromptCreateRequest) -> Dict[str, Any]:
        brief = str(request.brief or "").strip()
        if not brief:
            raise HTTPException(status_code=400, detail="Hãy nói ngắn gọn điều muốn tạo trước.")

        await self.ensure_media_skill_library()
        mode = self._parse_skill_type(request.mode)
        selected = self._select_prompt_skills(mode, brief, request.style, request.must_include)
        baseline_prompt = self._compose_prompt_draft(request, selected)
        prompt = baseline_prompt
        prompt, expanded_prompt = self._ensure_prompt_detail(prompt, baseline_prompt, mode)
        engine = "local"
        engine_label = "Nội bộ"
        model = ""
        summary = (
            f"Gemini chưa bật, đang dùng bộ viết prompt nội bộ với {len(selected)} skill để mở rộng prompt chi tiết."
            if selected
            else "Gemini chưa bật, đang dùng công thức prompt nội bộ mặc định."
        )
        if self._gemini_api_key():
            try:
                prompt = await asyncio.to_thread(self._generate_prompt_with_gemini, request, selected, baseline_prompt)
                prompt, expanded_prompt = self._ensure_prompt_detail(prompt, baseline_prompt, mode)
                engine = "gemini"
                engine_label = "Gemini"
                model = self._gemini_model()
                summary = (
                    f"Gemini {model} đã viết prompt chi tiết này với {len(selected)} skill nền."
                    if selected
                    else f"Gemini {model} đã viết prompt chi tiết này."
                )
            except Exception:
                model = self._gemini_model()
                summary = (
                    f"Gemini {model} chưa phản hồi ổn định, đã rơi về bộ viết prompt nội bộ với {len(selected)} skill."
                    if selected
                    else f"Gemini {model} chưa phản hồi ổn định, đã rơi về bộ viết prompt nội bộ."
                )
        if expanded_prompt:
            if engine == "gemini":
                summary = f"{summary} App đã bổ sung thêm chi tiết từ skill nền để prompt đầy đủ hơn."
            else:
                summary = f"{summary} Prompt đã được mở rộng thêm chi tiết từ bộ skill nền."
        title = "Prompt video" if mode == "video" else "Prompt ảnh"
        if engine == "gemini":
            title = f"{title} Gemini"
        return {
            "title": title,
            "mode": mode,
            "prompt": prompt,
            "applied_skills": [skill.name for skill in selected],
            "skill_count": len(self._prompt_relevant_skills(self.store.snapshot().skills)),
            "summary": summary,
            "aspect": request.aspect.strip() or ("square" if mode == "image" else "landscape"),
            "engine": engine,
            "engine_label": engine_label,
            "model": model,
        }

    async def sync_media_skills(self) -> Dict[str, Any]:
        try:
            entries = await asyncio.to_thread(self._media_skill_repo_entries)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Không quét được kho skill: {exc}") from exc

        imported: List[SkillRecord] = []
        skipped: List[str] = []
        for entry in entries:
            try:
                fetched = await asyncio.to_thread(self._download_skill_text, entry["download_url"])
                skill = await self.create_skill(
                    self._build_imported_skill_request(
                        self._name_from_path(entry["path"]) or "Skill media",
                        f"Đồng bộ từ {entry['html_url']}",
                        fetched["text"],
                        entry["path"],
                        source_repo=self.MEDIA_SKILL_REPO,
                        source_path=entry["path"],
                        source_url=entry["html_url"],
                        is_builtin=True,
                    )
                )
                imported.append(skill)
            except HTTPException as exc:
                skipped.append(f"{entry['path']}: {exc.detail}")
            except Exception as exc:
                skipped.append(f"{entry['path']}: {exc}")

        if not imported:
            raise HTTPException(status_code=400, detail="Chưa đồng bộ được skill nào từ repo nguồn.")

        imported.sort(key=lambda skill: (skill.type, skill.name.lower()))
        await self.store.replace_skills(imported)
        return {
            "items": [self._public_skill_payload(skill) for skill in imported],
            "imported_count": len(imported),
            "skipped_count": len(skipped),
            "skipped": skipped[:12],
            "mode": "sync",
            "source_url": self.MEDIA_SKILL_SOURCE_URL,
        }

    async def import_skill_from_url(self, request: SkillImportRequest) -> Dict[str, Any]:
        request = self._resolve_skill_import_request(request)
        raw_url = request.url.strip()
        if not raw_url:
            raise HTTPException(status_code=400, detail="Hãy nhập link, repo hoặc lệnh skills add.")

        github_source = self._parse_github_collection_url(raw_url)
        if github_source:
            return await self._import_skill_collection(github_source, request)

        skill = await self._import_single_skill(raw_url, request)
        return {
            "items": [skill],
            "imported_count": 1,
            "skipped_count": 0,
            "mode": "single",
            "source_url": raw_url,
        }

    async def _import_single_skill(self, raw_url: str, request: SkillImportRequest) -> SkillRecord:
        target_url = self._normalize_skill_source_url(raw_url)
        try:
            fetched = await asyncio.to_thread(self._download_skill_text, target_url)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Không tải được skill từ link này: {exc}") from exc

        name = request.name.strip() or self._name_from_url(fetched["url"])
        summary = request.summary.strip() or f"Tự tải từ link: {fetched['url']}"
        return await self.create_skill(self._build_imported_skill_request(name, summary, fetched["text"], fetched["url"]))

    async def _import_skill_collection(self, source: Dict[str, str], request: SkillImportRequest) -> Dict[str, Any]:
        selected_skills = self._normalize_selected_skills(request.skills)
        missing_requested: List[str] = []
        try:
            if selected_skills:
                selection = await asyncio.to_thread(
                    self._github_selected_skill_entries,
                    source["owner"],
                    source["repo"],
                    source["branch"],
                    source["path"],
                    selected_skills,
                )
                entries = selection["entries"]
                missing_requested = selection["missing"]
            else:
                entries = await asyncio.to_thread(
                    self._github_skill_file_entries,
                    source["owner"],
                    source["repo"],
                    source["branch"],
                    source["path"],
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Không quét được repo/thư mục skill: {exc}") from exc

        if not entries:
            if selected_skills:
                missing_text = ", ".join(f'"{skill}"' for skill in missing_requested or selected_skills)
                raise HTTPException(status_code=400, detail=f"Không tìm thấy skill {missing_text} trong repo này.")
            raise HTTPException(status_code=400, detail="Không tìm thấy file skill phù hợp trong repo/thư mục này.")

        existing_signatures = {
            self._skill_signature(skill.name, skill.skill_text or skill.prompt)
            for skill in self.store.snapshot().skills
        }

        imported: List[SkillRecord] = []
        skipped: List[str] = []
        name_prefix = request.name.strip()
        summary_prefix = request.summary.strip()

        for skill_name in missing_requested:
            skipped.append(f"{skill_name}: không tìm thấy skill này trong repo.")

        for entry in entries:
            try:
                fetched = await asyncio.to_thread(self._download_skill_text, entry["download_url"])
                if not self._looks_like_skill_text(fetched["text"], entry["path"]):
                    skipped.append(f"{entry['path']}: nội dung không giống skill.")
                    continue

                base_name = self._name_from_path(entry["path"]) or self._name_from_url(entry["download_url"]) or "Skill mới"
                final_name = f"{name_prefix} / {base_name}" if name_prefix else base_name
                signature = self._skill_signature(final_name, fetched["text"])
                if signature in existing_signatures:
                    skipped.append(f"{entry['path']}: đã có trong thư viện.")
                    continue

                summary = summary_prefix or f"Tự tải từ {entry['html_url']}"
                skill = await self.create_skill(self._build_imported_skill_request(final_name, summary, fetched["text"], entry["path"]))
                imported.append(skill)
                existing_signatures.add(signature)
            except HTTPException as exc:
                skipped.append(f"{entry['path']}: {exc.detail}")
            except Exception as exc:
                skipped.append(f"{entry['path']}: {exc}")

        if not imported:
            raise HTTPException(
                status_code=400,
                detail="Bot chưa import được skill nào từ repo/thư mục này. Hãy thử dùng thư mục chứa các file skill rõ ràng hơn.",
            )

        return {
            "items": imported,
            "imported_count": len(imported),
            "skipped_count": len(skipped),
            "skipped": skipped[:12],
            "mode": "batch",
            "source_url": source["source_url"],
        }

    def _resolve_skill_import_request(self, request: SkillImportRequest) -> SkillImportRequest:
        raw_source = request.url.strip()
        command = request.command.strip()
        name = request.name.strip()
        summary = request.summary.strip()
        selected_skills = self._normalize_selected_skills(request.skills)

        parsed_command: Dict[str, Any] = {}
        command_input = command or (raw_source if self._looks_like_skill_add_command(raw_source) else "")
        if command_input:
            parsed_command = self._parse_skill_add_command(command_input)
            raw_source = parsed_command.get("url", "") or raw_source
            selected_skills = self._normalize_selected_skills(parsed_command.get("skills", []) + selected_skills)
            if not name:
                name = parsed_command.get("name", "")
            if not summary:
                summary = parsed_command.get("summary", "")

        raw_source = self._normalize_skill_source_input(raw_source)

        return SkillImportRequest(
            url=raw_source,
            command=command_input,
            name=name,
            summary=summary,
            skills=selected_skills,
        )

    def _build_imported_skill_request(
        self,
        name: str,
        summary: str,
        skill_text: str,
        source_hint: str,
        *,
        source_repo: str = "",
        source_path: str = "",
        source_url: str = "",
        is_builtin: bool = False,
    ) -> SkillCreateRequest:
        if self._looks_like_instructional_skill_doc(skill_text, source_hint):
            inferred_type = self._infer_skill_type_from_hint(f"{name}\n{source_hint}") or "video"
            return SkillCreateRequest(
                name=name,
                summary=summary,
                skill_text=skill_text,
                source_repo=source_repo,
                source_path=source_path,
                source_url=source_url,
                is_builtin=is_builtin,
                type=inferred_type,
                prompt="",
                aspect="landscape",
                count=1,
                reference_media_names=[],
                media_id="",
                workflow_id="",
                motion="",
                position="",
                resolution="1080p",
                mask_x=0.5,
                mask_y=0.5,
                brush_size=40,
            )

        return SkillCreateRequest(
            name=name,
            summary=summary,
            skill_text=skill_text,
            source_repo=source_repo,
            source_path=source_path,
            source_url=source_url,
            is_builtin=is_builtin,
        )

    async def delete_skill(self, skill_id: str) -> None:
        deleted = await self.store.delete_skill(skill_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Không tìm thấy kỹ năng.")

    async def download_artifact(self, job_id: str, request: DownloadRequest) -> Dict[str, Any]:
        job, artifact = self._get_artifact_or_raise(job_id, request.artifact_index)
        source = artifact.url
        if not source:
            raise HTTPException(status_code=400, detail="Kết quả này chưa có liên kết tải xuống.")

        file_name = self._download_name(job, artifact, request.artifact_index)
        destination = self._download_root() / file_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        await self.store.append_log(job_id, f"Đang lưu kết quả vào {destination.name}")

        async def _go(client: Any) -> str:
            saved = await client.download(source, destination)
            return str(saved)

        job_input = job.input if isinstance(job.input, dict) else {}
        local_path = await self._with_client(_go, workflow_id=artifact.workflow_id or job_input.get("workflow_id", ""))
        artifact.local_path = local_path
        artifact.public_url = self._public_download_url(local_path)
        await self.store.replace_artifacts(job_id, job.artifacts)
        return {
            "path": local_path,
            "public_url": artifact.public_url,
        }

    async def open_artifact(self, job_id: str, request: ArtifactOpenRequest) -> Dict[str, str]:
        job, artifact = self._get_artifact_or_raise(job_id, request.artifact_index)
        target = str(request.target or "best").strip().lower() or "best"
        if target not in {"best", "local", "source"}:
            raise HTTPException(status_code=400, detail="Kiểu mở artifact không hợp lệ.")

        source_url = str(artifact.url or "").strip()
        local_error: HTTPException | None = None

        if target in {"best", "local"} and str(artifact.local_path or "").strip():
            try:
                self._artifact_local_path(artifact)
            except HTTPException as exc:
                local_error = exc
            else:
                return {
                    "url": self._artifact_file_url(job.id, request.artifact_index),
                    "label": "Mở tệp đã lưu",
                    "target": "local",
                }

        if target in {"best", "source"} and source_url:
            return {
                "url": source_url,
                "label": "Mở liên kết gốc",
                "target": "source",
            }

        if local_error is not None:
            raise local_error
        if target == "local":
            raise HTTPException(status_code=400, detail="Artifact này chưa có tệp local đã lưu.")
        if target == "source":
            raise HTTPException(status_code=400, detail="Artifact này chưa có liên kết gốc để mở.")
        raise HTTPException(status_code=400, detail="Artifact này chưa có liên kết để mở.")

    def artifact_file_path(self, job_id: str, artifact_index: int) -> Path:
        _, artifact = self._get_artifact_or_raise(job_id, artifact_index)
        return self._artifact_local_path(artifact)

    async def cleanup_replay_pack(self, request: ReplayCleanupRequest) -> Dict[str, Any]:
        cleared_job_ids = await self.store.clear_replay_metadata(request.job_ids)
        return {
            "cleared_job_ids": cleared_job_ids,
            "replay_pack": self._build_replay_pack(self.store.snapshot().jobs),
        }

    async def cleanup_scope(self, request: CleanupRequest) -> Dict[str, Any]:
        scope = str(request.scope or "").strip().lower()
        snapshot = self.store.snapshot()
        config = self._normalized_config(snapshot.config)
        output_shelf = self._build_output_shelf(snapshot.jobs)
        _, plans = self._build_cleanup_assistant(config, snapshot.jobs, output_shelf)
        plan = plans.get(scope)
        if plan is None:
            raise HTTPException(status_code=400, detail="Nhóm cleanup không hợp lệ.")

        deleted_paths: List[str] = []
        freed_bytes = 0
        cleared_refs: List[Dict[str, Any]] = []
        removed_job_ids: List[str] = []

        if scope == "uploads":
            for path in plan["paths"]:
                freed_bytes += self._file_size(path)
                deleted_paths.append(self._delete_cleanup_file(path, [UPLOADS_DIR.resolve()]))
        elif scope == "downloads":
            deleted_reference_keys: set[str] = set()
            download_roots = self._download_cleanup_roots()
            for path in plan["paths"]:
                freed_bytes += self._file_size(path)
                deleted_paths.append(self._delete_cleanup_file(path, download_roots))
                deleted_reference_keys.add(str(path))

            artifact_refs: List[tuple[str, int]] = []
            for path_key, refs in plan["artifact_refs"].items():
                if path_key not in deleted_reference_keys:
                    continue
                artifact_refs.extend(refs)
            if artifact_refs:
                cleared_refs = await self.store.clear_artifact_local_refs(artifact_refs)
        elif scope == "history":
            removed_job_ids = await self.store.remove_jobs(plan["job_ids"])

        fresh_snapshot = self.store.snapshot()
        fresh_output_shelf = self._build_output_shelf(fresh_snapshot.jobs)
        cleanup_assistant, _ = self._build_cleanup_assistant(config, fresh_snapshot.jobs, fresh_output_shelf)
        return {
            "scope": scope,
            "deleted_count": len(deleted_paths) + len(removed_job_ids),
            "deleted_paths": deleted_paths,
            "freed_bytes": freed_bytes,
            "cleared_artifact_refs": cleared_refs,
            "removed_job_ids": removed_job_ids,
            "cleanup_assistant": cleanup_assistant,
        }

    async def _set_job_progress(
        self,
        job_id: str,
        stage: str,
        detail: str,
        *,
        remote_status: str = "",
    ) -> None:
        await self.store.set_progress_hint(
            job_id,
            stage=stage,
            detail=detail,
            remote_status=remote_status,
        )

    async def _launch_login_browser(self, job_id: str) -> Any:
        self._assert_windows_interactive_browser_session("đăng nhập Google Flow")
        await self.store.patch_job(job_id, status="running")
        await self._set_job_progress(job_id, "launching_browser", "Em đang mở Chromium để đi tới Google Flow.")
        await self.store.append_log(job_id, "Đang mở Chromium để đăng nhập Google Flow")
        async with self._browser_session_lock:
            browser = await self._ensure_shared_browser()
            page = await self._open_login_flow_page(browser)
        await self._set_job_progress(
            job_id,
            "awaiting_login",
            "Chromium đã mở. Đang chờ hoàn tất đăng nhập Google Flow.",
        )
        await self.store.append_log(
            job_id,
            "Nếu chưa thấy tab hiện ra, hãy kiểm tra cửa sổ Chromium/Chrome for Testing vừa được mở trên màn hình."
            if os.name != "nt"
            else "Nếu chưa thấy tab hiện ra, hãy tìm cửa sổ 'Flow - Google Chrome for Testing' trên taskbar hoặc màn hình Windows.",
        )
        return page

    async def _wait_for_login_completion(self, job_id: str, page: Any) -> None:
        try:
            config = self._normalized_config(self.store.snapshot().config)
            email = None
            deadline = time.monotonic() + 900
            while time.monotonic() < deadline:
                if getattr(page, "is_closed", lambda: False)():
                    raise RuntimeError("Cửa sổ đăng nhập đã bị đóng trước khi hoàn tất.")
                if "accounts.google.com" not in page.url:
                    email = await page.evaluate(
                        """
                        () => window.__NEXT_DATA__?.props?.pageProps?.session?.user?.email || null
                        """
                    )
                    if email:
                        break
                await asyncio.sleep(2)
            if not email:
                raise RuntimeError("Hết thời gian chờ đăng nhập Google Flow.")
            if config.project_id:
                await page.goto(self._project_url(config.project_id), wait_until="domcontentloaded")
                await asyncio.sleep(1.5)
            await self.store.append_log(job_id, "Em sẽ giữ nguyên tab Google Flow này để dùng tiếp cho các lượt chạy sau.")
            await self.store.append_log(job_id, f"Đã đăng nhập với tài khoản {email}")
            await self.store.patch_job(job_id, status="completed", result={"email": email})
        except Exception as exc:
            detail = self._flow_error_detail(exc)
            await self.store.patch_job(job_id, status="failed", error=detail)
            await self.store.append_log(job_id, f"Đăng nhập thất bại: {detail}")

    async def _open_login_flow_page(self, browser: Any) -> Any:
        context = getattr(browser, "context", None)
        target_url = "https://labs.google/fx/vi/tools/flow"
        page = None
        if context is not None:
            try:
                page = await context.new_page()
            except Exception:
                page = None
        if page is None:
            page = await browser.page()
        try:
            browser._page = page
        except Exception:
            pass
        try:
            await page.bring_to_front()
        except Exception:
            pass
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60_000)
        except Exception:
            await page.goto(target_url, wait_until="commit", timeout=60_000)
        try:
            await page.bring_to_front()
        except Exception:
            pass
        try:
            await page.evaluate(
                """
                () => {
                  try { window.focus(); } catch (error) {}
                  return true;
                }
                """
            )
        except Exception:
            pass
        await self._foreground_native_flow_window()
        await asyncio.sleep(1.5)
        return page

    async def _foreground_native_flow_window(self) -> None:
        if os.name != "nt":
            return
        await asyncio.to_thread(self._foreground_native_flow_window_sync)

    def _assert_windows_interactive_browser_session(self, action: str) -> None:
        if os.name != "nt":
            return
        session_id = self._current_windows_session_id()
        if session_id == 0:
            raise HTTPException(
                status_code=400,
                detail=(
                "Flow Web UI đang chạy trong session nền của Windows (Session 0), thường là do mở app qua SSH, "
                "tác vụ nền hoặc Task Scheduler. Kiểu này không thể bật cửa sổ để "
                f"{action}. Hãy mở Flow Web UI trực tiếp trên desktop Windows rồi thử lại."
                ),
            )

    def _current_windows_session_id(self) -> int | None:
        if os.name != "nt":
            return None
        try:
            kernel32 = ctypes.windll.kernel32
            process_id = kernel32.GetCurrentProcessId()
            session_id = ctypes.c_uint()
            if kernel32.ProcessIdToSessionId(process_id, ctypes.byref(session_id)):
                return int(session_id.value)
        except Exception:
            pass

        session_name = str(os.environ.get("SESSIONNAME", "") or "").strip().lower()
        if session_name in {"services", "service"}:
            return 0
        if session_name.startswith("console"):
            return 1
        return None

    def _foreground_native_flow_window_sync(self) -> None:
        if os.name != "nt":
            return
        script = r"""
Add-Type -AssemblyName Microsoft.VisualBasic
$deadline = (Get-Date).AddSeconds(10)
while ((Get-Date) -lt $deadline) {
  $window = Get-Process chrome -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Sort-Object StartTime -Descending |
    Select-Object -First 1
  if ($window) {
    try {
      [Microsoft.VisualBasic.Interaction]::AppActivate($window.Id) | Out-Null
      exit 0
    } catch {
    }
  }
  foreach ($title in @('Flow - Google Chrome for Testing', 'Google Chrome for Testing', 'Flow')) {
    try {
      [Microsoft.VisualBasic.Interaction]::AppActivate($title) | Out-Null
      exit 0
    } catch {
    }
  }
  Start-Sleep -Milliseconds 350
}
exit 1
"""
        kwargs: Dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "timeout": 15,
            "check": False,
        }
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if creationflags:
            kwargs["creationflags"] = creationflags
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                **kwargs,
            )
        except Exception:
            return

    async def _run_flow_job(self, job_id: str, request: CreateJobRequest) -> None:
        await self.store.patch_job(job_id, status="running")
        await self._set_job_progress(job_id, "connecting", "Em đang khởi tạo client và kết nối tới project Flow hiện tại.")
        await self.store.append_log(job_id, "Đang khởi tạo kết nối tới Flow")
        artifacts: List[JobArtifact] = []
        result: Dict[str, Any] = {}

        async def _execute(client: Any) -> Dict[str, Any]:
            config = self.store.snapshot().config
            poll_s = config.poll_interval_s
            timeout_s = max(30, int(request.timeout_s or config.generation_timeout_s))

            if request.type == "video":
                requested_count = max(1, int(request.count or 1))
                if request.start_image_path:
                    send_timeout_s = timeout_s
                else:
                    send_timeout_s = max(30, min(timeout_s, 90 * requested_count))
                if request.start_image_path:
                    await self.store.append_log(job_id, "Đang chuẩn bị tải ảnh đầu vào và gắn vào ô Start.")
                    await self._set_job_progress(
                        job_id,
                        "sending_request",
                        "Em đang tải ảnh đầu vào lên Flow rồi mới gửi yêu cầu tạo video.",
                    )
                else:
                    await self._set_job_progress(job_id, "sending_request", "Em đang gửi yêu cầu tạo video tới Flow.")

                try:
                    jobs = await asyncio.wait_for(
                        client.generate_video(
                            request.prompt,
                            model=self._normalize_video_model(request.model),
                            aspect=request.aspect,
                            count=request.count,
                            start_image=request.start_image_path or None,
                            timeout_s=timeout_s,
                        ),
                        timeout=send_timeout_s,
                    )
                except asyncio.TimeoutError as exc:
                    raise RuntimeError(
                        f"Google Flow chưa gửi được yêu cầu tạo video sau {send_timeout_s} giây. "
                        "Có thể Flow đang kẹt ở bước tải ảnh, gắn ảnh vào Start hoặc bấm Create."
                    ) from exc
                if not jobs:
                    raise RuntimeError("Google Flow chưa khởi tạo được clip video nào từ yêu cầu này.")
                if len(jobs) < requested_count:
                    raise RuntimeError(
                        f"Google Flow chỉ khởi tạo {len(jobs)}/{requested_count} clip trong lượt gửi này. "
                        "Em không tự bấm gửi thêm để tránh tạo dư clip ngoài ý muốn. Hãy thử chạy lại."
                    )
                await self.store.append_log(job_id, f"Đã gửi {len(jobs)} tác vụ tạo video")
                await self._set_job_progress(
                    job_id,
                    "awaiting_response",
                    "Flow đã nhận yêu cầu tạo video. Đang chờ tín hiệu tiến trình đầu tiên.",
                )
                statuses = await asyncio.gather(
                    *[
                        self._wait_for_video_with_progress(
                            client,
                            job_id,
                            job,
                            f"Video {index + 1}",
                            poll_s=poll_s,
                            timeout_s=timeout_s,
                        )
                        for index, job in enumerate(jobs)
                    ]
                )
                return {
                    "video_jobs": jobs,
                    "statuses": statuses,
                }

            if request.type == "image":
                reference_media_names = await self._resolve_image_reference_media(client, job_id, request)
                all_reference_media_names = reference_media_names or list(request.reference_media_names or [])
                if all_reference_media_names:
                    await self._set_job_progress(
                        job_id,
                        "sending_request",
                        f"Em đang gửi yêu cầu chỉnh ảnh với {len(all_reference_media_names)} ảnh tham chiếu tới Flow.",
                    )
                else:
                    await self._set_job_progress(job_id, "sending_request", "Em đang gửi yêu cầu tạo ảnh tới Flow.")

                images = await self._generate_images_with_retry(
                    client,
                    job_id,
                    request,
                    all_reference_media_names,
                )
                await self.store.append_log(job_id, f"Đã tạo {len(images)} ảnh")
                await self._set_job_progress(
                    job_id,
                    "saving_artifacts",
                    f"Flow đã trả về {len(images)} ảnh. Em đang lưu artifact vào lịch sử tác vụ.",
                )
                return {"images": images}

            if request.type == "extend":
                await self._set_job_progress(job_id, "sending_request", "Em đang gửi lệnh kéo dài video tới Flow.")
                job = await client.extend_video(
                    request.media_id,
                    workflow_id=request.workflow_id or None,
                    prompt=request.prompt,
                    timeout_s=timeout_s,
                )
                await self.store.append_log(job_id, f"Đã gửi lệnh kéo dài video cho {request.media_id}")
                await self._set_job_progress(
                    job_id,
                    "awaiting_response",
                    "Flow đã nhận lệnh kéo dài video. Đang chờ tín hiệu tiến trình đầu tiên.",
                )
                status = await self._wait_for_video_with_progress(
                    client,
                    job_id,
                    job,
                    "Tác vụ kéo dài video",
                    poll_s=poll_s,
                    timeout_s=timeout_s,
                )
                return {"video_job": job, "status": status}

            if request.type == "upscale":
                await self._set_job_progress(job_id, "sending_request", "Em đang gửi lệnh nâng chất lượng tới Flow.")
                job = await client.upscale_video(
                    request.media_id,
                    workflow_id=request.workflow_id or None,
                    resolution=request.resolution,
                    timeout_s=timeout_s,
                )
                await self.store.append_log(job_id, f"Đã gửi lệnh nâng chất lượng cho {request.media_id}")
                await self._set_job_progress(
                    job_id,
                    "awaiting_response",
                    "Flow đã nhận lệnh nâng chất lượng. Đang chờ tín hiệu tiến trình đầu tiên.",
                )
                status = await self._wait_for_video_with_progress(
                    client,
                    job_id,
                    job,
                    "Tác vụ nâng chất lượng",
                    poll_s=poll_s,
                    timeout_s=timeout_s,
                )
                return {"video_job": job, "status": status}

            if request.type == "camera_motion":
                await self._set_job_progress(job_id, "sending_request", "Em đang gửi lệnh chuyển động camera tới Flow.")
                job = await client.camera_motion(
                    request.media_id,
                    request.motion,
                    workflow_id=request.workflow_id or None,
                    timeout_s=timeout_s,
                )
                await self.store.append_log(job_id, f"Đã gửi chuyển động camera {request.motion}")
                await self._set_job_progress(
                    job_id,
                    "awaiting_response",
                    "Flow đã nhận lệnh chuyển động camera. Đang chờ tín hiệu tiến trình đầu tiên.",
                )
                status = await self._wait_for_video_with_progress(
                    client,
                    job_id,
                    job,
                    "Tác vụ chuyển động camera",
                    poll_s=poll_s,
                    timeout_s=timeout_s,
                )
                return {"video_job": job, "status": status}

            if request.type == "camera_position":
                await self._set_job_progress(job_id, "sending_request", "Em đang gửi lệnh đổi vị trí camera tới Flow.")
                job = await client.camera_position(
                    request.media_id,
                    request.position,
                    workflow_id=request.workflow_id or None,
                    timeout_s=timeout_s,
                )
                await self.store.append_log(job_id, f"Đã gửi vị trí camera {request.position}")
                await self._set_job_progress(
                    job_id,
                    "awaiting_response",
                    "Flow đã nhận lệnh vị trí camera. Đang chờ tín hiệu tiến trình đầu tiên.",
                )
                status = await self._wait_for_video_with_progress(
                    client,
                    job_id,
                    job,
                    "Tác vụ vị trí camera",
                    poll_s=poll_s,
                    timeout_s=timeout_s,
                )
                return {"video_job": job, "status": status}

            if request.type == "insert":
                await self._set_job_progress(job_id, "sending_request", "Em đang gửi lệnh chèn vật thể tới Flow.")
                job = await client.insert_object(
                    request.media_id,
                    request.prompt,
                    workflow_id=request.workflow_id or None,
                    timeout_s=timeout_s,
                )
                await self.store.append_log(job_id, f"Đã gửi lệnh chèn vật thể cho {request.media_id}")
                await self._set_job_progress(
                    job_id,
                    "awaiting_response",
                    "Flow đã nhận lệnh chèn vật thể. Đang chờ tín hiệu tiến trình đầu tiên.",
                )
                status = await self._wait_for_video_with_progress(
                    client,
                    job_id,
                    job,
                    "Tác vụ chèn vật thể",
                    poll_s=poll_s,
                    timeout_s=timeout_s,
                )
                return {"video_job": job, "status": status}

            if request.type == "remove":
                await self._set_job_progress(job_id, "sending_request", "Em đang gửi lệnh xóa vật thể tới Flow.")
                job = await client.remove_object(
                    request.media_id,
                    workflow_id=request.workflow_id or None,
                    mask_x=request.mask_x,
                    mask_y=request.mask_y,
                    brush_size=request.brush_size,
                    timeout_s=timeout_s,
                )
                await self.store.append_log(job_id, f"Đã gửi lệnh xóa vật thể cho {request.media_id}")
                await self._set_job_progress(
                    job_id,
                    "awaiting_response",
                    "Flow đã nhận lệnh xóa vật thể. Đang chờ tín hiệu tiến trình đầu tiên.",
                )
                status = await self._wait_for_video_with_progress(
                    client,
                    job_id,
                    job,
                    "Tác vụ xóa vật thể",
                    poll_s=poll_s,
                    timeout_s=timeout_s,
                )
                return {"video_job": job, "status": status}

            raise ValueError(f"Loại tác vụ chưa được hỗ trợ: {request.type}")

        try:
            payload = await self._with_client(
                _execute,
                workflow_id=request.workflow_id,
                timeout_s=request.timeout_s,
            )
            if request.type == "image":
                images = payload["images"]
                artifacts = [
                    JobArtifact(
                        label=f"Ảnh {index + 1}",
                        media_name=getattr(image, "media_name", ""),
                        url=getattr(image, "fife_url", ""),
                        workflow_id=getattr(image, "workflow_id", request.workflow_id),
                        mime_type="image/jpeg",
                        prompt=getattr(image, "prompt", request.prompt),
                        dimensions=getattr(image, "dimensions", {}) or {},
                    )
                    for index, image in enumerate(images)
                ]
                result = {
                    "count": len(artifacts),
                    "mode": "image",
                }
            elif request.type == "video":
                video_jobs = payload["video_jobs"]
                statuses = payload["statuses"]
                artifacts, missing_labels = self._build_video_artifacts(video_jobs, statuses, request)
                if not artifacts:
                    raise RuntimeError(
                        "Google Flow báo đã hoàn tất nhưng chưa trả clip video nào về cho ứng dụng. Hãy thử chạy lại."
                    )
                if missing_labels:
                    await self.store.append_log(
                        job_id,
                        f"Flow chưa trả clip cho {len(missing_labels)} mục: {', '.join(missing_labels[:4])}. Em chỉ lưu các clip đã có thật.",
                    )
                result = {
                    "count": len(artifacts),
                    "mode": "video",
                    "missing_count": len(missing_labels),
                }
            else:
                job = payload["video_job"]
                status = payload["status"]
                artifacts, missing_labels = self._build_video_artifacts([job], [status], request, default_label=self._default_title(request))
                if not artifacts:
                    raise RuntimeError(
                        "Google Flow báo đã hoàn tất nhưng chưa trả clip video nào về cho ứng dụng. Hãy thử chạy lại."
                    )
                result = {
                    "media_name": getattr(job, "media_name", ""),
                    "mode": "video",
                    "missing_count": len(missing_labels),
                }

            await self._set_job_progress(
                job_id,
                "saving_artifacts",
                f"Đang lưu {len(artifacts)} artifact vào lịch sử tác vụ.",
            )
            await self.store.replace_artifacts(job_id, artifacts)
            await self.store.patch_job(job_id, status="completed", result=result)
            await self.store.append_log(job_id, "Tác vụ đã hoàn tất")
        except HTTPException as exc:
            detail = self._flow_error_detail(exc)
            await self.store.patch_job(job_id, status="failed", error=detail)
            await self.store.append_log(job_id, f"Tác vụ thất bại: {detail}")
        except Exception as exc:
            detail = self._flow_error_detail(exc)
            await self.store.patch_job(job_id, status="failed", error=detail)
            await self.store.append_log(job_id, f"Tác vụ thất bại: {detail}")

    def _build_video_artifacts(
        self,
        video_jobs: List[Any],
        statuses: List[Any],
        request: CreateJobRequest,
        *,
        default_label: str = "",
    ) -> tuple[List[JobArtifact], List[str]]:
        artifacts: List[JobArtifact] = []
        missing_labels: List[str] = []

        for index, (job, status) in enumerate(zip(video_jobs, statuses)):
            label = default_label or f"Video {index + 1}"
            media_name = str(getattr(job, "media_name", "") or "").strip()
            url = self._video_status_url(status, media_name=media_name)
            if not url:
                missing_labels.append(label)
                continue

            artifacts.append(
                JobArtifact(
                    label=label,
                    media_name=media_name,
                    url=url,
                    workflow_id=getattr(job, "workflow_id", request.workflow_id),
                    mime_type="video/mp4",
                    prompt=request.prompt,
                )
            )

        return artifacts, missing_labels

    def _video_status_url(self, status: Any, *, media_name: str = "") -> str:
        candidates = (
            getattr(status, "fife_url", ""),
            getattr(status, "download_url", ""),
            getattr(status, "url", ""),
        )
        for candidate in candidates:
            value = str(candidate or "").strip()
            if value:
                return value
        raw_status = getattr(status, "_raw", {}) or {}
        raw_media = raw_status.get("media", []) if isinstance(raw_status, dict) else []
        for media_item in raw_media or []:
            if not isinstance(media_item, dict):
                continue
            video_payload = media_item.get("video", {})
            if not isinstance(video_payload, dict):
                continue
            generated = video_payload.get("generatedVideo", {})
            if isinstance(generated, dict):
                for key in ("fifeUrl", "downloadUrl", "url"):
                    value = str(generated.get(key) or "").strip()
                    if value:
                        return value
                output_video = generated.get("outputVideo", {})
                if isinstance(output_video, dict):
                    for key in ("fifeUrl", "downloadUrl", "url"):
                        value = str(output_video.get(key) or "").strip()
                        if value:
                            return value
        fallback_media_name = str(media_name or getattr(status, "media_name", "") or "").strip()
        if fallback_media_name:
            return f"https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name={quote(fallback_media_name)}"
        return ""

    async def _with_client(
        self,
        fn: Callable[[Any], Any],
        workflow_id: str = "",
        timeout_s: int = 0,
    ) -> Any:
        FlowClient, _, _, _, _ = self._flow_modules(client_only=True)
        config = self._normalized_config(self.store.snapshot().config)
        if not config.project_id:
            raise HTTPException(status_code=400, detail="Mã project là bắt buộc.")
        effective_timeout_s = max(30, int(timeout_s or config.generation_timeout_s))
        resolved_workflow_id = workflow_id or config.active_workflow_id or None

        if self._should_keep_flow_browser_open(config):
            async with self._browser_session_lock:
                try:
                    browser = await self._ensure_shared_browser()
                    client = await self._build_client_from_shared_browser(
                        browser,
                        project_id=config.project_id,
                        workflow_id=resolved_workflow_id,
                        timeout_s=effective_timeout_s,
                    )
                    return await fn(client)
                except HTTPException:
                    raise
                except Exception as exc:
                    if self._is_browser_closed_error(exc):
                        await self._close_shared_browser()
                    raise HTTPException(
                        status_code=self._flow_error_status(exc),
                        detail=self._flow_error_detail(exc),
                    ) from exc

        try:
            client = await FlowClient.create(
                project_id=config.project_id,
                workflow_id=resolved_workflow_id,
                headless=config.headless,
                cdp_url=config.cdp_url or None,
                timeout_s=effective_timeout_s,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=self._flow_error_status(exc),
                detail=self._flow_error_detail(exc),
            ) from exc
        try:
            return await fn(client)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=self._flow_error_status(exc),
                detail=self._flow_error_detail(exc),
            ) from exc
        finally:
            await client.close()

    def _should_keep_flow_browser_open(self, config: AppConfig) -> bool:
        return not config.headless and not config.cdp_url

    async def _close_shared_browser(self) -> None:
        browser = self._shared_browser
        self._shared_browser = None
        if browser is None:
            return
        try:
            await browser.stop()
        except Exception:
            pass

    async def _shared_browser_is_usable(self) -> bool:
        browser = self._shared_browser
        if browser is None or getattr(browser, "_ctx", None) is None:
            return False
        try:
            page = await browser.page()
            if page.is_closed():
                return False
            await page.evaluate("() => document.readyState")
            return True
        except Exception:
            return False

    async def _ensure_shared_browser(self) -> Any:
        if await self._shared_browser_is_usable():
            return self._shared_browser
        await self._close_shared_browser()
        BrowserManager, _, _, _, _ = self._flow_modules()
        browser = BrowserManager(headless=False)
        await browser.start()
        config = self.store.snapshot().config
        project_id = self._normalize_project_id(config.project_id or config.project_url)
        target_url = self._project_url(project_id) if project_id else "https://labs.google/fx/tools/flow"
        await self._close_placeholder_flow_tabs(browser, target_url)
        self._shared_browser = browser
        return browser

    async def _build_client_from_shared_browser(
        self,
        browser: Any,
        *,
        project_id: str,
        workflow_id: str | None,
        timeout_s: int,
    ) -> Any:
        self._patch_flow_runtime_compat()
        from flow._api import FlowAPI
        from flow._client import FlowClient

        api = FlowAPI(browser, project_id=project_id, default_timeout_s=timeout_s)
        client = FlowClient(api, browser, project_id, workflow_id)
        client.workflow_id = workflow_id
        client._project_url = self._project_url(project_id)

        target_url = client._project_url
        await self._repair_placeholder_flow_tabs(browser, target_url)
        page = await self._acquire_fresh_flow_page(browser, target_url)
        await self._ensure_valid_flow_project_page(page, target_url)
        return client

    def _is_browser_closed_error(self, exc: Exception) -> bool:
        detail = str(exc or "").lower()
        needles = (
            "target page, context or browser has been closed",
            "browser has been closed",
            "context closed",
            "page closed",
        )
        return any(needle in detail for needle in needles)

    def _sync_project_to_flow_storage(self, config: AppConfig) -> None:
        project_id = self._normalize_project_id(config.project_id or config.project_url)
        if not project_id:
            return
        _, _, _, _, sync_project = self._flow_modules()
        sync_project(project_id, config.project_name or "web-ui", self._project_url(project_id))

    def _flow_modules(
        self,
        client_only: bool = False,
    ) -> Any:
        self._patch_flow_runtime_compat()
        from flow._client import FlowClient

        if client_only:
            return FlowClient, None, None, None, None

        from flow._browser import BrowserManager
        from flow._storage import add_project, get_active_project, is_authenticated, load_projects, set_active_project

        def sync_project(project_id: str, project_name: str, project_url: str) -> None:
            set_active_project(project_id, project_url)
            add_project(project_id, project_name, project_url)

        return BrowserManager, is_authenticated, load_projects, get_active_project, sync_project

    def _patch_flow_runtime_compat(self) -> None:
        if self.__class__._FLOW_RUNTIME_PATCHED:
            return

        from flow._api import FlowAPI, GeneratedImage, VideoJob, RECAPTCHA_SITE_KEY
        from flow._client import FlowClient
        from flow._flow_ui import FlowUI
        from flow._models import AspectRatio, GenerationMode
        from flow._ui_interceptor import UIInterceptor

        async def _compat_settings_visible(_self: Any, page: Any) -> bool:
            return bool(await page.evaluate(
                """
                () => {
                  const menus = [...document.querySelectorAll('[role="menu"]')];
                  return menus.some(el => {
                    const style = window.getComputedStyle(el);
                    const text = (el.textContent || '').trim().toLowerCase();
                    return style.display !== 'none'
                      && style.visibility !== 'hidden'
                      && (text.includes('image') || text.includes('hình ảnh') || text.includes('hinh anh'))
                      && text.includes('video')
                      && /x[1-4]/.test(text);
                  });
                }
                """
            ))

        async def _compat_find_create_options_trigger_index(page: Any) -> int:
            index = await page.evaluate(
                """
                () => {
                  const buttons = [...document.querySelectorAll('button[aria-haspopup="menu"]')];
                  const candidates = buttons
                    .map((button, index) => {
                      const text = (button.textContent || '').trim();
                      const rect = button.getBoundingClientRect();
                      const style = window.getComputedStyle(button);
                      return {
                        index,
                        text,
                        top: rect.top,
                        visible: rect.width > 0
                          && rect.height > 0
                          && style.display !== 'none'
                          && style.visibility !== 'hidden',
                      };
                    })
                    .filter(item => item.visible && /(x[1-4]|Nano Banana|Veo|Imagen|Video|Image|🍌)/i.test(item.text))
                    .sort((a, b) => a.top - b.top);
                  return candidates.length ? candidates[candidates.length - 1].index : -1;
                }
                """
            )
            try:
                return int(index)
            except Exception:
                return -1

        async def _compat_find_tabbed_menu_index(page: Any) -> int:
            index = await page.evaluate(
                """
                () => {
                  const menus = [...document.querySelectorAll('[role="menu"]')];
                  const candidates = menus
                    .map((menu, index) => {
                      const style = window.getComputedStyle(menu);
                      const rect = menu.getBoundingClientRect();
                      const tabs = [...menu.querySelectorAll('[role="tab"]')].filter((tab) => {
                        const tabStyle = window.getComputedStyle(tab);
                        const tabRect = tab.getBoundingClientRect();
                        return tabRect.width > 0
                          && tabRect.height > 0
                          && tabStyle.display !== 'none'
                          && tabStyle.visibility !== 'hidden';
                      });
                      return {
                        index,
                        top: rect.top,
                        visible: rect.width > 0
                          && rect.height > 0
                          && style.display !== 'none'
                          && style.visibility !== 'hidden',
                        tabCount: tabs.length,
                      };
                    })
                    .filter((item) => item.visible && item.tabCount > 0)
                    .sort((a, b) => a.top - b.top);
                  return candidates.length ? candidates[candidates.length - 1].index : -1;
                }
                """
            )
            try:
                return int(index)
            except Exception:
                return -1

        async def _compat_get_tabbed_menu(page: Any) -> Any | None:
            index = await _compat_find_tabbed_menu_index(page)
            if index < 0:
                return None
            return page.locator('[role="menu"]').nth(index)

        async def _compat_wait_for_new_call(
            interceptor: Any,
            start_index: int,
            endpoint_tail: str,
            *,
            timeout_s: float,
            fail_on_tails: Optional[List[str]] = None,
        ) -> Any:
            deadline = time.monotonic() + timeout_s
            seen_tails: List[str] = []
            fail_on = [str(item or "") for item in (fail_on_tails or []) if str(item or "")]
            best_match = None
            settle_deadline = 0.0

            def _response_weight(call: Any) -> int:
                if not isinstance(getattr(call, "resp", None), dict):
                    return 0
                resp = call.resp or {}
                return (
                    len(resp.get("jobs", []) or [])
                    + len(resp.get("media", []) or [])
                    + len(resp.get("workflows", []) or [])
                )

            while time.monotonic() < deadline:
                completed = [
                    call
                    for call in getattr(interceptor, "_calls", [])[start_index:]
                    if call.resp is not None
                ]
                if completed:
                    seen_tails = [str(call.tail or "") for call in completed]
                for call in reversed(completed):
                    tail = str(call.tail or "")
                    if any(fragment in tail for fragment in fail_on):
                        raise RuntimeError(
                            "Google Flow đã gửi nhầm endpoint cho thao tác hiện tại. "
                            f"Captured: {tail}"
                        )
                    if endpoint_tail not in tail:
                        continue
                    if call.status not in (200, 201):
                        message = ""
                        if isinstance(call.resp, dict):
                            message = str(((call.resp.get("error") or {}).get("message")) or "").strip()
                        raise RuntimeError(
                            f"{endpoint_tail} failed [{call.status}]: {message or tail}"
                        )
                    if best_match is None or _response_weight(call) >= _response_weight(best_match):
                        best_match = call
                        settle_deadline = time.monotonic() + 1.0
                if best_match is not None and time.monotonic() >= settle_deadline:
                    return best_match
                await asyncio.sleep(0.25)
            raise RuntimeError(
                f"Timed out ({timeout_s}s) waiting for {endpoint_tail}. Captured so far: {seen_tails}"
            )

        async def _compat_wait_for_video_submit_call(
            interceptor: Any,
            start_index: int,
            *,
            timeout_s: float,
            expect_start_image: bool,
        ) -> Any:
            deadline = time.monotonic() + timeout_s
            seen_tails: List[str] = []
            best_match = None
            settle_deadline = 0.0

            def _response_weight(call: Any) -> int:
                if not isinstance(getattr(call, "resp", None), dict):
                    return 0
                resp = call.resp or {}
                return (
                    len(resp.get("jobs", []) or [])
                    + len(resp.get("media", []) or [])
                    + len(resp.get("workflows", []) or [])
                )

            while time.monotonic() < deadline:
                completed = [
                    call
                    for call in getattr(interceptor, "_calls", [])[start_index:]
                    if call.resp is not None
                ]
                if completed:
                    seen_tails = [str(call.tail or "") for call in completed]

                for call in reversed(completed):
                    tail = str(call.tail or "")
                    normalized = tail.lower()
                    if "generatevideo" not in normalized:
                        continue
                    if call.status not in (200, 201):
                        continue
                    if expect_start_image and "text" in normalized:
                        raise RuntimeError(
                            "Google Flow đã gửi nhầm sang text-to-video. Ảnh đầu vào nhiều khả năng chưa được gắn vào Start."
                        )
                    if expect_start_image and not isinstance(getattr(call, "resp", None), dict):
                        continue
                    if expect_start_image and _response_weight(call) == 0:
                        continue
                    if best_match is None or _response_weight(call) >= _response_weight(best_match):
                        best_match = call
                        settle_deadline = time.monotonic() + 1.0

                if best_match is not None and time.monotonic() >= settle_deadline:
                    return best_match
                await asyncio.sleep(0.25)

            label = "image-to-video" if expect_start_image else "text-to-video"
            raise RuntimeError(
                f"Timed out ({timeout_s}s) waiting for {label} submit response. Captured so far: {seen_tails}"
            )

        async def _compat_click_menu_trigger(page: Any) -> bool:
            index = await _compat_find_create_options_trigger_index(page)
            if index < 0:
                return False
            trigger = page.locator('button[aria-haspopup="menu"]').nth(index)
            try:
                await trigger.click(force=True)
            except Exception:
                return False
            await asyncio.sleep(0.5)
            return True

        async def _compat_open_settings_panel(_self: Any, page: Any) -> bool:
            try:
                await page.wait_for_selector("button", timeout=8000)
            except Exception:
                pass
            await asyncio.sleep(0.5)

            if await _compat_settings_visible(_self, page):
                return True

            if await _compat_click_menu_trigger(page):
                await asyncio.sleep(1.0)
                if await _compat_settings_visible(_self, page):
                    return True

            return False

        async def _compat_click_menu_tab(page: Any, labels: List[str]) -> bool:
            menu = await _compat_get_tabbed_menu(page)
            if menu is None:
                return False
            for label in labels:
                wanted = str(label or "").strip().lower()
                tabs = menu.locator('[role="tab"]')
                count = await tabs.count()
                matched = False
                for index in range(count):
                    tab = tabs.nth(index)
                    try:
                        box = await tab.bounding_box()
                    except Exception:
                        box = None
                    if not box:
                        continue
                    text = str(await tab.text_content() or "").replace("\n", " ").strip().lower()
                    if wanted not in text:
                        continue
                    try:
                        await tab.click(force=True)
                    except Exception:
                        continue
                    matched = True
                    break
                if not matched:
                    continue
                await asyncio.sleep(0.45)
                selected_tabs = menu.locator('[role="tab"][aria-selected="true"]')
                selected_count = await selected_tabs.count()
                for selected_index in range(selected_count):
                    text = str(await selected_tabs.nth(selected_index).text_content() or "").replace("\n", " ").strip().lower()
                    if wanted in text:
                        return True
            return False

        async def _compat_click_visible_menu_item(page: Any, wanted: str) -> bool:
            wanted = str(wanted or "").strip().lower()
            items = page.locator('[role="menuitem"]')
            count = await items.count()
            for index in range(count):
                item = items.nth(index)
                try:
                    box = await item.bounding_box()
                except Exception:
                    box = None
                if not box:
                    continue
                text = str(await item.text_content() or "").replace("\n", " ").strip().lower()
                if wanted not in text:
                    continue
                try:
                    await item.click(force=True)
                    return True
                except Exception:
                    continue
            return False

        async def _compat_fill_prompt(_self: Any, page: Any, prompt: str) -> bool:
            prompt = str(prompt or "").strip()
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.2)
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.2)
            except Exception:
                pass

            best = None
            best_is_input = False
            best_y = -1.0
            for selector, is_input in (
                ('div[role="textbox"][contenteditable="true"]', False),
                ('div[data-slate-editor="true"][contenteditable="true"]', False),
                ('div[contenteditable="true"]', False),
                ('textarea', True),
                ('input[type="text"]', True),
            ):
                locator = page.locator(selector)
                count = await locator.count()
                for index in range(count):
                    candidate = locator.nth(index)
                    try:
                        box = await candidate.bounding_box()
                    except Exception:
                        box = None
                    if not box:
                        continue
                    if box["width"] < 240 or box["height"] < 18 or box["y"] < 300:
                        continue
                    if box["y"] >= best_y:
                        best = candidate
                        best_is_input = is_input
                        best_y = float(box["y"])

            if best is None:
                return False

            await best.scroll_into_view_if_needed()
            await asyncio.sleep(0.1)
            await best.click(force=True)
            await asyncio.sleep(0.2)

            if best_is_input:
                try:
                    await best.fill(prompt)
                except Exception:
                    return False
                try:
                    value = await best.input_value()
                except Exception:
                    value = await best.text_content()
                return prompt[:20] in str(value or "")

            try:
                await page.keyboard.press("Meta+a")
                await page.keyboard.press("Control+a")
                await asyncio.sleep(0.05)
                await page.keyboard.press("Backspace")
                await asyncio.sleep(0.05)
                await page.keyboard.insert_text(prompt)
                await asyncio.sleep(0.2)
                content = await best.text_content()
                if prompt[:20] in str(content or ""):
                    return True
            except Exception:
                pass

            try:
                injected = await best.evaluate(
                    """
                    (el, value) => {
                      el.focus();
                      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
                        el.value = value;
                      } else {
                        const paragraph = el.querySelector('[data-slate-node="element"]') || el.firstElementChild || el;
                        if (paragraph) {
                          paragraph.textContent = value;
                        }
                      }
                      el.dispatchEvent(new Event('input', { bubbles: true }));
                      el.dispatchEvent(new Event('change', { bubbles: true }));
                      return (el.textContent || el.value || '').trim();
                    }
                    """,
                    prompt,
                )
            except Exception:
                return False
            return prompt[:20] in str(injected or "")

        async def _compat_switch_mode(_self: Any, page: Any, mode: Any) -> bool:
            await _compat_open_settings_panel(_self, page)
            label_map = {
                GenerationMode.IMAGE: ["Image", "Hình ảnh", "Hinh anh"],
                GenerationMode.VIDEO: ["Video"],
                GenerationMode.FRAME_TO_VIDEO: ["Frames", "Frame", "Khung hình", "Khung"],
            }
            return await _compat_click_menu_tab(page, label_map.get(mode, []))

        async def _compat_set_aspect_ratio(_self: Any, page: Any, ratio: Any) -> bool:
            await _compat_open_settings_panel(_self, page)
            label_map = {
                AspectRatio.LANDSCAPE: ["16:9", "Landscape"],
                AspectRatio.PORTRAIT: ["9:16", "Portrait"],
                AspectRatio.SQUARE: ["1:1", "Square"],
            }
            return await _compat_click_menu_tab(page, label_map.get(ratio, []))

        async def _compat_set_count(_self: Any, page: Any, count: int) -> bool:
            await _compat_open_settings_panel(_self, page)
            return await _compat_click_menu_tab(page, [f"x{max(1, min(4, count))}"])

        async def _compat_get_video_model_selector(_self: Any, page: Any) -> str:
            await _compat_open_settings_panel(_self, page)
            menu = await _compat_get_tabbed_menu(page)
            if menu is None:
                return ""
            button = menu.locator('button[aria-haspopup="menu"]').first
            if await button.count() > 0:
                return str((await button.text_content()) or "").replace("arrow_drop_down", "").strip()
            for label in ["Veo", "Nano Banana", "Imagen"]:
                locator = menu.locator("button").filter(has_text=label).first
                if await locator.count() > 0:
                    return str((await locator.text_content()) or "").replace("arrow_drop_down", "").strip()
            return ""

        async def _compat_select_video_model(_self: Any, page: Any, model_display_name: str) -> bool:
            await _compat_open_settings_panel(_self, page)
            menu = await _compat_get_tabbed_menu(page)
            if menu is None:
                return False
            current = await _compat_get_video_model_selector(_self, page)
            wanted = str(model_display_name or "").strip()
            if wanted and wanted.lower() in current.lower():
                return True

            model_button = menu.locator('button[aria-haspopup="menu"]').first
            if await model_button.count() > 0:
                await model_button.click(force=True)
                await asyncio.sleep(0.5)

            if not wanted:
                return bool(await _compat_get_video_model_selector(_self, page))

            matched = await _compat_click_visible_menu_item(page, wanted)
            if matched:
                await asyncio.sleep(0.5)
                return True
            return False

        async def _compat_get_image_model_selector(_self: Any, page: Any) -> str:
            await _compat_open_settings_panel(_self, page)
            menu = await _compat_get_tabbed_menu(page)
            if menu is None:
                return ""
            button = menu.locator('button[aria-haspopup="menu"]').first
            if await button.count() > 0:
                return str((await button.text_content()) or "").replace("arrow_drop_down", "").strip()
            for label in ["Nano Banana", "Imagen"]:
                locator = menu.locator("button").filter(has_text=label).first
                if await locator.count() > 0:
                    return str((await locator.text_content()) or "").replace("arrow_drop_down", "").strip()
            return ""

        async def _compat_select_image_model(_self: Any, page: Any, model_display_name: str) -> bool:
            await _compat_open_settings_panel(_self, page)
            menu = await _compat_get_tabbed_menu(page)
            if menu is None:
                return False
            current = await _compat_get_image_model_selector(_self, page)
            wanted = str(model_display_name or "").strip()
            if wanted and wanted.lower() in current.lower():
                return True

            model_button = menu.locator('button[aria-haspopup="menu"]').first
            if await model_button.count() > 0:
                await model_button.click(force=True)
                await asyncio.sleep(0.5)

            if not wanted:
                return bool(await _compat_get_image_model_selector(_self, page))

            matched = await _compat_click_visible_menu_item(page, wanted)
            if matched:
                await asyncio.sleep(0.5)
                return True
            return False

        async def _compat_upload_via_file_input(page: Any, image_path: str) -> bool:
            selectors = [
                'input[type="file"][accept*="image"]',
                'input[type="file"]',
            ]
            for selector in selectors:
                locator = page.locator(selector)
                count = await locator.count()
                for index in range(count):
                    candidate = locator.nth(index)
                    try:
                        await candidate.set_input_files(image_path)
                        return True
                    except Exception:
                        continue
            return False

        async def _compat_visible_locator(locator: Any) -> Any | None:
            try:
                count = await locator.count()
            except Exception:
                return None
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    box = await candidate.bounding_box()
                except Exception:
                    box = None
                if not box or box["width"] < 16 or box["height"] < 16:
                    continue
                try:
                    disabled = await candidate.evaluate(
                        """
                        (el) => {
                          const node = el instanceof HTMLElement ? el : el.closest('*');
                          if (!node) return false;
                          const style = window.getComputedStyle(node);
                          return node.hasAttribute('disabled')
                            || node.getAttribute('aria-disabled') === 'true'
                            || style.pointerEvents === 'none';
                        }
                        """
                    )
                except Exception:
                    disabled = False
                if disabled:
                    continue
                return candidate
            return None

        async def _compat_start_trigger(page: Any) -> Any | None:
            locators = [
                page.locator('[aria-label*="Bắt đầu" i]'),
                page.locator('[aria-label*="Bat dau" i]'),
                page.locator('[aria-label*="Start image" i]'),
                page.locator('[aria-label*="Start frame" i]'),
                page.locator('[aria-label*="Add image" i]'),
                page.locator('[aria-label*="Add media" i]'),
                page.locator('[aria-label*="Start" i]'),
                page.locator('[aria-label*="frame" i]'),
                page.locator('button').filter(has_text=re.compile(r"^Bắt đầu$|^Bat dau$", re.I)),
                page.locator('button').filter(has_text=re.compile(r"^Start image$", re.I)),
                page.locator('button').filter(has_text=re.compile(r"^Start frame$", re.I)),
                page.locator('button').filter(has_text=re.compile(r"^Add image$", re.I)),
                page.locator('button').filter(has_text=re.compile(r"^Add Media$", re.I)),
                page.locator('button').filter(has_text=re.compile(r"^Start$", re.I)),
                page.locator('[role="button"]').filter(has_text=re.compile(r"^Bắt đầu$|^Bat dau$", re.I)),
                page.locator('[role="button"]').filter(has_text=re.compile(r"^Start$", re.I)),
                page.locator('[role="button"]').filter(has_text=re.compile(r"^Add image$", re.I)),
                page.locator('[role="button"]').filter(has_text=re.compile(r"^Add Media$", re.I)),
                page.locator('div[type="button"]').filter(has_text=re.compile(r"^Bắt đầu$|^Bat dau$", re.I)),
                page.locator('div[type="button"]').filter(has_text=re.compile(r"^Start$", re.I)),
                page.get_by_text("Bắt đầu", exact=True),
                page.get_by_text("Bat dau", exact=True),
                page.get_by_text("Start", exact=True),
            ]
            for locator in locators:
                candidate = await _compat_visible_locator(locator)
                if candidate is not None:
                    return candidate
            return None

        async def _compat_open_start_dialog(page: Any) -> Any | None:
            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                existing = page.locator('[role="dialog"]').last
                if await existing.count() > 0:
                    return existing

                trigger = await _compat_start_trigger(page)
                if trigger is not None:
                    try:
                        await trigger.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        await trigger.click(force=True)
                    except Exception:
                        await asyncio.sleep(0.4)
                    try:
                        await page.wait_for_selector('[role="dialog"]', timeout=1500)
                    except Exception:
                        await asyncio.sleep(0.4)
                        continue
                    return page.locator('[role="dialog"]').last
                await asyncio.sleep(0.5)
            return None

        async def _compat_first_start_image_option(dialog: Any) -> Any | None:
            selectors = [
                '[data-index]',
                '[data-item-index]',
                'button:has(img)',
                '[role="button"]:has(img)',
                'img[alt]',
            ]
            for selector in selectors:
                locator = dialog.locator(selector)
                count = await locator.count()
                for index in range(count):
                    candidate = locator.nth(index)
                    try:
                        box = await candidate.bounding_box()
                    except Exception:
                        box = None
                    if not box or box["width"] < 48 or box["height"] < 48:
                        continue
                    return candidate
            return None

        async def _compat_confirm_start_dialog(page: Any, dialog: Any) -> bool:
            labels = ["Use", "Select", "Done", "Add", "Choose", "Dùng", "Chọn", "Xong", "Thêm"]
            for label in labels:
                locator = dialog.locator("button").filter(has_text=label)
                count = await locator.count()
                for index in range(count):
                    button = locator.nth(index)
                    try:
                        box = await button.bounding_box()
                    except Exception:
                        box = None
                    if not box:
                        continue
                    try:
                        await button.click(force=True)
                    except Exception:
                        continue
                    await asyncio.sleep(0.35)
                    if await page.locator('[role="dialog"]').count() == 0:
                        return True
            try:
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.25)
            except Exception:
                pass
            return await page.locator('[role="dialog"]').count() == 0

        async def _compat_describe_start_dialog(dialog: Any) -> str:
            try:
                text = re.sub(r"\s+", " ", str(await dialog.text_content() or "")).strip()
            except Exception:
                text = ""
            try:
                button_count = await dialog.locator("button").count()
            except Exception:
                button_count = 0
            try:
                image_count = await dialog.locator("img").count()
            except Exception:
                image_count = 0
            summary = f"dialog buttons={button_count}, images={image_count}"
            if text:
                return f"{summary}, text='{text[:220]}'"
            return summary

        async def _compat_find_start_image_option(dialog: Any, image_name: str) -> Any | None:
            search = dialog.locator('input[type="text"]').first
            search_terms = self._start_image_search_terms(image_name)
            if not search_terms:
                search_terms = [str(image_name or "").strip()]

            for term in search_terms:
                if await search.count() > 0:
                    try:
                        await search.fill(term)
                        await asyncio.sleep(0.4)
                    except Exception:
                        pass

                candidates = [
                    dialog.locator('[data-index]').filter(has_text=term).last,
                    dialog.locator('[data-item-index]').filter(has_text=term).last,
                    dialog.locator('[role="button"]').filter(has_text=term).last,
                    dialog.locator("button").filter(has_text=term).last,
                    dialog.get_by_text(term, exact=True).last,
                ]
                for candidate in candidates:
                    try:
                        if await candidate.count() > 0:
                            return candidate
                    except Exception:
                        continue

                image_candidates = dialog.locator("img[alt]")
                image_count = await image_candidates.count()
                for index in range(image_count):
                    candidate = image_candidates.nth(index)
                    try:
                        alt_text = str(await candidate.get_attribute("alt") or "").strip()
                    except Exception:
                        alt_text = ""
                    haystack = " ".join(self._start_image_search_terms(alt_text))
                    if term.lower() and term.lower() in haystack.lower():
                        return candidate

            if await search.count() > 0:
                try:
                    await search.fill("")
                    await asyncio.sleep(0.2)
                except Exception:
                    pass

            return await _compat_first_start_image_option(dialog)

        async def _compat_close_dialog(page: Any) -> None:
            if await page.locator('[role="dialog"]').count() == 0:
                return
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
            except Exception:
                pass

        async def _compat_wait_for_uploaded_image(page: Any, image_name: str, *, timeout_s: float = 18.0) -> bool:
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                dialog = await _compat_open_start_dialog(page)
                if dialog is not None:
                    option = await _compat_find_start_image_option(dialog, image_name)
                    await _compat_close_dialog(page)
                    if option is not None:
                        return True
                await asyncio.sleep(1.0)
            return False

        async def _compat_wait_for_project_media_name(client_self: Any, known_media: set[str], *, timeout_s: float = 8.0) -> str:
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                try:
                    data = await client_self._api.get_project_data()
                except Exception:
                    data = {}
                for workflow in data.get("projectContents", {}).get("workflows", []) or []:
                    media_name = str((workflow.get("metadata") or {}).get("primaryMediaId") or "").strip()
                    if media_name and media_name not in known_media:
                        return media_name
                    for media in workflow.get("medias", []) or []:
                        media_name = str(media.get("name") or "").strip()
                        if media_name and media_name not in known_media:
                            return media_name
                await asyncio.sleep(0.8)
            return ""

        def _compat_parse_video_jobs_from_project_data(
            client_self: Any,
            project_data: Dict[str, Any],
            known_media: set[str],
        ) -> list[Any]:
            jobs: List[Any] = []
            seen_media: set[str] = set()
            workflows = project_data.get("projectContents", {}).get("workflows", []) or []
            for workflow in workflows:
                workflow_id = str(workflow.get("name") or "").strip()
                metadata = workflow.get("metadata", {}) or {}
                candidate_media: List[str] = []
                primary_media_id = str(metadata.get("primaryMediaId") or "").strip()
                if primary_media_id:
                    candidate_media.append(primary_media_id)
                for media in workflow.get("medias", []) or []:
                    media_name = str(media.get("name") or "").strip()
                    if media_name:
                        candidate_media.append(media_name)
                for media_name in candidate_media:
                    if not media_name or media_name in known_media or media_name in seen_media:
                        continue
                    seen_media.add(media_name)
                    job = VideoJob.__new__(VideoJob)
                    job.media_name = media_name
                    job.status = "PENDING"
                    job.project_id = client_self.project_id
                    job.workflow_id = workflow_id
                    jobs.append(job)
            return jobs

        async def _compat_wait_for_video_jobs_from_project(
            client_self: Any,
            known_media: set[str],
            *,
            target_count: int,
            timeout_s: float,
        ) -> list[Any]:
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                try:
                    data = await client_self._api.get_project_data()
                except Exception:
                    data = {}
                jobs = _compat_parse_video_jobs_from_project_data(client_self, data, known_media)
                if len(jobs) >= target_count:
                    return jobs[:target_count]
                await asyncio.sleep(1.0)
            return []

        async def _compat_upload_project_image(client_self: Any, page: Any, image_path: str) -> dict[str, str]:
            image_file = Path(str(image_path or "")).expanduser().resolve()
            file_name = image_file.name.strip()
            if not file_name:
                raise RuntimeError("Chưa nhận được đường dẫn ảnh đầu vào hợp lệ.")
            if not image_file.exists():
                raise RuntimeError("Không tìm thấy ảnh đầu vào trên máy để tải lên Flow.")

            known_media: set[str] = set()
            try:
                known_media = self._project_media_names(await client_self._api.get_project_data())
            except Exception:
                known_media = set()

            uploaded = await _compat_upload_via_file_input(page, str(image_file))
            if not uploaded:
                for trigger in (
                    page.locator("button").filter(has_text="Add Media").first,
                    page.get_by_text("Add Media", exact=True).first,
                    page.locator("button").filter(has_text="Upload image").first,
                    page.get_by_text("Upload image", exact=True).first,
                ):
                    try:
                        if await trigger.count() > 0:
                            await trigger.click(force=True)
                            await asyncio.sleep(0.5)
                            uploaded = await _compat_upload_via_file_input(page, str(image_file))
                            if uploaded:
                                break
                    except Exception:
                        continue

            if not uploaded:
                raise RuntimeError("Google Flow chưa tải được ảnh đầu vào lên project.")

            media_name = await _compat_wait_for_project_media_name(client_self, known_media)
            await asyncio.sleep(1.0)
            return {"file_name": file_name, "media_name": media_name}

        async def _compat_attach_start_frame(page: Any, image_name: str, media_name: str = "") -> tuple[bool, str]:
            dialog = await _compat_open_start_dialog(page)
            if dialog is None:
                return False, "Không mở được dialog Start."
            row = await _compat_find_start_image_option(dialog, image_name)
            if row is None and media_name:
                row = await _compat_find_start_image_option(dialog, media_name)
            if row is None:
                search = dialog.locator('input[type="text"]').first
                if await search.count() > 0:
                    await search.fill("")
                    await asyncio.sleep(0.3)
                    row = await _compat_find_start_image_option(dialog, image_name)
                    if row is None and media_name:
                        row = await _compat_find_start_image_option(dialog, media_name)
            if row is None:
                row = await _compat_first_start_image_option(dialog)
                if row is None:
                    await _compat_close_dialog(page)
                    return False, await _compat_describe_start_dialog(dialog)

            click_attempts = [
                (
                    "closest-clickable",
                    lambda: row.evaluate(
                        """(el) => {
                            const target = el.closest('button, [role="button"], [data-index], [data-item-index]') || el;
                            target.click();
                        }"""
                    ),
                ),
                ("row", lambda: row.click(force=True)),
                ("row-double", lambda: row.dblclick(force=True)),
                ("image", lambda: row.locator("img").first.click(force=True)),
                ("first-child", lambda: row.evaluate("(el) => (el.firstElementChild || el).click()")),
                (
                    "dispatch-events",
                    lambda: row.evaluate(
                        """(el) => {
                            const target = el.closest('button, [role="button"], [data-index], [data-item-index]') || el;
                            ['mousedown','mouseup','click','dblclick'].forEach((type) => {
                                target.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
                            });
                        }"""
                    ),
                ),
            ]
            for _, action in click_attempts:
                try:
                    await action()
                except Exception:
                    continue
                try:
                    await page.wait_for_function(
                        "() => !document.querySelector('[role=\"dialog\"]')",
                        timeout=5000,
                    )
                except Exception:
                    pass
                await asyncio.sleep(0.5)
                if await page.locator('[role="dialog"]').count() == 0:
                    return True, ""
                if await _compat_confirm_start_dialog(page, dialog):
                    return True, ""
                dialog = page.locator('[role="dialog"]').last
            try:
                detail = await _compat_describe_start_dialog(dialog)
                await _compat_close_dialog(page)
            except Exception:
                detail = ""
            return False, detail

        async def _compat_generate_video(
            client_self: Any,
            prompt: str,
            *,
            model: str = "Veo 3.1 - Fast",
            aspect: str = "landscape",
            count: int = 1,
            start_image: str | None = None,
            workflow_id: str | None = None,
            timeout_s: int = 120,
        ) -> list[Any]:
            page = await client_self._bm.page()
            await client_self._ensure_project_page(page)

            interceptor = UIInterceptor()
            interceptor.attach(page)
            target_count = max(1, min(4, int(count or 1)))

            mode = GenerationMode.FRAME_TO_VIDEO if start_image else GenerationMode.VIDEO
            ratio = AspectRatio.PORTRAIT if aspect == "portrait" else AspectRatio.LANDSCAPE

            await client_self._ui.open_settings_panel(page)
            switched = await client_self._ui.switch_mode(page, mode)
            if start_image and not switched:
                raise RuntimeError(
                    "Google Flow chưa chuyển được sang chế độ video từ ảnh (Frames), nên ảnh đầu vào chưa thể được gắn vào Start."
                )
            await client_self._ui.select_video_model(page, model)
            await client_self._ui.set_aspect_ratio(page, ratio)
            await client_self._ui.set_count(page, target_count)
            await client_self._ui.fill_prompt(page, prompt)
            uploaded_image_info: dict[str, str] = {"file_name": "", "media_name": ""}
            if start_image:
                uploaded_image_info = await _compat_upload_project_image(client_self, page, start_image)
            if uploaded_image_info.get("file_name") or uploaded_image_info.get("media_name"):
                attached, attach_detail = await _compat_attach_start_frame(
                    page,
                    uploaded_image_info.get("file_name", ""),
                    uploaded_image_info.get("media_name", ""),
                )
                if not attached:
                    # Flow thay đổi UI khá thất thường: có lúc upload xong là ảnh đã tự gắn vào Start
                    # mà không còn mở dialog theo đường cũ nữa. Đừng fail sớm ở đây; hãy thử submit
                    # thật và bắt đúng endpoint i2v để biết ảnh có được gắn hay không.
                    await asyncio.sleep(0.75)

            try:
                known_media_before_submit = self._project_media_names(await client_self._api.get_project_data())
            except Exception:
                known_media_before_submit = set()

            call_start = len(getattr(interceptor, "_calls", []))
            await client_self._ui.click_submit(page)
            jobs: list[Any] = []
            submit_error: Exception | None = None
            if start_image:
                submit_task = asyncio.create_task(
                    _compat_wait_for_video_submit_call(
                        interceptor,
                        call_start,
                        timeout_s=timeout_s,
                        expect_start_image=True,
                    )
                )
                project_task = asyncio.create_task(
                    _compat_wait_for_video_jobs_from_project(
                        client_self,
                        known_media_before_submit,
                        target_count=target_count,
                        timeout_s=min(timeout_s, 120),
                    )
                )
                done, pending = await asyncio.wait(
                    {submit_task, project_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                for task in done:
                    try:
                        result = task.result()
                    except Exception as exc:
                        submit_error = exc
                        continue
                    if isinstance(result, list):
                        jobs = result
                    else:
                        jobs = _compat_parse_video_jobs(client_self, result.resp)
                    break
                if not jobs and submit_error is not None:
                    raise submit_error
            else:
                entry = await _compat_wait_for_video_submit_call(
                    interceptor,
                    call_start,
                    timeout_s=timeout_s,
                    expect_start_image=False,
                )
                jobs = _compat_parse_video_jobs(client_self, entry.resp)
            if not jobs:
                raise RuntimeError("Google Flow chưa khởi tạo được clip video nào từ yêu cầu này.")
            if len(jobs) < target_count:
                raise RuntimeError(
                    f"Google Flow chỉ khởi tạo {len(jobs)}/{target_count} clip trong một lượt gửi. "
                    "Em dừng tại đây để tránh bấm thêm và tạo dư clip ngoài ý muốn. Hãy thử chạy lại."
                )
            return jobs[:target_count]

        async def _compat_ensure_project_page(client_self: Any, page: Any = None) -> None:
            if page is None:
                page = await client_self._bm.page()
            if client_self.project_id in str(page.url or ""):
                return
            try:
                await page.goto(
                    client_self._project_url,
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
            except Exception:
                await page.goto(
                    client_self._project_url,
                    wait_until="commit",
                    timeout=60_000,
                )
            await asyncio.sleep(2.5)

        async def _compat_generate_image(
            client_self: Any,
            prompt: str,
            *,
            model: str = "Nano Banana 2",
            aspect: str = "landscape",
            count: int = 1,
            reference_images: Optional[list[str]] = None,
            timeout_s: int = 120,
        ) -> list[Any]:
            page = await client_self._bm.page()
            await client_self._ensure_project_page(page)

            interceptor = UIInterceptor()
            interceptor.attach(page)
            target_count = max(1, min(4, int(count or 1)))

            ratio = (
                AspectRatio.PORTRAIT
                if "port" in str(aspect or "").lower()
                else AspectRatio.SQUARE
                if "square" in str(aspect or "").lower()
                else AspectRatio.LANDSCAPE
            )
            images: List[Any] = []
            attempts = 0
            max_attempts = max(target_count, 1) + 1
            while len(images) < target_count and attempts < max_attempts:
                remaining = target_count - len(images)
                batch_target = max(1, min(4, remaining))
                attempts += 1

                await client_self._ui.open_settings_panel(page)
                switched = await client_self._ui.switch_mode(page, GenerationMode.IMAGE)
                if not switched:
                    raise RuntimeError("Google Flow chưa chuyển sang chế độ tạo ảnh.")
                await client_self._ui.select_image_model(page, model)
                await client_self._ui.set_aspect_ratio(page, ratio)
                await client_self._ui.set_count(page, batch_target)
                await client_self._ui.fill_prompt(page, prompt)
                call_start = len(getattr(interceptor, "_calls", []))
                await client_self._ui.click_submit(page)
                entry = await _compat_wait_for_new_call(
                    interceptor,
                    call_start,
                    "batchGenerateImages",
                    timeout_s=max(30, timeout_s),
                    fail_on_tails=["batchAsyncGenerateVideo"],
                )
                batch_images = _compat_parse_images(entry.resp)
                if not batch_images:
                    raise RuntimeError("Google Flow không trả ảnh nào về từ yêu cầu hiện tại.")
                images.extend(batch_images)

            return images[:target_count]

        def _compat_parse_images(payload: Any) -> list[Any]:
            response = payload if isinstance(payload, dict) else {}
            images: List[Any] = []

            media_items = response.get("media", []) or []
            if media_items:
                for media_item in media_items:
                    if not isinstance(media_item, dict):
                        continue
                    image = GeneratedImage.__new__(GeneratedImage)
                    image._raw = media_item
                    image.media_name = str(media_item.get("name") or media_item.get("mediaName") or "").strip()
                    image.project_id = str(media_item.get("projectId") or "").strip()
                    image.workflow_id = str(media_item.get("workflowId") or "").strip()
                    generated = ((media_item.get("image") or {}).get("generatedImage") or {})
                    image.fife_url = str(
                        generated.get("fifeUrl")
                        or generated.get("url")
                        or media_item.get("fifeUrl")
                        or ""
                    ).strip()
                    image.seed = generated.get("seed", 0)
                    image.model = str(generated.get("modelNameType") or generated.get("model") or "").strip()
                    image.prompt = str(generated.get("prompt") or "").strip()
                    image.dimensions = media_item.get("dimensions", {}) or {}
                    image.file_path = None
                    images.append(image)
                if images:
                    return images

            generated_items = response.get("generatedImages", []) or []
            for item in generated_items:
                if not isinstance(item, dict):
                    continue
                image = GeneratedImage.__new__(GeneratedImage)
                image._raw = item
                image.media_name = str(item.get("mediaName") or item.get("name") or "").strip()
                image.project_id = ""
                image.workflow_id = ""
                image.fife_url = str(item.get("fifeUrl") or item.get("url") or "").strip()
                image.seed = int(item.get("seed", 0) or 0)
                image.model = str(item.get("modelNameType") or item.get("model") or "").strip()
                image.prompt = str(item.get("prompt") or "").strip()
                image.dimensions = item.get("dimensions", {}) or {}
                image.file_path = None
                images.append(image)
            return images

        def _compat_parse_video_jobs(client_self: Any, payload: Any) -> list[Any]:
            response = payload if isinstance(payload, dict) else {}
            jobs: List[Any] = []

            workflows_by_media: Dict[str, str] = {}
            for media_item in response.get("media", []) or []:
                media_name = str(media_item.get("name") or media_item.get("mediaName") or "").strip()
                workflow_id = str(media_item.get("workflowId") or "").strip()
                if media_name and workflow_id:
                    workflows_by_media[media_name] = workflow_id

            if not workflows_by_media:
                for job_data in response.get("jobs", []) or []:
                    media_id = job_data.get("mediaId", {}) if isinstance(job_data, dict) else {}
                    media_name = str(media_id.get("mediaName") or media_id.get("name") or "").strip()
                    workflow_id = str(job_data.get("workflowId") or "").strip()
                    if media_name and workflow_id:
                        workflows_by_media[media_name] = workflow_id

            if response.get("media"):
                for media_item in response.get("media", []) or []:
                    media_name = str(media_item.get("name") or media_item.get("mediaName") or "").strip()
                    if not media_name:
                        continue
                    job = VideoJob.__new__(VideoJob)
                    job.media_name = media_name
                    job.status = "PENDING"
                    job.project_id = client_self.project_id
                    job.workflow_id = workflows_by_media.get(media_name, "")
                    jobs.append(job)
                if jobs:
                    return jobs

            for job_data in response.get("jobs", []) or []:
                media_id = job_data.get("mediaId", {}) if isinstance(job_data, dict) else {}
                media_name = str(media_id.get("mediaName") or media_id.get("name") or "").strip()
                if not media_name:
                    continue
                job = VideoJob.__new__(VideoJob)
                job.media_name = media_name
                job.status = "PENDING"
                job.project_id = client_self.project_id
                job.workflow_id = workflows_by_media.get(media_name, str(job_data.get("workflowId") or "").strip())
                jobs.append(job)
            return jobs

        async def _compat_get_recaptcha_token(api_self: Any) -> str:
            page = await api_self._bm.page()

            is_on_flow = "labs.google" in str(page.url or "")
            if not is_on_flow:
                await api_self._ensure_project_page()
                page = await api_self._bm.page()
            elif getattr(api_self, "project_id", "") and getattr(api_self, "_project_page_url", "") not in str(page.url or ""):
                await api_self._ensure_project_page()
                page = await api_self._bm.page()

            async def _token_once() -> str:
                try:
                    ready = await page.wait_for_function(
                        "() => !!window.grecaptcha?.enterprise?.execute",
                        timeout=12_000,
                    )
                    await ready.dispose()
                except Exception:
                    return ""
                try:
                    token = await page.evaluate(
                        f"""
                        async () => {{
                            try {{
                                return await window.grecaptcha.enterprise.execute(
                                    '{RECAPTCHA_SITE_KEY}',
                                    {{ action: 'GENERATE' }}
                                );
                            }} catch (error) {{
                                return '';
                            }}
                        }}
                        """
                    )
                except Exception:
                    return ""
                return str(token or "").strip()

            for attempt in range(3):
                token = await _token_once()
                if token:
                    return token
                if attempt == 0:
                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=20_000)
                    except Exception:
                        pass
                await asyncio.sleep(1.5)
            return ""

        async def _compat_api_fetch(api_self: Any, method: str, url: str, body: Optional[dict] = None) -> dict:
            if not str(url).startswith("http"):
                url = f"{api_self.API_BASE if hasattr(api_self, 'API_BASE') else 'https://aisandbox-pa.googleapis.com/v1'}/{str(url).lstrip('/')}"

            hdrs = await api_self._get_auth_headers()
            api_key = str(getattr(api_self, "FLOW_API_KEY", "") or "").strip()
            if api_key:
                hdrs["x-goog-api-key"] = api_key
            data = json.dumps(body) if body is not None else None
            ctx = api_self._bm.context.request
            timeout_ms = int(max(30, int(getattr(api_self, "_timeout_s", 300) or 300)) * 1000)

            if method.upper() == "GET":
                resp = await ctx.get(url, headers=hdrs, timeout=timeout_ms)
            elif method.upper() == "PATCH":
                resp = await ctx.patch(url, headers=hdrs, data=data, timeout=timeout_ms)
            else:
                resp = await ctx.post(url, headers=hdrs, data=data, timeout=timeout_ms)

            if resp.status >= 400:
                text = await resp.text()
                endpoint = str(url).split("/")[-1].split(":")[-1]
                if resp.status == 404:
                    raise RuntimeError(
                        f"Endpoint not found (HTTP 404): {endpoint}\n"
                        f"This feature may be deprecated or unavailable via direct API.\n"
                        f"Response: {text[:200]}"
                    )
                if resp.status == 400:
                    try:
                        err_body = json.loads(text)
                        msg = err_body.get("error", {}).get("message", text[:200])
                    except Exception:
                        msg = text[:200]
                    raise RuntimeError(f"HTTP 400 INVALID_ARGUMENT on {endpoint}: {msg}")
                if resp.status in (401, 403):
                    try:
                        err_body = json.loads(text)
                        msg = err_body.get("error", {}).get("message", text[:200])
                    except Exception:
                        msg = text[:200]
                    raise RuntimeError(
                        f"HTTP {resp.status} on {endpoint}: {msg or 'authentication failed. Session cookies may be expired.'}"
                    )
                raise RuntimeError(f"HTTP {resp.status} on {endpoint}: {text[:200]}")

            try:
                return await resp.json()
            except Exception:
                return {}

        def _compat_interceptor_attach(self: Any, page: Any) -> None:
            if getattr(self, "_attached", False):
                return
            self._attached = True

            targets: List[Any] = [page]
            context = getattr(page, "context", None)
            if context is not None and hasattr(context, "on"):
                targets.append(context)

            for target in targets:
                try:
                    target.on("request", self._on_request)
                    target.on("response", self._on_response)
                except Exception:
                    continue

        FlowAPI._fetch = _compat_api_fetch
        FlowAPI.get_recaptcha_token = _compat_get_recaptcha_token
        UIInterceptor.attach = _compat_interceptor_attach
        FlowClient._ensure_project_page = _compat_ensure_project_page
        FlowUI._settings_visible = _compat_settings_visible
        FlowUI.fill_prompt = _compat_fill_prompt
        FlowUI.open_settings_panel = _compat_open_settings_panel
        FlowUI.switch_mode = _compat_switch_mode
        FlowUI.set_aspect_ratio = _compat_set_aspect_ratio
        FlowUI.set_count = _compat_set_count
        FlowUI.get_video_model_selector = _compat_get_video_model_selector
        FlowUI.select_video_model = _compat_select_video_model
        FlowUI.get_image_model_selector = _compat_get_image_model_selector
        FlowUI.select_image_model = _compat_select_image_model
        FlowClient.generate_video = _compat_generate_video
        FlowClient.generate_image = _compat_generate_image
        self.__class__._FLOW_RUNTIME_PATCHED = True

    def _project_url(self, project_id: str) -> str:
        return canonical_project_url(project_id)

    def _looks_like_placeholder_project_url(self, url: str) -> bool:
        candidate = str(url or "").strip().lower()
        if not candidate:
            return False
        return any(
            marker in candidate
            for marker in (
                "/project/[projectid]",
                "/project/%5bprojectid%5d",
                "/project/%5bproject_id%5d",
                "/project/[project_id]",
            )
        )

    async def _ensure_valid_flow_project_page(self, page: Any, project_url: str) -> None:
        target_url = str(project_url or "").strip()
        if not target_url:
            return

        current_url = str(getattr(page, "url", "") or "").strip()
        if current_url.startswith(target_url) and not self._looks_like_placeholder_project_url(current_url):
            return

        if self._looks_like_placeholder_project_url(current_url):
            logging.getLogger(__name__).warning(
                "Flow tab opened placeholder project route (%s); redirecting to %s",
                current_url,
                target_url,
            )

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60_000)
        except Exception:
            await page.goto(target_url, wait_until="commit", timeout=60_000)
        await asyncio.sleep(2.0)

    async def _repair_placeholder_flow_tabs(self, browser: Any, project_url: str) -> None:
        target_url = str(project_url or "").strip()
        if not target_url:
            return

        context = getattr(browser, "context", None)
        pages = list(getattr(context, "pages", []) or [])
        for candidate in pages:
            current_url = str(getattr(candidate, "url", "") or "").strip()
            if not self._looks_like_placeholder_project_url(current_url):
                continue
            try:
                logging.getLogger(__name__).warning(
                    "Repairing stale Flow placeholder tab (%s) -> %s",
                    current_url,
                    target_url,
                )
                await self._ensure_valid_flow_project_page(candidate, target_url)
            except Exception:
                continue

    async def _acquire_fresh_flow_page(self, browser: Any, project_url: str) -> Any:
        target_url = str(project_url or "").strip()
        context = getattr(browser, "context", None)
        pages = list(getattr(context, "pages", []) or [])

        for candidate in pages:
            current_url = str(getattr(candidate, "url", "") or "").strip()
            if current_url.startswith(target_url) and not self._looks_like_placeholder_project_url(current_url):
                try:
                    browser._page = candidate
                except Exception:
                    pass
                return candidate

        try:
            fresh_page = await context.new_page()
        except Exception:
            fresh_page = await browser.page()
        try:
            browser._page = fresh_page
        except Exception:
            pass
        return fresh_page

    async def _close_placeholder_flow_tabs(self, browser: Any, project_url: str) -> None:
        target_url = str(project_url or "").strip()
        context = getattr(browser, "context", None)
        pages = list(getattr(context, "pages", []) or [])
        stale_pages = [
            candidate
            for candidate in pages
            if self._looks_like_placeholder_project_url(str(getattr(candidate, "url", "") or ""))
        ]
        if not stale_pages:
            return

        logger = logging.getLogger(__name__)
        for candidate in stale_pages:
            current_url = str(getattr(candidate, "url", "") or "").strip()
            try:
                logger.warning("Closing stale Flow placeholder tab (%s)", current_url)
                await candidate.close()
            except Exception:
                continue

        remaining_pages = list(getattr(context, "pages", []) or [])
        if remaining_pages:
            try:
                browser._page = remaining_pages[0]
            except Exception:
                pass
            return

        try:
            fresh_page = await context.new_page()
        except Exception:
            return
        try:
            browser._page = fresh_page
        except Exception:
            pass
        if target_url:
            await self._ensure_valid_flow_project_page(fresh_page, target_url)

    def _normalize_project_id(self, project_value: str) -> str:
        return normalize_project_id(project_value)

    def _normalized_config(self, config: AppConfig) -> AppConfig:
        return normalized_app_config(config)

    def _normalize_projects_payload(self, projects: Dict[str, Dict[str, Any]]) -> tuple[Dict[str, Dict[str, str]], bool]:
        normalized: Dict[str, Dict[str, str]] = {}
        changed = False

        for raw_id, payload in projects.items():
            normalized_id = self._normalize_project_id(raw_id) or self._normalize_project_id(payload.get("url", ""))
            if not normalized_id:
                changed = True
                continue

            normalized_entry = {
                "name": str(payload.get("name", "")),
                "url": self._project_url(normalized_id),
            }
            current = normalized.get(normalized_id)
            if current is None or (not current["name"] and normalized_entry["name"]):
                normalized[normalized_id] = normalized_entry

            if raw_id != normalized_id or payload.get("url", "") != normalized_entry["url"]:
                changed = True

        return normalized, changed

    def _save_project_registry(self, projects: Dict[str, Dict[str, str]], active_id: str) -> None:
        from flow._storage import save_projects, set_active_project

        save_projects(projects)
        set_active_project(active_id or None, self._project_url(active_id) or None)

    def _fields_set(self, model: Any) -> set[str]:
        return set(getattr(model, "model_fields_set", getattr(model, "__fields_set__", set())))

    def _pick_skill_value(self, fields_set: set[str], field_name: str, explicit: Any, fallback: Any) -> Any:
        if field_name in fields_set:
            if isinstance(explicit, str):
                return explicit.strip()
            return explicit
        return fallback

    def _pick_skill_list(self, fields_set: set[str], field_name: str, explicit: List[str], fallback: List[str]) -> List[str]:
        return explicit if field_name in fields_set else fallback

    def _normalize_reference_media_names(self, values: List[str]) -> List[str]:
        return [str(entry).strip() for entry in values if str(entry).strip()]

    def _strip_accents(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", text)
        return "".join(char for char in normalized if unicodedata.category(char) != "Mn")

    def _normalize_skill_token(self, text: str) -> str:
        stripped = self._strip_accents(text or "").lower()
        stripped = re.sub(r"[^a-z0-9]+", "_", stripped)
        return stripped.strip("_")

    def _suggest_skill_name(self, skill_type: str, prompt: str) -> str:
        labels = {
            "video": "Tạo video",
            "image": "Tạo ảnh",
            "extend": "Kéo dài video",
            "upscale": "Nâng chất lượng",
            "camera_motion": "Chuyển động camera",
            "camera_position": "Vị trí camera",
            "insert": "Chèn vật thể",
            "remove": "Xóa vật thể",
        }
        snippet = (prompt or "").strip().replace("\n", " ")
        if snippet:
            return f"{labels.get(skill_type, skill_type)}: {snippet[:40]}"
        return labels.get(skill_type, "Skill mới")

    def _infer_skill_type(self, text: str) -> str:
        hinted = self._infer_skill_type_from_hint(text)
        if hinted:
            return hinted
        return "video"

    def _infer_skill_type_from_hint(self, text: str) -> str:
        normalized = self._normalize_skill_token(text)
        if any(token in normalized for token in {"tools_video", "guides_video", "video_guide", "video_ad"}):
            return "video"
        if any(token in normalized for token in {"tools_image", "guides_photo", "photo_graphy", "product_photography"}):
            return "image"
        rules = [
            ("camera_position", ["camera_position", "vi_tri_camera", "position_camera"]),
            ("camera_motion", ["camera_motion", "chuyen_dong_camera", "motion_camera"]),
            ("upscale", ["upscale", "nang_chat_luong"]),
            ("extend", ["extend", "keo_dai"]),
            ("insert", ["insert", "chen_vat_the", "them_vat_the"]),
            ("remove", ["remove", "xoa_vat_the"]),
            ("image", ["tao_anh", "image", "anh", "concept"]),
            ("video", ["tao_video", "video", "clip"]),
        ]
        for skill_type, keys in rules:
            if any(key in normalized for key in keys):
                return skill_type
        return ""

    def _parse_skill_type(self, value: str) -> str:
        normalized = self._normalize_skill_token(value)
        mapping = {
            "video": "video",
            "tao_video": "video",
            "image": "image",
            "anh": "image",
            "tao_anh": "image",
            "extend": "extend",
            "keo_dai": "extend",
            "upscale": "upscale",
            "nang_chat_luong": "upscale",
            "camera_motion": "camera_motion",
            "chuyen_dong_camera": "camera_motion",
            "camera_position": "camera_position",
            "vi_tri_camera": "camera_position",
            "insert": "insert",
            "chen_vat_the": "insert",
            "remove": "remove",
            "xoa_vat_the": "remove",
        }
        return mapping.get(normalized, self._infer_skill_type(value))

    def _parse_aspect(self, value: str) -> str:
        normalized = self._normalize_skill_token(value)
        if normalized in {"portrait", "9_16", "doc", "dung", "vertical"}:
            return "portrait"
        if normalized in {"square", "1_1", "vuong"}:
            return "square"
        return "landscape"

    def _parse_skill_text(self, text: str) -> Dict[str, Any]:
        parsed: Dict[str, Any] = {
            "type": self._infer_skill_type(text),
            "summary": "Học từ ô skill tự do.",
            "reference_media_names": [],
            "aspect": "landscape",
            "count": 1,
            "resolution": "1080p",
            "mask_x": 0.5,
            "mask_y": 0.5,
            "brush_size": 40,
        }
        free_lines: List[str] = []

        alias_map = {
            "ten": "name",
            "name": "name",
            "skill": "name",
            "tom_tat": "summary",
            "summary": "summary",
            "ghi_chu": "summary",
            "note": "summary",
            "loai": "type",
            "type": "type",
            "mode": "type",
            "prompt": "prompt",
            "mo_ta": "prompt",
            "description": "prompt",
            "aspect": "aspect",
            "ti_le": "aspect",
            "ratio": "aspect",
            "count": "count",
            "so_luong": "count",
            "quantity": "count",
            "workflow": "workflow_id",
            "workflow_id": "workflow_id",
            "ma_workflow": "workflow_id",
            "media": "media_id",
            "media_id": "media_id",
            "ma_media": "media_id",
            "motion": "motion",
            "huong_camera": "motion",
            "position": "position",
            "vi_tri_camera": "position",
            "resolution": "resolution",
            "do_phan_giai": "resolution",
            "references": "reference_media_names",
            "reference_media_names": "reference_media_names",
            "media_ref": "reference_media_names",
            "mask_x": "mask_x",
            "maskx": "mask_x",
            "mask_y": "mask_y",
            "masky": "mask_y",
            "brush": "brush_size",
            "brush_size": "brush_size",
            "co": "brush_size",
        }

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#!"):
                continue
            if line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            line = line.strip("-").strip()
            if not line:
                continue

            separator = ":" if ":" in line else "=" if "=" in line else ""
            if separator:
                key, value = [part.strip() for part in line.split(separator, 1)]
                value = value.strip().strip('"').strip("'")
                field_name = alias_map.get(self._normalize_skill_token(key), "")
                if not field_name:
                    free_lines.append(line)
                    continue

                if field_name == "type":
                    parsed["type"] = self._parse_skill_type(value)
                elif field_name == "aspect":
                    parsed["aspect"] = self._parse_aspect(value)
                elif field_name == "count":
                    numbers = re.findall(r"\d+", value)
                    if numbers:
                        parsed["count"] = int(numbers[0])
                elif field_name == "reference_media_names":
                    parsed["reference_media_names"] = [entry.strip() for entry in re.split(r"[,\n]", value) if entry.strip()]
                elif field_name in {"mask_x", "mask_y"}:
                    try:
                        parsed[field_name] = float(value)
                    except ValueError:
                        pass
                elif field_name == "brush_size":
                    numbers = re.findall(r"\d+", value)
                    if numbers:
                        parsed["brush_size"] = int(numbers[0])
                else:
                    parsed[field_name] = value
                continue

            free_lines.append(line)

        normalized_text = self._normalize_skill_token(text)
        plain_text = self._strip_accents(text).lower()
        count_match = re.search(r"\b(\d+)\s*(anh|video|ket qua|ket_qua|results?)\b", plain_text)
        if count_match and parsed.get("count", 1) == 1:
            parsed["count"] = int(count_match.group(1))

        if "9_16" in normalized_text or "doc" in normalized_text:
            parsed["aspect"] = "portrait"
        elif "1_1" in normalized_text or "vuong" in normalized_text:
            parsed["aspect"] = "square"
        elif "16_9" in normalized_text or "ngang" in normalized_text:
            parsed["aspect"] = "landscape"

        if "4k" in normalized_text:
            parsed["resolution"] = "4k"

        if not parsed.get("prompt"):
            parsed["prompt"] = "\n".join(free_lines).strip()

        if not parsed.get("name"):
            parsed["name"] = self._suggest_skill_name(parsed.get("type", "video"), parsed.get("prompt", ""))

        return parsed

    def _looks_like_instructional_skill_doc(self, text: str, source_hint: str = "") -> bool:
        source_name = Path(urlparse(source_hint).path or source_hint).name.lower()
        lowered = text.lower()
        has_frontmatter = lowered.startswith("---\n") and ("name:" in lowered[:300] or "description:" in lowered[:600])
        has_markdown_sections = "\n# " in text or text.startswith("# ")
        if source_name in {"skill.md", "readme.md"} and has_markdown_sections:
            return True
        return has_frontmatter and has_markdown_sections and "```" in text

    def _looks_like_skill_add_command(self, value: str) -> bool:
        lowered = value.strip().lower()
        return " skills add " in f" {lowered} " or lowered.startswith("skills add ") or lowered.startswith("npx ")

    def _parse_skill_add_command(self, command: str) -> Dict[str, Any]:
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Lệnh skills add không hợp lệ: {exc}") from exc

        if not tokens:
            raise HTTPException(status_code=400, detail="Lệnh skills add đang trống.")

        position = 0
        wrappers = {"npx", "bunx"}
        while position < len(tokens) and tokens[position] in wrappers:
            position += 1
            while position < len(tokens) and tokens[position].startswith("-"):
                position += 1

        if position + 1 < len(tokens) and tokens[position] == "pnpm" and tokens[position + 1] == "dlx":
            position += 2
        elif position + 1 < len(tokens) and tokens[position] == "yarn" and tokens[position + 1] == "dlx":
            position += 2

        if position >= len(tokens) or tokens[position] not in {"skills", "skill"}:
            raise HTTPException(status_code=400, detail="Bot hiện mới hiểu lệnh kiểu `skills add ...`.")

        position += 1
        if position >= len(tokens) or tokens[position] != "add":
            raise HTTPException(status_code=400, detail="Bot hiện mới hỗ trợ lệnh `skills add`.")

        position += 1
        source = ""
        name = ""
        summary = ""
        selected_skills: List[str] = []

        while position < len(tokens):
            token = tokens[position]

            if token in {"--skill", "-s"}:
                position += 1
                if position >= len(tokens):
                    raise HTTPException(status_code=400, detail="Thiếu tên skill sau `--skill`.")
                selected_skills.extend(self._split_skill_selector_values(tokens[position]))
                position += 1
                continue

            if token.startswith("--skill="):
                selected_skills.extend(self._split_skill_selector_values(token.split("=", 1)[1]))
                position += 1
                continue

            if token == "--skills":
                position += 1
                if position >= len(tokens):
                    raise HTTPException(status_code=400, detail="Thiếu danh sách skill sau `--skills`.")
                selected_skills.extend(self._split_skill_selector_values(tokens[position]))
                position += 1
                continue

            if token.startswith("--skills="):
                selected_skills.extend(self._split_skill_selector_values(token.split("=", 1)[1]))
                position += 1
                continue

            if token == "--name":
                position += 1
                if position < len(tokens):
                    name = tokens[position].strip()
                position += 1
                continue

            if token.startswith("--name="):
                name = token.split("=", 1)[1].strip()
                position += 1
                continue

            if token == "--summary":
                position += 1
                if position < len(tokens):
                    summary = tokens[position].strip()
                position += 1
                continue

            if token.startswith("--summary="):
                summary = token.split("=", 1)[1].strip()
                position += 1
                continue

            if token.startswith("-"):
                position += 1
                continue

            if not source:
                source = token
                position += 1
                continue

            selected_skills.extend(self._split_skill_selector_values(token))
            position += 1

        if not source:
            raise HTTPException(status_code=400, detail="Lệnh skills add đang thiếu repo hoặc link skill.")

        return {
            "url": source,
            "skills": self._normalize_selected_skills(selected_skills),
            "name": name,
            "summary": summary,
        }

    def _split_skill_selector_values(self, value: str) -> List[str]:
        return [part.strip() for part in re.split(r"[,\n]", value) if part.strip()]

    def _normalize_selected_skills(self, skills: List[str]) -> List[str]:
        normalized: List[str] = []
        seen: set[str] = set()
        for raw_skill in skills:
            for value in self._split_skill_selector_values(raw_skill):
                skill = value.strip().strip("/")
                if not skill:
                    continue
                lowered = skill.lower()
                if lowered.endswith("/skill.md"):
                    skill = skill[:-9].rstrip("/")
                elif lowered.endswith("/readme.md"):
                    skill = skill[:-10].rstrip("/")
                elif lowered.endswith(".md") and "/" not in skill:
                    skill = re.sub(r"\.md$", "", skill, flags=re.IGNORECASE)
                key = skill.lower()
                if key in seen:
                    continue
                seen.add(key)
                normalized.append(skill)
        return normalized

    def _normalize_skill_source_input(self, value: str) -> str:
        raw = value.strip()
        if not raw:
            return ""
        if raw.startswith("github.com/"):
            return f"https://{raw}"
        if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?", raw):
            return f"https://github.com/{raw[:-4] if raw.endswith('.git') else raw}"
        return raw

    def _parse_github_collection_url(self, value: str) -> Dict[str, str] | None:
        parsed = urlparse(value.strip())
        if parsed.netloc != "github.com":
            return None

        parts = [segment for segment in parsed.path.strip("/").split("/") if segment]
        if len(parts) < 2:
            return None
        if len(parts) >= 3 and parts[2] == "blob":
            return None

        owner = parts[0]
        repo = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
        branch = ""
        path = ""

        if len(parts) >= 4 and parts[2] == "tree":
            branch = parts[3]
            path = "/".join(parts[4:])
        elif len(parts) > 2:
            return None

        return {
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "path": path,
            "source_url": value.strip(),
        }

    def _normalize_skill_source_url(self, value: str) -> str:
        url = value.strip()
        if url.startswith("www."):
            url = f"https://{url}"

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise HTTPException(status_code=400, detail="Link skill phải bắt đầu bằng http:// hoặc https://")

        if parsed.netloc == "github.com":
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 5 and parts[2] == "blob":
                owner, repo = parts[0], parts[1]
                branch = parts[3]
                file_path = "/".join(parts[4:])
                return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"

        return url

    def _download_skill_text(self, url: str) -> Dict[str, str]:
        request = Request(url, headers={"User-Agent": "flow-web-ui/0.1"})
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                with urlopen(request, timeout=30) as response:
                    payload = response.read(200_000)
                    content_type = response.headers.get_content_type()
                    charset = response.headers.get_content_charset() or "utf-8"
                    final_url = response.geturl()
                break
            except HTTPError as exc:
                message = f"Không tải được file skill từ link này ({exc.code})."
                if exc.code == 404:
                    message = "Không tìm thấy file skill tại link này."
                raise HTTPException(status_code=400, detail=message) from exc
            except URLError as exc:
                last_error = exc
                if attempt == 1:
                    raise HTTPException(status_code=400, detail=f"Không tải được skill từ link này: {exc.reason}") from exc
                time.sleep(0.5)
        else:
            raise HTTPException(status_code=400, detail=f"Không tải được skill từ link này: {last_error}")

        if content_type not in {
            "text/plain",
            "text/markdown",
            "text/x-shellscript",
            "text/x-sh",
            "application/x-sh",
            "application/octet-stream",
            "text/html",
        }:
            raise HTTPException(status_code=400, detail="Link này không giống tệp văn bản/skill có thể đọc được.")

        text = payload.decode(charset, errors="replace").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Link skill không có nội dung để học.")

        return {
            "url": final_url,
            "text": text,
        }

    def _http_json(self, url: str) -> Any:
        request = Request(
            url,
            headers={
                "User-Agent": "flow-web-ui/0.1",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = response.read(500_000)
        except HTTPError as exc:
            message = f"GitHub trả về lỗi {exc.code}"
            if exc.code == 404:
                message = "Không tìm thấy repo/thư mục GitHub này."
            elif exc.code == 403:
                message = "GitHub tạm chặn hoặc giới hạn lượt truy cập. Hãy thử lại sau ít phút."
            raise HTTPException(status_code=400, detail=message) from exc
        except URLError as exc:
            raise HTTPException(status_code=400, detail=f"Không kết nối được tới GitHub: {exc.reason}") from exc

        try:
            return json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="GitHub trả về dữ liệu không hợp lệ.") from exc

    def _github_default_branch(self, owner: str, repo: str) -> str:
        payload = self._http_json(f"https://api.github.com/repos/{owner}/{repo}")
        branch = str(payload.get("default_branch", "")).strip()
        return branch or "main"

    def _github_contents_api_url(self, owner: str, repo: str, path: str, branch: str) -> str:
        encoded_path = quote(path.strip("/"), safe="/")
        base = f"https://api.github.com/repos/{owner}/{repo}/contents"
        if encoded_path:
            base = f"{base}/{encoded_path}"
        return f"{base}?ref={quote(branch, safe='')}"

    def _github_tree_api_url(self, owner: str, repo: str, branch: str) -> str:
        return f"https://api.github.com/repos/{owner}/{repo}/git/trees/{quote(branch, safe='')}?recursive=1"

    def _media_skill_repo_entries(self) -> List[Dict[str, Any]]:
        owner, repo = self.MEDIA_SKILL_REPO.split("/", 1)
        branch = self._github_default_branch(owner, repo)
        payload = self._http_json(self._github_tree_api_url(owner, repo, branch))
        tree = payload.get("tree", []) if isinstance(payload, dict) else []
        entries: List[Dict[str, Any]] = []

        for item in tree:
            if item.get("type") != "blob":
                continue
            path = str(item.get("path", "")).strip()
            if not self.MEDIA_SKILL_PATH_PATTERN.match(path):
                continue
            entries.append(
                {
                    "path": path,
                    "download_url": f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}",
                    "html_url": f"https://github.com/{owner}/{repo}/blob/{branch}/{path}",
                }
            )

        entries.sort(key=lambda item: item["path"].lower())
        return entries

    def _github_selected_skill_entries(
        self,
        owner: str,
        repo: str,
        branch: str,
        root_path: str,
        selected_skills: List[str],
    ) -> Dict[str, Any]:
        active_branch = branch or self._github_default_branch(owner, repo)
        payload = self._http_json(self._github_tree_api_url(owner, repo, active_branch))
        tree = payload.get("tree", []) if isinstance(payload, dict) else []
        root_prefix = root_path.strip("/").lower()
        candidate_paths: List[str] = []

        for item in tree:
            if item.get("type") != "blob":
                continue
            item_path = str(item.get("path", "")).strip()
            if not item_path:
                continue
            lowered = item_path.lower()
            if root_prefix and lowered != root_prefix and not lowered.startswith(f"{root_prefix}/"):
                continue
            file_name = Path(lowered).name
            if file_name not in {"skill.md", "readme.md"} and Path(lowered).suffix not in self.SKILL_TEXT_EXTENSIONS:
                continue
            candidate_paths.append(item_path)

        entries: List[Dict[str, Any]] = []
        missing: List[str] = []
        seen_paths: set[str] = set()
        for skill in selected_skills:
            matches = self._match_skill_paths(skill, candidate_paths)
            if not matches:
                missing.append(skill)
                continue
            for path in matches:
                if path in seen_paths:
                    continue
                seen_paths.add(path)
                entries.append(
                    {
                        "path": path,
                        "download_url": f"https://raw.githubusercontent.com/{owner}/{repo}/{active_branch}/{path}",
                        "html_url": f"https://github.com/{owner}/{repo}/blob/{active_branch}/{path}",
                        "size": 0,
                    }
                )

        return {
            "entries": entries,
            "missing": missing,
        }

    def _github_skill_file_entries(self, owner: str, repo: str, branch: str, root_path: str) -> List[Dict[str, Any]]:
        active_branch = branch or self._github_default_branch(owner, repo)
        queue = [root_path.strip("/")]
        files: List[Dict[str, Any]] = []
        visited: set[str] = set()
        scanned_dirs = 0

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            scanned_dirs += 1
            if scanned_dirs > 40:
                break

            payload = self._http_json(self._github_contents_api_url(owner, repo, current, active_branch))
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                item_type = item.get("type", "")
                item_path = str(item.get("path", "")).strip()
                if item_type == "dir":
                    queue.append(item_path)
                    continue
                if item_type != "file":
                    continue
                if self._is_skill_candidate_path(item_path):
                    files.append(
                        {
                            "path": item_path,
                            "download_url": item.get("download_url", ""),
                            "html_url": item.get("html_url", ""),
                            "size": int(item.get("size", 0) or 0),
                        }
                    )
                if len(files) >= 25:
                    return files
        return files

    def _match_skill_paths(self, skill: str, candidate_paths: List[str]) -> List[str]:
        normalized_skill = skill.strip().strip("/")
        if not normalized_skill:
            return []

        normalized_skill_lower = normalized_skill.lower()
        skill_base = Path(normalized_skill_lower).name
        direct_file_matches: List[str] = []
        folder_matches: List[str] = []
        fuzzy_matches: List[str] = []

        for path in candidate_paths:
            lowered = path.lower()
            parent = str(Path(lowered).parent)
            file_name = Path(lowered).name

            if lowered == normalized_skill_lower or lowered.endswith(f"/{normalized_skill_lower}"):
                direct_file_matches.append(path)
                continue

            if lowered.endswith(f"/{normalized_skill_lower}/skill.md") or lowered.endswith(f"/{normalized_skill_lower}/readme.md"):
                folder_matches.append(path)
                continue

            if skill_base and (
                parent.endswith(f"/{skill_base}")
                or parent == skill_base
                or lowered.endswith(f"/{skill_base}/skill.md")
                or lowered.endswith(f"/{skill_base}/readme.md")
            ):
                folder_matches.append(path)
                continue

            if normalized_skill_lower in lowered:
                fuzzy_matches.append(path)
                continue

            if file_name in {"skill.md", "readme.md"} and skill_base and skill_base in parent:
                fuzzy_matches.append(path)

        matches = direct_file_matches or folder_matches or fuzzy_matches
        return sorted(
            matches,
            key=lambda path: (
                0 if Path(path).name.lower() == "skill.md" else 1,
                path.count("/"),
                len(path),
            ),
        )[:5]

    def _is_skill_candidate_path(self, path: str) -> bool:
        lower = path.lower()
        name = Path(lower).name
        ext = Path(lower).suffix
        parent = str(Path(lower).parent)
        if ext not in self.SKILL_TEXT_EXTENSIONS:
            return False
        if name.startswith("."):
            return False
        if name == "readme.md" and "skill" not in parent:
            return False
        return True

    def _looks_like_skill_text(self, text: str, path: str = "") -> bool:
        normalized_path = path.lower()
        if "skill" in normalized_path:
            return True

        lowered = self._strip_accents(text).lower()
        signals = [
            "prompt",
            "workflow",
            "workflow_id",
            "type=",
            "type:",
            "aspect",
            "count",
            "tao anh",
            "tao video",
            "image",
            "video",
            "camera_motion",
            "camera_position",
            "upscale",
            "insert",
            "remove",
        ]
        score = sum(1 for signal in signals if signal in lowered)
        return score >= 2

    def _skill_signature(self, name: str, content: str) -> str:
        return f"{name.strip().lower()}::{content.strip()}"

    def _name_from_url(self, url: str) -> str:
        path = urlparse(url).path.rstrip("/")
        file_name = path.split("/")[-1] if path else ""
        if not file_name:
            return ""
        name = re.sub(r"\.[A-Za-z0-9]+$", "", file_name).replace("-", " ").replace("_", " ").strip()
        return name[:80]

    def _name_from_path(self, path: str) -> str:
        path_obj = Path(path)
        file_name = path_obj.name
        if not file_name:
            return ""
        if file_name.lower() in {"skill.md", "readme.md"} and path_obj.parent.name:
            file_name = path_obj.parent.name
        return re.sub(r"\.[A-Za-z0-9]+$", "", file_name).replace("-", " ").replace("_", " ").strip()[:80]

    def _flow_error_status(self, exc: Exception) -> int:
        if isinstance(exc, HTTPException):
            return exc.status_code
        if self._is_profile_lock_error(exc):
            return 409
        return 500

    def _flow_error_detail(self, exc: Exception) -> str:
        if isinstance(exc, HTTPException):
            detail = exc.detail
            if isinstance(detail, str):
                return humanize_flow_error(detail)
            return "Yêu cầu tới Google Flow không thành công."

        return humanize_flow_error(str(exc).strip()) or "Không thể kết nối tới Google Flow."

    def _is_profile_lock_error(self, exc: Exception) -> bool:
        message = str(exc)
        lowered = message.lower()
        return (
            "processsingleton" in message
            or "singletonlock" in lowered
            or "profile directory is already in use" in lowered
        )

    def _download_name(self, job: JobRecord, artifact: JobArtifact, artifact_index: int) -> str:
        extension = ".mp4" if artifact.mime_type.startswith("video") else ".jpg"
        slug = artifact.media_name or f"{job.type}-{job.id[:8]}-{artifact_index + 1}"
        return f"{slug}{extension}"

    def _resolve_job_request(self, request: CreateJobRequest, config: AppConfig) -> CreateJobRequest:
        payload = _model_dump(request)
        raw_timeout = int(payload.get("timeout_s") or 0)
        payload["type"] = str(payload.get("type", "")).strip()
        payload["prompt"] = str(payload.get("prompt", "")).strip()
        payload["title"] = str(payload.get("title", "")).strip()
        payload["model"] = self._normalize_job_model(payload["type"], str(payload.get("model", "")).strip())
        payload["aspect"] = str(payload.get("aspect", "landscape")).strip() or "landscape"
        payload["start_image_path"] = str(payload.get("start_image_path", "")).strip()
        payload["reference_image_paths"] = [
            str(item).strip()
            for item in payload.get("reference_image_paths", [])
            if str(item).strip()
        ]
        payload["reference_image_roles"] = self._normalize_reference_image_roles(
            payload["reference_image_paths"],
            payload.get("reference_image_roles", []),
        )
        payload["reference_media_names"] = [
            str(item).strip()
            for item in payload.get("reference_media_names", [])
            if str(item).strip()
        ]
        payload["media_id"] = str(payload.get("media_id", "")).strip()
        payload["workflow_id"] = str(payload.get("workflow_id", "")).strip() or config.active_workflow_id
        payload["motion"] = str(payload.get("motion", "")).strip()
        payload["position"] = str(payload.get("position", "")).strip()
        payload["resolution"] = str(payload.get("resolution", "1080p")).strip() or "1080p"
        payload["source_job_id"] = str(payload.get("source_job_id", "")).strip()
        payload["timeout_s"] = max(30, raw_timeout) if raw_timeout > 0 else max(30, int(config.generation_timeout_s))
        return CreateJobRequest(**payload)

    def _resolve_retry_source(self, source_job_id: str, request_type: str) -> JobRecord | None:
        source_id = str(source_job_id or "").strip()
        if not source_id:
            return None

        source_job = self.store.get_job(source_id)
        if source_job is None:
            raise HTTPException(status_code=400, detail="Không tìm thấy job gốc để chạy lại.")
        if source_job.status not in {"failed", "interrupted"}:
            raise HTTPException(status_code=400, detail="Chỉ có thể chạy lại job đang lỗi hoặc đã bị ngắt.")
        if source_job.type not in self.SUPPORTED_SKILL_TYPES:
            raise HTTPException(status_code=400, detail="Loại job này chưa hỗ trợ chạy lại.")
        if source_job.type != request_type:
            raise HTTPException(status_code=400, detail="Loại tác vụ chạy lại phải khớp với job gốc.")
        return source_job

    def _build_retry_snapshot(self, source_job: JobRecord | None) -> JobRetrySnapshot:
        if source_job is None:
            return JobRetrySnapshot()
        return JobRetrySnapshot(
            is_retry=True,
            source_job_id=source_job.id,
            source_job_title=source_job.title or source_job.type.replace("_", " ").title(),
            source_job_type=source_job.type,
            source_job_status=source_job.status,
            source_job_created_at=source_job.created_at,
        )

    def _default_title(self, request: CreateJobRequest) -> str:
        if request.type == "video":
            if request.start_image_path:
                return "Tạo video từ ảnh"
            return "Tạo video từ prompt"
        if request.type == "image":
            if request.reference_image_paths or request.reference_media_names:
                return "Chỉnh ảnh từ ảnh tham chiếu"
            return "Tạo ảnh từ prompt"
        titles = {
            "extend": "Kéo dài video",
            "upscale": "Nâng chất lượng video",
            "camera_motion": "Chuyển động camera",
            "camera_position": "Vị trí camera",
            "insert": "Chèn vật thể",
            "remove": "Xóa vật thể",
        }
        return titles.get(request.type, request.type.replace("_", " ").title())

    def _job_type_label(self, job_type: str) -> str:
        titles = {
            "login": "Đăng nhập",
            "video": "Tạo video",
            "image": "Tạo ảnh",
            "extend": "Kéo dài video",
            "upscale": "Nâng chất lượng",
            "camera_motion": "Chuyển động camera",
            "camera_position": "Vị trí camera",
            "insert": "Chèn vật thể",
            "remove": "Xóa vật thể",
        }
        return titles.get(str(job_type or "").strip(), str(job_type or "").strip())

    def _build_output_shelf(self, jobs: List[JobRecord]) -> OutputShelfSnapshot:
        items: List[OutputShelfItem] = []

        for job in jobs:
            if job.status != "completed" or not job.artifacts:
                continue

            job_input = job.input if isinstance(job.input, dict) else {}
            for artifact_index, artifact in enumerate(job.artifacts):
                workflow_id = str(artifact.workflow_id or "").strip() or str(job_input.get("workflow_id", "") or "").strip()
                local_path = str(artifact.local_path or "").strip()
                local_exists = self._artifact_local_exists(local_path)
                local_file_url = self._artifact_file_url(job.id, artifact_index) if local_path else ""
                items.append(
                    OutputShelfItem(
                        job_id=job.id,
                        artifact_index=artifact_index,
                        title=artifact.label or f"Kết quả {artifact_index + 1}",
                        job_title=job.title or self._job_type_label(job.type),
                        job_type=job.type,
                        job_type_label=self._job_type_label(job.type),
                        created_at=job.updated_at or job.created_at,
                        media_id=str(artifact.media_name or "").strip(),
                        workflow_id=workflow_id,
                        source_url=str(artifact.url or "").strip(),
                        local_path=local_path,
                        local_file_url=local_file_url,
                        local_exists=local_exists,
                        preview_url=self._artifact_preview_url(job, artifact, artifact_index),
                        mime_type=str(artifact.mime_type or "").strip(),
                        prompt=str(artifact.prompt or job_input.get("prompt", "") or "").strip(),
                        dimensions=artifact.dimensions or {},
                    )
                )
                if len(items) >= self.MAX_OUTPUT_SHELF_ITEMS:
                    break

            if len(items) >= self.MAX_OUTPUT_SHELF_ITEMS:
                break

        if not items:
            return OutputShelfSnapshot()

        job_count = len({item.job_id for item in items})
        return OutputShelfSnapshot(
            has_items=True,
            total_items=len(items),
            job_count=job_count,
            summary=self._output_shelf_summary(len(items), job_count),
            items=items,
        )

    def _replay_group_meta(self, group_key: str) -> Dict[str, str]:
        mapping = {
            "auth": {
                "label": "Cụm đăng nhập bị ngắt",
                "description": "Giữ log cuối để mở lại đăng nhập Google Flow mà không phải mò lại từ đầu.",
            },
            "video": {
                "label": "Cụm tạo video bị ngắt",
                "description": "Giữ prompt, tỉ lệ, ảnh đầu vào và timeout cuối để mở retry nhanh.",
            },
            "image": {
                "label": "Cụm tạo ảnh bị ngắt",
                "description": "Giữ prompt, tỉ lệ, media tham chiếu và timeout cuối để khôi phục nhanh.",
            },
            "edit": {
                "label": "Cụm chỉnh sửa media bị ngắt",
                "description": "Giữ media ID, workflow và tham số chỉnh sửa cuối để mở lại đúng form retry.",
            },
            "other": {
                "label": "Interrupted work khác",
                "description": "Giữ log cuối để quyết định bước recovery phù hợp mà không mất dấu công việc dở dang.",
            },
        }
        return mapping.get(group_key, mapping["edit"])

    def _download_root(self) -> Path:
        configured = self.store.snapshot().config.output_dir.strip()
        if configured:
            return Path(configured).expanduser()
        return DOWNLOADS_DIR

    def _artifact_file_url(self, job_id: str, artifact_index: int) -> str:
        return f"/api/jobs/{quote(str(job_id or '').strip(), safe='')}/artifacts/{int(artifact_index)}/file"

    def _get_artifact_or_raise(self, job_id: str, artifact_index: int) -> tuple[JobRecord, JobArtifact]:
        job = self.store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ.")
        if artifact_index < 0 or artifact_index >= len(job.artifacts):
            raise HTTPException(status_code=400, detail="Chỉ mục kết quả không hợp lệ.")
        return job, job.artifacts[artifact_index]

    def _artifact_local_exists(self, local_path: str) -> bool:
        raw = str(local_path or "").strip()
        if not raw:
            return False
        try:
            return Path(raw).expanduser().exists()
        except OSError:
            return False

    def _artifact_local_roots(self) -> List[Path]:
        roots = [DOWNLOADS_DIR.resolve(), UPLOADS_DIR.resolve()]
        configured = str(self.store.snapshot().config.output_dir or "").strip()
        if configured:
            try:
                roots.insert(0, Path(configured).expanduser().resolve())
            except OSError:
                pass

        unique_roots: List[Path] = []
        seen: set[str] = set()
        for root in roots:
            normalized = str(root)
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_roots.append(root)
        return unique_roots

    def _artifact_local_path(self, artifact: JobArtifact) -> Path:
        raw = str(artifact.local_path or "").strip()
        if not raw:
            raise HTTPException(status_code=400, detail="Artifact này chưa có tệp local đã lưu.")

        try:
            path = Path(raw).expanduser().resolve()
        except OSError as exc:
            raise HTTPException(status_code=404, detail="Không thể đọc tệp local của artifact này.") from exc

        allowed_roots = self._artifact_local_roots()
        if allowed_roots and not any(str(path).startswith(str(root)) for root in allowed_roots):
            raise HTTPException(status_code=403, detail="Tệp local này nằm ngoài vùng app đang phục vụ.")
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Tệp đã lưu cho artifact này không còn trên máy.")
        return path

    def _artifact_preview_url(self, job: JobRecord, artifact: JobArtifact, artifact_index: int) -> str:
        if str(artifact.local_path or "").strip():
            try:
                self._artifact_local_path(artifact)
            except HTTPException:
                pass
            else:
                return self._artifact_file_url(job.id, artifact_index)
        return str(artifact.public_url or artifact.url or "").strip()

    def _output_shelf_summary(self, item_count: int, job_count: int) -> str:
        return (
            f"{item_count} artifact mới nhất từ {job_count} job hoàn tất gần đây. "
            "Có thể mở, lưu hoặc tái dùng ngay tại đây mà không cần cuộn hết lịch sử tác vụ."
        )

    def _build_cleanup_assistant(
        self,
        config: Dict[str, Any] | AppConfig,
        jobs: List[JobRecord],
        output_shelf: OutputShelfSnapshot,
    ) -> tuple[CleanupAssistantSnapshot, Dict[str, Dict[str, Any]]]:
        normalized_config = self._normalized_config(config)
        upload_group, upload_plan = self._build_upload_cleanup_group(jobs)
        download_group, download_plan = self._build_download_cleanup_group(normalized_config, jobs, output_shelf)
        history_group, history_plan = self._build_history_cleanup_group(normalized_config, jobs, output_shelf)
        groups = [upload_group, download_group, history_group]

        total_safe_count = sum(group.safe_count for group in groups)
        total_safe_bytes = sum(group.safe_bytes for group in groups)
        protected_count = sum(group.protected_count for group in groups)
        protected_bytes = sum(group.protected_bytes for group in groups)
        visible = any(group.safe_count or group.protected_count for group in groups)

        if total_safe_count:
            headline = f"Có {total_safe_count} mục an toàn để dọn ngay"
            if protected_count:
                summary = (
                    f"Em đã tách riêng {total_safe_count} mục an toàn khỏi {protected_count} mục còn mới hoặc còn quan trọng. "
                    "Các nút dọn chỉ xóa trong phạm vi đã được phân loại sẵn."
                )
            else:
                summary = "Các mục hiện có đều nằm trong phạm vi an toàn đã được phân loại sẵn để dọn."
        elif protected_count:
            headline = "Chưa có mục an toàn để dọn"
            summary = (
                "Uploads, downloads và history hiện vẫn còn mới hoặc còn gắn với artifact local quan trọng, "
                "nên em đang giữ lại mặc định."
            )
        else:
            headline = ""
            summary = ""

        return (
            CleanupAssistantSnapshot(
                visible=visible,
                headline=headline,
                summary=summary,
                total_safe_count=total_safe_count,
                total_safe_bytes=total_safe_bytes,
                protected_count=protected_count,
                protected_bytes=protected_bytes,
                groups=groups,
            ),
            {
                "uploads": upload_plan,
                "downloads": download_plan,
                "history": history_plan,
            },
        )

    def _build_upload_cleanup_group(self, jobs: List[JobRecord]) -> tuple[CleanupGroupSnapshot, Dict[str, Any]]:
        root = UPLOADS_DIR.resolve()
        references: Dict[str, Dict[str, int]] = {}

        for job in jobs:
            job_input = job.input if isinstance(job.input, dict) else {}
            raw_paths = [str(job_input.get("start_image_path", "") or "").strip()]
            raw_paths.extend(
                str(item or "").strip()
                for item in job_input.get("reference_image_paths", [])
                if str(item or "").strip()
            )
            for raw_path in raw_paths:
                if not raw_path:
                    continue
                try:
                    path = Path(raw_path).expanduser().resolve()
                except OSError:
                    continue
                if not self._path_within_roots(path, [root]):
                    continue

                key = str(path)
                ref = references.setdefault(key, {"active": 0, "terminal": 0, "total": 0})
                ref["total"] += 1
                if job.status in {"queued", "running", "polling"}:
                    ref["active"] += 1
                else:
                    ref["terminal"] += 1

        safe_entries: List[Dict[str, Any]] = []
        protected_entries: List[Dict[str, Any]] = []
        safe_paths: List[Path] = []
        for path in self._list_cleanup_files([root]):
            modified_at = self._path_modified_datetime(path)
            size_bytes = self._file_size(path)
            ref = references.get(str(path), {"active": 0, "terminal": 0, "total": 0})
            active_count = int(ref.get("active", 0) or 0)
            terminal_count = int(ref.get("terminal", 0) or 0)
            is_recent = self._is_recent_datetime(modified_at, hours=self.CLEANUP_UPLOAD_GRACE_HOURS)

            if active_count:
                detail = f"Ảnh đầu vào này đang được {active_count} job chưa xong tham chiếu, nên em giữ lại."
                protected_entries.append({
                    "path": path,
                    "bytes": size_bytes,
                    "snapshot": self._cleanup_file_item(
                        path,
                        root,
                        detail=detail,
                        size_bytes=size_bytes,
                        status="protected",
                    ),
                })
                continue

            if is_recent:
                detail = (
                    f"Upload này mới xuất hiện trong khoảng {self.CLEANUP_UPLOAD_GRACE_HOURS} giờ gần đây. "
                    "App giữ lại để tránh xóa nhầm trước khi dùng."
                )
                if terminal_count:
                    detail += f" Nó đã từng được dùng cho {terminal_count} job đã xong."
                protected_entries.append({
                    "path": path,
                    "bytes": size_bytes,
                    "snapshot": self._cleanup_file_item(
                        path,
                        root,
                        detail=detail,
                        size_bytes=size_bytes,
                        status="protected",
                    ),
                })
                continue

            detail = "File tạm đã cũ và không còn job đang chạy nào giữ lại."
            if terminal_count:
                detail += f" Nó từng được dùng cho {terminal_count} job đã xong."
            safe_paths.append(path)
            safe_entries.append({
                "path": path,
                "bytes": size_bytes,
                "snapshot": self._cleanup_file_item(
                    path,
                    root,
                    detail=detail,
                    size_bytes=size_bytes,
                    status="safe",
                ),
            })

        safe_entries.sort(key=lambda item: item["snapshot"].path_hint)
        protected_entries.sort(key=lambda item: item["snapshot"].path_hint)
        safe_count = len(safe_entries)
        safe_bytes = sum(item["bytes"] for item in safe_entries)
        protected_count = len(protected_entries)
        protected_bytes = sum(item["bytes"] for item in protected_entries)

        if safe_count:
            summary = "Uploads tạm đã cũ có thể dọn ngay mà không ảnh hưởng các job đang chạy."
        elif protected_count:
            summary = "Uploads hiện còn mới hoặc còn bị job đang chạy giữ lại, nên em chưa xếp chúng vào nhóm an toàn."
        else:
            summary = "Chưa có upload tạm nào để phân loại."

        group = CleanupGroupSnapshot(
            key="uploads",
            label="Uploads tạm",
            action_label="Dọn uploads tạm",
            summary=summary,
            empty_label="Chưa có upload tạm nào cần dọn.",
            safe_count=safe_count,
            safe_bytes=safe_bytes,
            protected_count=protected_count,
            protected_bytes=protected_bytes,
            notes=[
                "Chỉ quét trong thư mục uploads của app.",
                "Upload mới hoặc đang bị job chưa xong tham chiếu sẽ được giữ lại mặc định.",
            ],
            safe_items=[entry["snapshot"] for entry in safe_entries[: self.CLEANUP_PREVIEW_LIMIT]],
            protected_items=[entry["snapshot"] for entry in protected_entries[: self.CLEANUP_PREVIEW_LIMIT]],
        )
        return group, {"paths": safe_paths, "artifact_refs": {}, "job_ids": []}

    def _build_download_cleanup_group(
        self,
        config: AppConfig,
        jobs: List[JobRecord],
        output_shelf: OutputShelfSnapshot,
    ) -> tuple[CleanupGroupSnapshot, Dict[str, Any]]:
        roots = self._download_cleanup_roots()
        reference_map = self._download_artifact_reference_map(jobs, roots)
        shelf_keys = {
            f"{item.job_id}:{int(item.artifact_index)}"
            for item in (output_shelf.items if output_shelf and output_shelf.items else [])
        }
        active_workflow_id = str(config.active_workflow_id or "").strip()

        safe_entries: List[Dict[str, Any]] = []
        protected_entries: List[Dict[str, Any]] = []
        safe_paths: List[Path] = []
        artifact_refs: Dict[str, List[tuple[str, int]]] = {}
        for path in self._list_cleanup_files(roots):
            size_bytes = self._file_size(path)
            refs = reference_map.get(str(path), [])
            protection_reasons = self._download_protection_reasons(refs, shelf_keys, active_workflow_id)

            if protection_reasons:
                protected_entries.append({
                    "path": path,
                    "bytes": size_bytes,
                    "snapshot": self._cleanup_file_item(
                        path,
                        self._matching_cleanup_root(path, roots),
                        detail=" ".join(protection_reasons[:2]),
                        size_bytes=size_bytes,
                        status="protected",
                    ),
                })
                continue

            if refs:
                detail = (
                    f"Artifact local này đã cũ hơn {self.CLEANUP_DOWNLOAD_RETENTION_DAYS} ngày "
                    "và không còn nằm trong nhóm output quan trọng gần đây."
                )
                artifact_refs[str(path)] = [(entry["job"].id, entry["artifact_index"]) for entry in refs]
            else:
                detail = "Tệp đã tải này không còn job history nào tham chiếu, nên có thể dọn an toàn."
                artifact_refs[str(path)] = []

            safe_paths.append(path)
            safe_entries.append({
                "path": path,
                "bytes": size_bytes,
                "snapshot": self._cleanup_file_item(
                    path,
                    self._matching_cleanup_root(path, roots),
                    detail=detail,
                    size_bytes=size_bytes,
                    status="safe",
                ),
            })

        safe_entries.sort(key=lambda item: item["snapshot"].path_hint)
        protected_entries.sort(key=lambda item: item["snapshot"].path_hint)
        safe_count = len(safe_entries)
        safe_bytes = sum(item["bytes"] for item in safe_entries)
        protected_count = len(protected_entries)
        protected_bytes = sum(item["bytes"] for item in protected_entries)

        if safe_count:
            summary = (
                "Các file đã tải cũ hoặc không còn tham chiếu sẽ được xóa, "
                "đồng thời metadata local liên quan trong history cũng được làm sạch."
            )
        elif protected_count:
            summary = "Các file đã tải hiện còn mới, còn nằm trên output shelf hoặc còn gắn với workflow quan trọng nên em giữ lại."
        else:
            summary = "Chưa có file đã tải nào để phân loại."

        group = CleanupGroupSnapshot(
            key="downloads",
            label="Downloads đã lưu",
            action_label="Dọn file đã tải",
            summary=summary,
            empty_label="Chưa có file đã tải nào cần dọn.",
            safe_count=safe_count,
            safe_bytes=safe_bytes,
            protected_count=protected_count,
            protected_bytes=protected_bytes,
            notes=[
                "Chỉ xóa file nằm trong thư mục tải xuống an toàn của app.",
                "Artifact local còn mới, còn trên output shelf hoặc còn trùng workflow mặc định sẽ được giữ lại mặc định.",
            ],
            safe_items=[entry["snapshot"] for entry in safe_entries[: self.CLEANUP_PREVIEW_LIMIT]],
            protected_items=[entry["snapshot"] for entry in protected_entries[: self.CLEANUP_PREVIEW_LIMIT]],
        )
        return group, {"paths": safe_paths, "artifact_refs": artifact_refs, "job_ids": []}

    def _build_history_cleanup_group(
        self,
        config: AppConfig,
        jobs: List[JobRecord],
        output_shelf: OutputShelfSnapshot,
    ) -> tuple[CleanupGroupSnapshot, Dict[str, Any]]:
        safe_entries: List[CleanupItemSnapshot] = []
        protected_entries: List[CleanupItemSnapshot] = []
        removable_job_ids: List[str] = []
        shelf_job_ids = {item.job_id for item in (output_shelf.items if output_shelf and output_shelf.items else [])}
        active_workflow_id = str(config.active_workflow_id or "").strip()

        for job in jobs:
            job_activity = self._job_activity_datetime(job)
            is_recent = self._is_recent_datetime(job_activity, days=self.CLEANUP_HISTORY_RETENTION_DAYS)
            has_local_files = self._job_has_existing_local_artifacts(job)
            touches_active_workflow = self._job_touches_workflow(job, active_workflow_id)

            protected_reason = ""
            if job.status in {"queued", "running", "polling"}:
                protected_reason = "Job này vẫn chưa hoàn tất nên history cần được giữ nguyên."
            elif has_local_files:
                protected_reason = "Job này vẫn còn file local trên máy, nên app giữ history để lần lại artifact."
            elif job.id in shelf_job_ids:
                protected_reason = "Job này vẫn đang góp mặt trong output shelf gần đây."
            elif is_recent:
                protected_reason = f"Job này còn mới trong khoảng {self.CLEANUP_HISTORY_RETENTION_DAYS} ngày gần đây."
            elif touches_active_workflow:
                protected_reason = "Job này còn khớp workflow mặc định đang ghim, nên em giữ lại mặc định."

            if protected_reason:
                protected_entries.append(self._cleanup_job_item(job, protected_reason, status="protected"))
                continue

            if job.type == "login":
                detail = "Lịch sử đăng nhập cũ có thể gỡ đi mà không ảnh hưởng phiên hiện tại."
            elif job.status in {"failed", "interrupted"}:
                detail = "Job lỗi cũ này có thể gỡ khỏi history để bảng tác vụ gọn hơn."
            else:
                detail = "Metadata job hoàn tất đã cũ và không còn giữ file local trên máy."

            removable_job_ids.append(job.id)
            safe_entries.append(self._cleanup_job_item(job, detail, status="safe"))

        safe_count = len(safe_entries)
        protected_count = len(protected_entries)
        if safe_count:
            summary = "Các job cũ này chỉ còn là metadata, nên có thể gỡ khỏi history mà không đụng tới file local còn tồn tại."
        elif protected_count:
            summary = "History hiện chỉ còn các job mới hơn hoặc vẫn còn gắn với artifact local cần giữ."
        else:
            summary = "History hiện chưa có mục cũ nào cần dọn."

        group = CleanupGroupSnapshot(
            key="history",
            label="History cũ",
            action_label="Dọn history cũ",
            summary=summary,
            empty_label="Chưa có metadata history nào cần dọn.",
            safe_count=safe_count,
            safe_bytes=0,
            protected_count=protected_count,
            protected_bytes=0,
            notes=[
                "Chỉ gỡ metadata job cũ khỏi state của app.",
                "Job còn mới hoặc còn gắn với file local trên máy sẽ được giữ lại mặc định.",
            ],
            safe_items=safe_entries[: self.CLEANUP_PREVIEW_LIMIT],
            protected_items=protected_entries[: self.CLEANUP_PREVIEW_LIMIT],
        )
        return group, {"paths": [], "artifact_refs": {}, "job_ids": removable_job_ids}

    def _download_cleanup_roots(self) -> List[Path]:
        roots = [DOWNLOADS_DIR.resolve()]
        configured = str(self.store.snapshot().config.output_dir or "").strip()
        if configured:
            try:
                roots.insert(0, Path(configured).expanduser().resolve())
            except OSError:
                pass

        unique_roots: List[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = str(root)
            if key in seen:
                continue
            seen.add(key)
            unique_roots.append(root)
        return unique_roots

    def _download_artifact_reference_map(
        self,
        jobs: List[JobRecord],
        roots: List[Path],
    ) -> Dict[str, List[Dict[str, Any]]]:
        references: Dict[str, List[Dict[str, Any]]] = {}
        for job in jobs:
            job_input = job.input if isinstance(job.input, dict) else {}
            for artifact_index, artifact in enumerate(job.artifacts):
                raw_path = str(artifact.local_path or "").strip()
                if not raw_path:
                    continue
                try:
                    path = Path(raw_path).expanduser().resolve()
                except OSError:
                    continue
                if not self._path_within_roots(path, roots):
                    continue
                references.setdefault(str(path), []).append({
                    "job": job,
                    "job_input": job_input,
                    "artifact": artifact,
                    "artifact_index": artifact_index,
                })
        return references

    def _download_protection_reasons(
        self,
        refs: List[Dict[str, Any]],
        shelf_keys: set[str],
        active_workflow_id: str,
    ) -> List[str]:
        reasons: List[str] = []
        for entry in refs:
            job = entry["job"]
            artifact = entry["artifact"]
            artifact_index = int(entry["artifact_index"])
            workflow_id = str(artifact.workflow_id or entry["job_input"].get("workflow_id", "") or "").strip()
            activity_at = self._job_activity_datetime(job)

            if job.status in {"queued", "running", "polling"}:
                reasons.append("Tệp này vẫn gắn với job chưa hoàn tất.")
            if self._is_recent_datetime(activity_at, days=self.CLEANUP_DOWNLOAD_RETENTION_DAYS):
                reasons.append(f"Job này còn mới trong khoảng {self.CLEANUP_DOWNLOAD_RETENTION_DAYS} ngày gần đây.")
            if f"{job.id}:{artifact_index}" in shelf_keys:
                reasons.append("Artifact này vẫn đang nằm trên output shelf gần đây.")
            if active_workflow_id and workflow_id and workflow_id == active_workflow_id:
                reasons.append("Artifact này còn thuộc workflow mặc định đang ghim.")

        deduped: List[str] = []
        seen: set[str] = set()
        for reason in reasons:
            if reason in seen:
                continue
            seen.add(reason)
            deduped.append(reason)
        return deduped

    def _cleanup_file_item(
        self,
        path: Path,
        root: Path,
        *,
        detail: str,
        size_bytes: int,
        status: str,
    ) -> CleanupItemSnapshot:
        status_label = "An toàn để xóa" if status == "safe" else "Đang giữ lại"
        relative_path = path.name
        try:
            relative_path = str(path.relative_to(root))
        except ValueError:
            relative_path = path.name
        return CleanupItemSnapshot(
            key=str(path),
            label=path.name,
            detail=detail,
            path_hint=f"{root.name}/{relative_path}".replace("\\", "/"),
            bytes=size_bytes,
            status=status,
            status_label=status_label,
        )

    def _cleanup_job_item(self, job: JobRecord, detail: str, *, status: str) -> CleanupItemSnapshot:
        status_label = "An toàn để xóa" if status == "safe" else "Đang giữ lại"
        return CleanupItemSnapshot(
            key=job.id,
            label=job.title or self._job_type_label(job.type),
            detail=f"{self._job_type_label(job.type)} · {detail}",
            path_hint=f"job {job.id[:8]}",
            bytes=0,
            status=status,
            status_label=status_label,
        )

    def _job_has_existing_local_artifacts(self, job: JobRecord) -> bool:
        for artifact in job.artifacts:
            if str(artifact.local_path or "").strip() and self._artifact_local_exists(str(artifact.local_path or "").strip()):
                return True
        return False

    def _job_touches_workflow(self, job: JobRecord, workflow_id: str) -> bool:
        safe_workflow_id = str(workflow_id or "").strip()
        if not safe_workflow_id:
            return False
        job_input = job.input if isinstance(job.input, dict) else {}
        if str(job_input.get("workflow_id", "") or "").strip() == safe_workflow_id:
            return True
        return any(str(artifact.workflow_id or "").strip() == safe_workflow_id for artifact in job.artifacts)

    def _list_cleanup_files(self, roots: List[Path]) -> List[Path]:
        files: List[Path] = []
        seen: set[str] = set()
        for root in roots:
            if not root.exists() or not root.is_dir():
                continue
            for candidate in root.rglob("*"):
                if not candidate.is_file() or candidate.name == ".gitkeep":
                    continue
                try:
                    resolved = candidate.resolve()
                except OSError:
                    continue
                key = str(resolved)
                if key in seen or not self._path_within_roots(resolved, [root]):
                    continue
                seen.add(key)
                files.append(resolved)
        return files

    def _matching_cleanup_root(self, path: Path, roots: List[Path]) -> Path:
        for root in roots:
            if self._path_within_roots(path, [root]):
                return root
        return roots[0]

    def _path_within_roots(self, path: Path, roots: List[Path]) -> bool:
        for root in roots:
            try:
                path.relative_to(root)
            except ValueError:
                continue
            return True
        return False

    def _path_modified_datetime(self, path: Path) -> datetime | None:
        try:
            stat = path.stat()
        except OSError:
            return None
        return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    def _is_recent_datetime(self, value: datetime | None, *, days: int = 0, hours: int = 0) -> bool:
        if value is None:
            return False
        threshold = datetime.now(timezone.utc) - timedelta(days=max(0, days), hours=max(0, hours))
        return value >= threshold

    def _file_size(self, path: Path) -> int:
        try:
            return int(path.stat().st_size)
        except OSError:
            return 0

    def _delete_cleanup_file(self, path: Path, roots: List[Path]) -> str:
        try:
            resolved = Path(path).expanduser().resolve()
        except OSError as exc:
            raise HTTPException(status_code=400, detail=f"Không thể xác định tệp cần dọn: {path}") from exc

        if not self._path_within_roots(resolved, roots):
            raise HTTPException(status_code=403, detail="Tệp cần dọn nằm ngoài phạm vi an toàn của app.")
        if resolved.exists() and not resolved.is_file():
            raise HTTPException(status_code=400, detail="Cleanup chỉ hỗ trợ xóa tệp, không xóa thư mục.")
        if resolved.exists():
            resolved.unlink()
        return str(resolved)

    def _public_download_url(self, local_path: str) -> str:
        path = Path(local_path).resolve()
        default_root = DOWNLOADS_DIR.resolve()
        if str(path).startswith(str(default_root)):
            return f"/files/downloads/{path.name}"
        return ""

    def _validate_job_request(self, request: CreateJobRequest) -> None:
        if request.type != "login" and not self.get_auth_status().authenticated:
            raise HTTPException(
                status_code=400,
                detail="Cần đăng nhập Google Flow trước khi chạy tác vụ. Hãy bấm Đăng nhập Google Flow rồi thử lại.",
            )

        if request.type == "video" and not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Hãy nhập mô tả video trước khi chạy.")

        if request.type == "image" and not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Hãy nhập mô tả ảnh trước khi chạy.")

        if request.type == "image" and len(request.reference_image_paths) > 4:
            raise HTTPException(status_code=400, detail="Tối đa 4 ảnh tham chiếu cho một lượt chỉnh ảnh.")

        if request.type in {"video", "image"} and not 1 <= int(request.count) <= 4:
            raise HTTPException(status_code=400, detail="Số lượng cho tác vụ tạo nội dung phải nằm trong khoảng 1 đến 4.")

        if request.type == "image" and self._normalize_image_model(request.model) not in self.IMAGE_MODEL_LABELS:
            raise HTTPException(status_code=400, detail="Model ảnh này hiện chưa được hỗ trợ trong app.")

        if request.type in {"extend", "upscale", "camera_motion", "camera_position", "insert", "remove"}:
            if not request.media_id.strip():
                raise HTTPException(status_code=400, detail="Vui lòng nhập Media ID cho tác vụ chỉnh sửa.")

        if request.type == "camera_motion" and not request.motion.strip():
            raise HTTPException(status_code=400, detail="Vui lòng chọn chuyển động camera.")

        if request.type == "camera_position" and not request.position.strip():
            raise HTTPException(status_code=400, detail="Vui lòng chọn vị trí camera.")

        if request.type == "insert" and not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Vui lòng nhập prompt để chèn vật thể.")

    def _image_api_aspect_ratio(self, aspect: str) -> str:
        normalized = self._parse_aspect(aspect or "landscape")
        if normalized == "portrait":
            return "IMAGE_ASPECT_RATIO_PORTRAIT"
        if normalized == "square":
            return "IMAGE_ASPECT_RATIO_SQUARE"
        return "IMAGE_ASPECT_RATIO_LANDSCAPE"

    def _normalize_video_model(self, model: str) -> str:
        raw = str(model or "").strip()
        if not raw:
            return self.DEFAULT_VIDEO_MODEL
        compact = re.sub(r"\s+", " ", raw).strip().lower()
        return self.VIDEO_MODEL_DISPLAY_ALIASES.get(compact, raw)

    def _normalize_image_model(self, model: str) -> str:
        raw = str(model or "").strip()
        if not raw:
            return self.DEFAULT_IMAGE_MODEL
        compact = re.sub(r"\s+", " ", raw).strip().lower()
        normalized = self.IMAGE_MODEL_ALIASES.get(compact, raw.upper())
        if normalized not in self.IMAGE_MODEL_LABELS:
            return self.DEFAULT_IMAGE_MODEL
        return normalized

    def _normalize_job_model(self, request_type: str, model: str) -> str:
        kind = str(request_type or "").strip()
        if kind == "video":
            return self._normalize_video_model(model)
        if kind == "image":
            return self._normalize_image_model(model)
        return str(model or "").strip()

    def _image_api_model_name(self, model: str) -> str:
        return self._normalize_image_model(model)

    def _image_edit_model_name(self, model: str) -> str:
        normalized = self._normalize_image_model(model)
        return self.IMAGE_MODEL_EDIT_VALUES.get(normalized, self.IMAGE_MODEL_EDIT_VALUES[self.DEFAULT_IMAGE_MODEL])

    def _image_ui_model_label(self, model: str) -> str:
        normalized = self._normalize_image_model(model)
        return self.IMAGE_MODEL_LABELS.get(normalized, self.IMAGE_MODEL_LABELS[self.DEFAULT_IMAGE_MODEL])

    def _normalize_reference_image_role(self, role: str) -> str:
        normalized = re.sub(r"[^a-z]+", "", str(role or "").strip().lower())
        if normalized in {"base", "main", "model", "subject", "primary"}:
            return "base"
        if normalized in {"logo", "brand"}:
            return "logo"
        if normalized in {"product", "item"}:
            return "product"
        return "reference"

    def _start_image_search_terms(self, value: str) -> List[str]:
        raw = str(value or "").strip()
        if not raw:
            return []

        candidates = [raw]
        try:
            path = PureWindowsPath(raw) if ("\\" in raw or re.match(r"^[A-Za-z]:", raw)) else Path(raw)
        except Exception:
            path = None

        if path is not None:
            name = path.name.strip()
            stem = path.stem.strip()
            if name:
                candidates.append(name)
            if stem:
                candidates.append(stem)

        normalized_variants: List[str] = []
        for item in candidates:
            compact = re.sub(r"\s+", " ", str(item or "").strip())
            if compact:
                normalized_variants.append(compact)
            simple = re.sub(r"[^a-z0-9]+", " ", str(item or "").strip().lower())
            simple = re.sub(r"\s+", " ", simple).strip()
            if simple:
                normalized_variants.append(simple)

        ordered: List[str] = []
        seen: set[str] = set()
        for item in normalized_variants:
            key = item.lower()
            if not key or key in seen:
                continue
            seen.add(key)
            ordered.append(item)
        return ordered

    def _normalize_reference_image_roles(self, image_paths: List[str], roles: List[str]) -> List[str]:
        path_count = len(image_paths or [])
        if path_count <= 0:
            return []

        normalized = [
            self._normalize_reference_image_role(roles[index] if index < len(roles or []) else "")
            for index in range(path_count)
        ]
        if "base" not in normalized:
            normalized[0] = "base"
        else:
            base_index = normalized.index("base")
            normalized = ["reference" if role == "base" and index != base_index else role for index, role in enumerate(normalized)]
        return normalized

    def _ordered_reference_media_names(
        self,
        media_items: List[Dict[str, str]],
        fallback_names: List[str] | None = None,
    ) -> List[str]:
        ordered: List[str] = []
        seen: set[str] = set()

        def push(name: str) -> None:
            safe_name = str(name or "").strip()
            if not safe_name or safe_name in seen:
                return
            seen.add(safe_name)
            ordered.append(safe_name)

        for role in ("base", "product", "logo", "reference"):
            for item in media_items:
                if str(item.get("role") or "") == role:
                    push(item.get("media_name", ""))

        for name in fallback_names or []:
            push(name)
        return ordered

    def _normalize_local_upload_paths(self, values: List[str]) -> List[str]:
        roots = [UPLOADS_DIR.resolve()]
        normalized: List[str] = []
        seen: set[str] = set()
        for value in values:
            raw = str(value or "").strip()
            if not raw:
                continue
            try:
                resolved = Path(raw).expanduser().resolve()
            except OSError:
                continue
            if not resolved.exists() or not resolved.is_file():
                continue
            if not self._path_within_roots(resolved, roots):
                continue
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(key)
        return normalized

    async def _resolve_image_reference_media(self, client: Any, job_id: str, request: CreateJobRequest) -> List[str]:
        reference_media_names = self._normalize_reference_media_names(request.reference_media_names or [])
        reference_image_paths = self._normalize_local_upload_paths(request.reference_image_paths or [])
        if not reference_image_paths:
            return reference_media_names

        reference_roles = self._normalize_reference_image_roles(reference_image_paths, request.reference_image_roles or [])
        total = len(reference_image_paths)
        await self.store.append_log(job_id, f"Đang chuẩn bị {total} ảnh tham chiếu để ghép/chỉnh ảnh.")
        uploaded_items: List[Dict[str, str]] = []
        for index, image_path in enumerate(reference_image_paths):
            role = reference_roles[index] if index < len(reference_roles) else ("base" if index == 0 else "reference")
            role_label = self.REFERENCE_IMAGE_ROLE_LABELS.get(role, "tham chiếu")
            await self._set_job_progress(
                job_id,
                "sending_request",
                f"Em đang tải ảnh {role_label} {index + 1}/{total} lên Flow trước khi chỉnh ảnh.",
            )
            await self.store.append_log(job_id, f"Đang tải ảnh {role_label} {index + 1}/{total}: {Path(image_path).name}")
            media_name = await self._upload_project_image_robust(client, image_path)
            if media_name:
                uploaded_items.append({"role": role, "media_name": media_name})

        return self._ordered_reference_media_names(uploaded_items, reference_media_names)

    async def _upload_project_image_robust(self, client: Any, image_path: str) -> str:
        image_file = Path(str(image_path or "")).expanduser().resolve()
        if not image_file.exists():
            raise RuntimeError(f"Khong tim thay anh de tai len: {image_file}")

        page = await client._bm.page()
        project_url = str(
            getattr(client, "_project_url", "")
            or getattr(getattr(client, "_api", None), "_project_page_url", "")
            or self._project_url(getattr(client, "project_id", ""))
        ).strip()
        await self._ensure_valid_flow_project_page(page, project_url)

        before_data = await client._api.get_project_data()
        known_media = self._project_media_names(before_data)

        selectors = [
            'input[type="file"][accept*="image"]',
            'input[type="file"]',
        ]
        uploaded = False
        for selector in selectors:
            locator = page.locator(selector)
            count = await locator.count()
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    await candidate.set_input_files(str(image_file))
                    uploaded = True
                    break
                except Exception:
                    continue
            if uploaded:
                break

        if not uploaded:
            for trigger in (
                page.locator("button").filter(has_text="Add Media").first,
                page.get_by_text("Add Media", exact=True).first,
                page.locator("button").filter(has_text="Upload image").first,
                page.get_by_text("Upload image", exact=True).first,
            ):
                try:
                    if await trigger.count() == 0:
                        continue
                    await trigger.click(force=True)
                    await asyncio.sleep(0.5)
                    for selector in selectors:
                        locator = page.locator(selector)
                        count = await locator.count()
                        for index in range(count):
                            candidate = locator.nth(index)
                            try:
                                await candidate.set_input_files(str(image_file))
                                uploaded = True
                                break
                            except Exception:
                                continue
                        if uploaded:
                            break
                    if uploaded:
                        break
                except Exception:
                    continue

        if not uploaded:
            raise RuntimeError(f"Failed to upload: {image_file}")

        deadline = time.monotonic() + 25.0
        while time.monotonic() < deadline:
            data = await client._api.get_project_data()
            for workflow in data.get("projectContents", {}).get("workflows", []) or []:
                media_name = str((workflow.get("metadata") or {}).get("primaryMediaId") or "").strip()
                if media_name and media_name not in known_media:
                    return media_name
                for media in workflow.get("medias", []) or []:
                    media_name = str(media.get("name") or "").strip()
                    if media_name and media_name not in known_media:
                        return media_name
            await asyncio.sleep(1.0)

        raise RuntimeError(f"Flow da nhan thao tac upload nhung chua thay anh xuat hien: {image_file.name}")

    def _project_media_names(self, project_data: Dict[str, Any]) -> set[str]:
        names: set[str] = set()
        for workflow in project_data.get("projectContents", {}).get("workflows", []) or []:
            metadata = workflow.get("metadata", {}) or {}
            primary_media_id = str(metadata.get("primaryMediaId") or "").strip()
            if primary_media_id:
                names.add(primary_media_id)
            for media in workflow.get("medias", []) or []:
                media_name = str(media.get("name") or "").strip()
                if media_name:
                    names.add(media_name)
        return names

    async def _generate_image_edit_result(
        self,
        client: Any,
        prompt: str,
        *,
        model: str,
        aspect: str,
        count: int,
        reference_media_names: List[str],
        workflow_id: str = "",
    ) -> List[Any]:
        normalized_media_names = self._normalize_reference_media_names(reference_media_names)
        if not normalized_media_names:
            raise RuntimeError("Chưa có ảnh nào để dùng làm đầu vào chỉnh sửa.")

        base_media_name = normalized_media_names[0]
        extra_reference_media_names = normalized_media_names[1:]
        resolved_workflow_id = str(workflow_id or "").strip() or await self._find_workflow_id_for_media(client, base_media_name)
        if not resolved_workflow_id:
            raise RuntimeError(
                "Google Flow chưa tìm thấy workflow gắn với ảnh gốc. Hãy thử tải lại ảnh rồi chạy lại giúp em."
            )

        client_context = dict(await client._api._client_context())
        client_context["workflowId"] = resolved_workflow_id

        image_inputs = [
            {
                "imageInputType": "IMAGE_INPUT_TYPE_BASE_IMAGE",
                "name": base_media_name,
            }
        ]
        image_inputs.extend(
            {
                "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE",
                "name": media_name,
            }
            for media_name in extra_reference_media_names
        )

        body = {
            "clientContext": client_context,
            "mediaGenerationContext": {"batchId": str(uuid.uuid4())},
            "useNewMedia": True,
            "requests": [
                {
                    "clientContext": dict(client_context),
                    "imageModelName": self._image_edit_model_name(model),
                    "imageAspectRatio": self._image_api_aspect_ratio(aspect),
                    "structuredPrompt": {"parts": [{"text": prompt}]},
                    "seed": random.randint(0, 2**31 - 1),
                    "imageInputs": list(image_inputs),
                }
                for _ in range(max(1, min(4, int(count or 1))))
            ],
        }
        data = await client._api._fetch(
            "POST",
            f"projects/{client._api.project_id}/flowMedia:batchGenerateImages",
            body,
        )

        from flow._api import GeneratedImage

        images = [GeneratedImage(item) for item in data.get("media", [])]
        for image in images:
            image.prompt = prompt
        if not images:
            raise RuntimeError("Google Flow không trả ảnh nào về từ yêu cầu chỉnh sửa hiện tại.")
        return images

    async def _generate_images_with_retry(
        self,
        client: Any,
        job_id: str,
        request: CreateJobRequest,
        reference_media_names: List[str],
    ) -> List[Any]:
        try:
            return await self._generate_images_once(client, request, reference_media_names)
        except Exception as exc:
            if not self._is_recaptcha_error(exc):
                raise

            await self.store.append_log(
                job_id,
                "Flow vua bat reCAPTCHA khi tao anh. Em dang chuyen sang duong chay qua giao dien Flow de thu lai.",
            )
            await self._set_job_progress(
                job_id,
                "sending_request",
                "Flow dang yeu cau xac nhan reCAPTCHA. Em dang tai lai trang project va gui lai bang giao dien Flow.",
            )
            await self._reload_flow_project_page(client)
            return await self._generate_images_via_ui(client, request, reference_media_names)

    async def _generate_images_once(
        self,
        client: Any,
        request: CreateJobRequest,
        reference_media_names: List[str],
    ) -> List[Any]:
        target_count = max(1, min(4, int(request.count or 1)))
        if reference_media_names:
            return await self._generate_image_edit_result(
                client,
                request.prompt,
                model=request.model,
                aspect=request.aspect,
                count=target_count,
                reference_media_names=reference_media_names,
                workflow_id=request.workflow_id or "",
            )
        return await client._api.generate_image(
            request.prompt,
            model=self._image_api_model_name(request.model),
            aspect_ratio=self._image_api_aspect_ratio(request.aspect),
            count=target_count,
        )

    async def _generate_images_via_ui(
        self,
        client: Any,
        request: CreateJobRequest,
        reference_media_names: List[str],
    ) -> List[Any]:
        if reference_media_names:
            if len(reference_media_names) > 1:
                raise RuntimeError(
                    "Flow dang chan nhanh ghep nhieu anh bang reCAPTCHA, nen em chua the fallback UI an toan cho hon 1 anh tham chieu."
                )
            return await self._generate_single_reference_image_via_ui(
                client,
                request.prompt,
                model=request.model,
                workflow_id=request.workflow_id or "",
                reference_media_name=reference_media_names[0],
                count=max(1, min(4, int(request.count or 1))),
                timeout_s=max(30, int(request.timeout_s or self.store.snapshot().config.generation_timeout_s or 300)),
            )
        return await client.generate_image(
            request.prompt,
            model=self._image_ui_model_label(request.model),
            aspect=request.aspect,
            count=max(1, min(4, int(request.count or 1))),
            timeout_s=max(30, int(request.timeout_s or self.store.snapshot().config.generation_timeout_s or 300)),
        )

    async def _generate_single_reference_image_via_ui(
        self,
        client: Any,
        prompt: str,
        *,
        model: str,
        reference_media_name: str,
        workflow_id: str = "",
        count: int = 1,
        timeout_s: int = 120,
    ) -> List[Any]:
        from flow._ui_interceptor import UIInterceptor

        resolved_workflow_id = str(workflow_id or "").strip() or await self._find_workflow_id_for_media(client, reference_media_name)
        if not resolved_workflow_id:
            raise RuntimeError("Google Flow chua tim thay workflow cua anh goc de mo man hinh chinh anh.")

        page = await client._bm.page()
        edit_url = f"{self._project_url(client.project_id).rstrip('/')}/edit/{resolved_workflow_id}"
        try:
            await page.goto(edit_url, wait_until="domcontentloaded", timeout=60_000)
        except Exception:
            await page.goto(edit_url, wait_until="commit", timeout=60_000)
        await asyncio.sleep(2.5)

        interceptor = UIInterceptor()
        interceptor.attach(page)
        interceptor.clear()

        try:
            await client._ui.open_settings_panel(page)
            await client._ui.select_image_model(page, self._image_ui_model_label(model))
            await client._ui.set_count(page, max(1, min(4, int(count or 1))))
        except Exception:
            pass

        filled = await client._ui.fill_prompt(page, prompt)
        if not filled:
            raise RuntimeError("Google Flow chua dien duoc prompt vao man hinh chinh anh.")

        clicked = await client._ui.click_submit(page)
        if not clicked:
            raise RuntimeError("Google Flow chua bam duoc nut tao anh o man hinh chinh anh.")

        try:
            entry = await interceptor.wait_for(
                "batchGenerateImages",
                timeout=max(30.0, min(120.0, float(timeout_s or 120))),
                require_success=True,
            )
        except Exception as exc:
            detail = str(exc or "").lower()
            if "timed out" in detail or "timeout" in detail or "recaptcha" in detail:
                raise RuntimeError(
                    "Google Flow co the dang doi xac nhan reCAPTCHA tren tab Flow. "
                    "Hay mo tab Google Flow, xac nhan neu thay captcha, roi bam Chay lai."
                ) from exc
            raise
        images = self._parse_images_from_flow_payload(entry.resp, prompt=prompt, fallback_workflow_id=resolved_workflow_id)
        if not images:
            raise RuntimeError("Google Flow khong tra anh nao ve tu man hinh chinh anh.")
        return images[: max(1, min(4, int(count or 1)))]

    async def _find_workflow_id_for_media(self, client: Any, media_name: str) -> str:
        safe_media_name = str(media_name or "").strip()
        if not safe_media_name:
            return ""

        for attempt in range(3):
            project_data = await client._api.get_project_data()
            workflows = project_data.get("projectContents", {}).get("workflows", [])
            for workflow in workflows:
                workflow_id = str(workflow.get("name") or "").strip()
                if not workflow_id:
                    continue
                metadata = workflow.get("metadata", {}) or {}
                if str(metadata.get("primaryMediaId") or "").strip() == safe_media_name:
                    return workflow_id
                for media in workflow.get("medias", []) or []:
                    if str(media.get("name") or "").strip() == safe_media_name:
                        return workflow_id
            if attempt < 2:
                await asyncio.sleep(1)

        return ""

    async def _reload_flow_project_page(self, client: Any) -> None:
        page = await client._bm.page()
        project_url = str(
            getattr(client, "_project_url", "")
            or getattr(getattr(client, "_api", None), "_project_page_url", "")
            or self._project_url(getattr(client, "project_id", ""))
        ).strip()
        if not project_url:
            return

        await self._ensure_valid_flow_project_page(page, project_url)
        try:
            await page.reload(wait_until="networkidle", timeout=60_000)
        except Exception:
            try:
                await page.reload(wait_until="domcontentloaded", timeout=60_000)
            except Exception:
                await self._ensure_valid_flow_project_page(page, project_url)

        try:
            ready = await page.wait_for_function(
                "() => !!window.grecaptcha?.enterprise?.execute",
                timeout=15_000,
            )
            await ready.dispose()
        except Exception:
            pass
        await asyncio.sleep(2.0)

    def _is_recaptcha_error(self, exc: Exception) -> bool:
        detail = str(exc or "").lower()
        return "recaptcha" in detail and "failed" in detail

    def _parse_images_from_flow_payload(
        self,
        payload: Any,
        *,
        prompt: str,
        fallback_workflow_id: str = "",
    ) -> List[Any]:
        from flow._api import GeneratedImage

        response = payload if isinstance(payload, dict) else {}
        images: List[Any] = []

        for media_item in response.get("media", []) or []:
            if not isinstance(media_item, dict):
                continue
            image = GeneratedImage.__new__(GeneratedImage)
            image._raw = media_item
            image.media_name = str(media_item.get("name") or media_item.get("mediaName") or "").strip()
            image.project_id = str(media_item.get("projectId") or "").strip()
            image.workflow_id = str(media_item.get("workflowId") or fallback_workflow_id or "").strip()
            generated = ((media_item.get("image") or {}).get("generatedImage") or {})
            image.fife_url = str(
                generated.get("fifeUrl")
                or generated.get("url")
                or media_item.get("fifeUrl")
                or ""
            ).strip()
            image.seed = generated.get("seed", 0)
            image.model = str(generated.get("modelNameType") or generated.get("model") or "").strip()
            image.prompt = str(generated.get("prompt") or prompt or "").strip()
            image.dimensions = media_item.get("dimensions", {}) or {}
            image.file_path = None
            images.append(image)

        if images:
            return images

        for item in response.get("generatedImages", []) or []:
            if not isinstance(item, dict):
                continue
            image = GeneratedImage.__new__(GeneratedImage)
            image._raw = item
            image.media_name = str(item.get("mediaName") or item.get("name") or "").strip()
            image.project_id = ""
            image.workflow_id = fallback_workflow_id
            image.fife_url = str(item.get("fifeUrl") or item.get("url") or "").strip()
            image.seed = int(item.get("seed", 0) or 0)
            image.model = str(item.get("modelNameType") or item.get("model") or "").strip()
            image.prompt = str(item.get("prompt") or prompt or "").strip()
            image.dimensions = item.get("dimensions", {}) or {}
            image.file_path = None
            images.append(image)
        return images

    async def _wait_for_video_with_progress(
        self,
        client: Any,
        job_id: str,
        video_job: Any,
        label: str,
        *,
        poll_s: float,
        timeout_s: int,
    ) -> Any:
        await self.store.patch_job(job_id, status="polling")
        started_at = time.monotonic()
        last_state = ""
        last_logged_at = -999.0

        while True:
            elapsed = time.monotonic() - started_at
            if elapsed > timeout_s:
                raise RuntimeError(f"{label} đã hết thời gian chờ sau {timeout_s} giây.")

            status = await client.poll_video(video_job.media_name)
            remote_state = getattr(status, "status", "")
            state_message = self._describe_remote_status(remote_state)

            should_log = remote_state != last_state or (elapsed - last_logged_at) >= max(15.0, poll_s * 3)
            if should_log:
                if getattr(status, "complete", False):
                    await self._set_job_progress(
                        job_id,
                        "saving_artifacts",
                        f"{label}: Flow đã hoàn tất render sau {int(elapsed)} giây. Em đang chuẩn bị lưu artifact.",
                        remote_status=remote_state,
                    )
                    await self.store.append_log(job_id, f"{label}: đã hoàn tất sau {int(elapsed)} giây.")
                elif getattr(status, "failed", False):
                    await self._set_job_progress(
                        job_id,
                        "polling",
                        f"{label}: Flow báo thất bại với trạng thái {state_message}.",
                        remote_status=remote_state,
                    )
                    await self.store.append_log(job_id, f"{label}: thất bại với trạng thái {state_message}.")
                else:
                    await self._set_job_progress(
                        job_id,
                        "polling",
                        f"{label}: {state_message} ({int(elapsed)} giây).",
                        remote_status=remote_state,
                    )
                    await self.store.append_log(job_id, f"{label}: {state_message} ({int(elapsed)} giây).")
                last_logged_at = elapsed
                last_state = remote_state

            if getattr(status, "complete", False):
                await self._set_job_progress(
                    job_id,
                    "saving_artifacts",
                    f"{label}: Flow đã hoàn tất render. Em đang chuẩn bị lưu artifact.",
                    remote_status=remote_state,
                )
                return status

            if getattr(status, "failed", False):
                raise RuntimeError(f"{label} thất bại với trạng thái {state_message}.")

            await asyncio.sleep(poll_s)

    def _describe_remote_status(self, status: str) -> str:
        mapping = {
            "MEDIA_GENERATION_STATUS_PENDING": "đang chờ xử lý",
            "MEDIA_GENERATION_STATUS_RUNNING": "đang tạo nội dung",
            "MEDIA_GENERATION_STATUS_IN_PROGRESS": "đang xử lý",
            "MEDIA_GENERATION_STATUS_COMPLETE": "đã hoàn tất",
            "MEDIA_GENERATION_STATUS_SUCCESS": "đã hoàn tất",
            "MEDIA_GENERATION_STATUS_SUCCESSFUL": "đã hoàn tất",
            "MEDIA_GENERATION_STATUS_FAILED": "đã thất bại",
            "MEDIA_GENERATION_STATUS_REJECTED": "bị từ chối",
        }
        return mapping.get(status, status.replace("_", " ").lower() if status else "đang xử lý")
