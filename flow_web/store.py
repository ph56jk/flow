from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from .messages import classify_job_error, humanize_flow_error
from .paths import STATE_FILE, ensure_app_dirs
from .schemas import (
    AppConfig,
    JobArtifact,
    JobErrorSnapshot,
    JobLog,
    JobProgressHint,
    JobProgressMilestone,
    JobProgressSnapshot,
    JobRecord,
    JobReplayField,
    JobReplaySnapshot,
    JobRetrySnapshot,
    SkillRecord,
    StateSnapshot,
    normalized_app_config,
    utc_now,
)


def _model_dump(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def _model_validate(model_cls: Any, payload: Dict[str, Any]) -> Any:
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(payload)
    return model_cls.parse_obj(payload)


class StateStore:
    def __init__(self) -> None:
        ensure_app_dirs()
        self._lock = asyncio.Lock()
        self._state = self._load()
        self._normalize_saved_config()
        self._normalize_saved_jobs()
        self._repair_incomplete_jobs()

    def snapshot(self) -> StateSnapshot:
        return self._state

    async def replace_config(self, config: AppConfig) -> AppConfig:
        async with self._lock:
            self._state.config = normalized_app_config(config)
            await self._save_locked()
        return self._state.config

    async def list_jobs(self) -> List[JobRecord]:
        return list(self._state.jobs)

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        return next((job for job in self._state.jobs if job.id == job_id), None)

    async def add_job(self, job: JobRecord) -> JobRecord:
        async with self._lock:
            self._state.jobs.insert(0, job)
            self._state.jobs = self._state.jobs[:50]
            self._sync_job_error_snapshot(job)
            self._sync_job_retry_snapshot(job)
            self._sync_job_replay_snapshot(job)
            self._sync_job_progress_snapshot(job)
            await self._save_locked()
        return job

    def get_skill(self, skill_id: str) -> Optional[SkillRecord]:
        return next((skill for skill in self._state.skills if skill.id == skill_id), None)

    async def add_skill(self, skill: SkillRecord) -> SkillRecord:
        async with self._lock:
            self._state.skills.insert(0, skill)
            self._state.skills = self._state.skills[:100]
            await self._save_locked()
        return skill

    async def replace_skills(self, skills: List[SkillRecord]) -> List[SkillRecord]:
        async with self._lock:
            self._state.skills = list(skills)[:100]
            await self._save_locked()
        return self._state.skills

    async def delete_skill(self, skill_id: str) -> bool:
        async with self._lock:
            original_count = len(self._state.skills)
            self._state.skills = [skill for skill in self._state.skills if skill.id != skill_id]
            changed = len(self._state.skills) != original_count
            if changed:
                await self._save_locked()
            return changed

    async def patch_job(self, job_id: str, **changes: Any) -> JobRecord:
        async with self._lock:
            job = self.get_job(job_id)
            if job is None:
                raise KeyError(job_id)
            for key, value in changes.items():
                if key == "error":
                    value = humanize_flow_error(value)
                setattr(job, key, value)
            job.updated_at = utc_now()
            self._sync_job_error_snapshot(job)
            self._sync_job_retry_snapshot(job)
            self._sync_job_replay_snapshot(job)
            self._sync_job_progress_snapshot(job)
            await self._save_locked()
            return job

    async def set_progress_hint(
        self,
        job_id: str,
        *,
        stage: str = "",
        detail: str = "",
        remote_status: str = "",
    ) -> JobRecord:
        async with self._lock:
            job = self.get_job(job_id)
            if job is None:
                raise KeyError(job_id)

            now = utc_now()
            if any([stage.strip(), detail.strip(), remote_status.strip()]):
                job.progress_hint = JobProgressHint(
                    stage=stage.strip(),
                    detail=detail.strip(),
                    remote_status=remote_status.strip(),
                    updated_at=now,
                )
            else:
                job.progress_hint = JobProgressHint()

            job.updated_at = now
            self._sync_job_progress_snapshot(job)
            await self._save_locked()
            return job

    async def append_log(self, job_id: str, message: str) -> JobRecord:
        async with self._lock:
            job = self.get_job(job_id)
            if job is None:
                raise KeyError(job_id)
            job.logs.append(JobLog(message=humanize_flow_error(message)))
            job.updated_at = utc_now()
            self._sync_job_replay_snapshot(job)
            self._sync_job_progress_snapshot(job)
            await self._save_locked()
            return job

    async def replace_artifacts(self, job_id: str, artifacts: List[JobArtifact]) -> JobRecord:
        async with self._lock:
            job = self.get_job(job_id)
            if job is None:
                raise KeyError(job_id)
            job.artifacts = artifacts
            job.updated_at = utc_now()
            self._sync_job_replay_snapshot(job)
            self._sync_job_progress_snapshot(job)
            await self._save_locked()
            return job

    async def clear_replay_metadata(self, job_ids: Optional[List[str]] = None) -> List[str]:
        requested_ids = {str(job_id or "").strip() for job_id in (job_ids or []) if str(job_id or "").strip()}
        async with self._lock:
            cleared: List[str] = []
            for job in self._state.jobs:
                if requested_ids and job.id not in requested_ids:
                    continue

                snapshot = getattr(job, "replay_snapshot", JobReplaySnapshot())
                if job.status != "interrupted" or snapshot.cleared_at:
                    continue

                job.replay_snapshot = JobReplaySnapshot(cleared_at=utc_now())
                job.updated_at = utc_now()
                cleared.append(job.id)

            if cleared:
                await self._save_locked()
            return cleared

    async def clear_artifact_local_refs(self, refs: List[tuple[str, int]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, set[int]] = {}
        for job_id, artifact_index in refs:
            safe_job_id = str(job_id or "").strip()
            if not safe_job_id:
                continue
            grouped.setdefault(safe_job_id, set()).add(int(artifact_index))

        async with self._lock:
            cleared: List[Dict[str, Any]] = []
            for job in self._state.jobs:
                artifact_indexes = grouped.get(job.id)
                if not artifact_indexes:
                    continue

                changed = False
                for artifact_index in sorted(artifact_indexes):
                    if artifact_index < 0 or artifact_index >= len(job.artifacts):
                        continue

                    artifact = job.artifacts[artifact_index]
                    if not str(artifact.local_path or "").strip() and not str(artifact.public_url or "").strip():
                        continue

                    artifact.local_path = ""
                    artifact.public_url = ""
                    changed = True
                    cleared.append({
                        "job_id": job.id,
                        "artifact_index": artifact_index,
                    })

                if changed:
                    job.updated_at = utc_now()
                    self._sync_job_replay_snapshot(job)
                    self._sync_job_progress_snapshot(job)

            if cleared:
                await self._save_locked()
            return cleared

    async def remove_jobs(self, job_ids: List[str]) -> List[str]:
        requested_ids = {str(job_id or "").strip() for job_id in (job_ids or []) if str(job_id or "").strip()}
        if not requested_ids:
            return []

        async with self._lock:
            kept_jobs: List[JobRecord] = []
            removed: List[str] = []
            for job in self._state.jobs:
                if job.id in requested_ids:
                    removed.append(job.id)
                    continue
                kept_jobs.append(job)

            if removed:
                self._state.jobs = kept_jobs
                await self._save_locked()
            return removed

    def _load(self) -> StateSnapshot:
        if not STATE_FILE.exists():
            return StateSnapshot()
        try:
            payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return _model_validate(StateSnapshot, payload)
        except Exception:
            return StateSnapshot()

    async def _save_locked(self) -> None:
        STATE_FILE.write_text(
            json.dumps(_model_dump(self._state), indent=2),
            encoding="utf-8",
        )

    def _normalize_saved_config(self) -> None:
        normalized = normalized_app_config(self._state.config)
        if _model_dump(normalized) == _model_dump(self._state.config):
            return
        self._state.config = normalized
        STATE_FILE.write_text(
            json.dumps(_model_dump(self._state), indent=2),
            encoding="utf-8",
        )

    def _normalize_saved_jobs(self) -> None:
        changed = False
        for job in self._state.jobs:
            normalized_error = humanize_flow_error(job.error)
            if normalized_error != job.error:
                job.error = normalized_error
                changed = True

            for log in job.logs:
                normalized_message = humanize_flow_error(log.message)
                if normalized_message != log.message:
                    log.message = normalized_message
                    changed = True

            snapshot_changed = self._sync_job_error_snapshot(job)
            changed = changed or snapshot_changed

            retry_changed = self._sync_job_retry_snapshot(job)
            changed = changed or retry_changed

            replay_changed = self._sync_job_replay_snapshot(job)
            changed = changed or replay_changed

            progress_changed = self._sync_job_progress_snapshot(job)
            changed = changed or progress_changed

        if changed:
            STATE_FILE.write_text(
                json.dumps(_model_dump(self._state), indent=2),
                encoding="utf-8",
            )

    def _repair_incomplete_jobs(self) -> None:
        changed = False
        for job in self._state.jobs:
            if job.status in {"queued", "running", "polling"}:
                previous_status = job.status
                job.status = "interrupted"
                job.error = "Máy chủ đã khởi động lại khi tác vụ đang chạy."
                job.updated_at = utc_now()
                self._sync_job_error_snapshot(job)
                self._sync_job_replay_snapshot(job, previous_status=previous_status)
                self._sync_job_progress_snapshot(job)
                changed = True
        if changed:
            STATE_FILE.write_text(
                json.dumps(_model_dump(self._state), indent=2),
                encoding="utf-8",
            )

    def _sync_job_error_snapshot(self, job: JobRecord) -> bool:
        current = _model_dump(getattr(job, "error_snapshot", JobErrorSnapshot()))
        if job.error:
            target = classify_job_error(job.error, job_type=job.type)
        else:
            target = JobErrorSnapshot()
        updated = _model_dump(target)
        if current == updated:
            return False
        job.error_snapshot = target
        return True

    def _sync_job_retry_snapshot(self, job: JobRecord) -> bool:
        current_source_job_id = str(getattr(job, "source_job_id", "") or "").strip()
        input_payload = job.input if isinstance(job.input, dict) else {}
        source_job_id = str(current_source_job_id or input_payload.get("source_job_id", "") or "").strip()
        source_job_changed = source_job_id != current_source_job_id
        if source_job_changed:
            job.source_job_id = source_job_id

        current = _model_dump(getattr(job, "retry_snapshot", JobRetrySnapshot()))
        if not source_job_id:
            target = JobRetrySnapshot()
        else:
            source_job = self.get_job(source_job_id)
            existing = getattr(job, "retry_snapshot", JobRetrySnapshot())
            target = JobRetrySnapshot(
                is_retry=True,
                source_job_id=source_job_id,
                source_job_title=(
                    (source_job.title if source_job and source_job.title else "")
                    or existing.source_job_title
                    or source_job_id
                ),
                source_job_type=(source_job.type if source_job else "") or existing.source_job_type,
                source_job_status=(source_job.status if source_job else "") or existing.source_job_status,
                source_job_created_at=(source_job.created_at if source_job else "") or existing.source_job_created_at,
            )

        updated = _model_dump(target)
        if not source_job_changed and current == updated:
            return False
        job.retry_snapshot = target
        return True

    def _sync_job_replay_snapshot(self, job: JobRecord, *, previous_status: str = "") -> bool:
        current = _model_dump(getattr(job, "replay_snapshot", JobReplaySnapshot()))
        existing = getattr(job, "replay_snapshot", JobReplaySnapshot())

        if existing.cleared_at:
            target = JobReplaySnapshot(cleared_at=existing.cleared_at)
        elif job.status != "interrupted":
            target = JobReplaySnapshot()
        else:
            recovery_input = self._build_replay_recovery_input(job)
            group_key, group_label = self._replay_group(job.type)
            last_log = job.logs[-1] if job.logs else None
            resolved_previous_status = previous_status or existing.previous_status
            resolved_previous_label = existing.previous_status_label or self._job_status_label(resolved_previous_status)
            prompt_excerpt = self._trim_text(str(recovery_input.get("prompt", "")).strip(), 180)

            target = JobReplaySnapshot(
                available=True,
                reason="server_restart",
                reason_label="App đã khởi động lại",
                summary=self._replay_summary(job.type, resolved_previous_label),
                group_key=group_key,
                group_label=group_label,
                previous_status=resolved_previous_status,
                previous_status_label=resolved_previous_label,
                last_log_at=getattr(last_log, "at", ""),
                last_log_message=getattr(last_log, "message", "") or "Chưa kịp ghi log trước khi app khởi động lại.",
                interrupted_at=str(job.updated_at or ""),
                prompt_excerpt=prompt_excerpt,
                input_fields=self._build_replay_fields(job.type, recovery_input),
                recovery_input=recovery_input,
            )

        updated = _model_dump(target)
        if current == updated:
            return False
        job.replay_snapshot = target
        return True

    def _sync_job_progress_snapshot(self, job: JobRecord) -> bool:
        current = _model_dump(getattr(job, "progress_snapshot", JobProgressSnapshot()))
        target = self._build_job_progress_snapshot(job)
        updated = _model_dump(target)
        if current == updated:
            return False
        job.progress_snapshot = target
        return True

    def _build_job_progress_snapshot(self, job: JobRecord) -> JobProgressSnapshot:
        hint = getattr(job, "progress_hint", JobProgressHint())
        last_log = job.logs[-1] if job.logs else None
        log_stage, log_detail = self._infer_progress_stage_from_log(job, getattr(last_log, "message", ""))
        stage = ""
        detail = ""

        if job.status == "completed":
            stage = "completed"
            detail = getattr(last_log, "message", "") or self._default_progress_detail(job.type, stage, "")
        elif job.status == "failed":
            stage = "failed"
            detail = job.error or getattr(last_log, "message", "") or "Tác vụ đã thất bại."
        elif job.status == "interrupted":
            stage = "interrupted"
            detail = getattr(last_log, "message", "") or "Tác vụ bị ngắt khi app khởi động lại."
        elif job.artifacts and job.status in {"running", "polling"}:
            stage = "saving_artifacts"
            detail = f"Đang lưu {len(job.artifacts)} artifact vào lịch sử tác vụ."
        elif hint.stage:
            stage = hint.stage
            detail = hint.detail or log_detail or self._default_progress_detail(job.type, hint.stage, hint.remote_status)
        elif log_stage:
            stage = log_stage
            detail = log_detail or self._default_progress_detail(job.type, log_stage, "")
        elif job.status == "polling":
            stage = "polling"
            detail = self._default_progress_detail(job.type, stage, hint.remote_status)
        elif job.status == "running":
            stage = "launching_browser" if job.type == "login" else "connecting"
            detail = self._default_progress_detail(job.type, stage, "")
        else:
            stage = "queued"
            detail = self._default_progress_detail(job.type, stage, "")

        sequence = self._progress_stage_sequence(job.type)
        sequence_keys = [item["key"] for item in sequence]
        progress_stage = stage if stage in sequence_keys else ""
        if not progress_stage:
            if job.status in {"failed", "interrupted"}:
                progress_stage = hint.stage if hint.stage in sequence_keys else log_stage if log_stage in sequence_keys else "queued"
            elif job.status == "completed":
                progress_stage = "completed"
            elif job.status == "polling" and "polling" in sequence_keys:
                progress_stage = "polling"
            elif job.status == "running" and len(sequence_keys) > 1:
                progress_stage = sequence_keys[1]
            else:
                progress_stage = "launching_browser" if job.type == "login" and "launching_browser" in sequence_keys else sequence_keys[0]

        current_index = sequence_keys.index(progress_stage) if progress_stage in sequence_keys else 0
        current_at = (
            getattr(hint, "updated_at", "")
            or getattr(last_log, "at", "")
            or (job.updated_at if stage != "queued" else job.created_at)
        )

        milestones: List[JobProgressMilestone] = []
        for index, item in enumerate(sequence):
            milestone_status = "pending"
            if job.status == "completed":
                milestone_status = "done"
            elif job.status in {"failed", "interrupted"}:
                if index < current_index:
                    milestone_status = "done"
                elif index == current_index:
                    milestone_status = "blocked"
            else:
                if index < current_index:
                    milestone_status = "done"
                elif index == current_index:
                    milestone_status = "current"

            milestone_detail = detail if item["key"] == progress_stage and detail else ""
            milestone_at = ""
            if item["key"] == "queued":
                milestone_at = job.created_at
            elif item["key"] == "completed" and job.status == "completed":
                milestone_at = job.updated_at
            elif item["key"] == progress_stage and milestone_status in {"current", "blocked"}:
                milestone_at = current_at

            milestones.append(
                JobProgressMilestone(
                    key=item["key"],
                    label=item["label"],
                    status=milestone_status,
                    detail=milestone_detail,
                    at=milestone_at,
                )
            )

        last_signal_at, last_signal_message = self._resolve_progress_signal(job, detail)
        return JobProgressSnapshot(
            stage=stage,
            stage_label=self._progress_stage_label(job.type, stage),
            detail=detail,
            is_active=job.status in {"queued", "running", "polling"},
            is_terminal=job.status in {"completed", "failed", "interrupted"},
            last_signal_at=last_signal_at,
            last_signal_message=last_signal_message,
            milestones=milestones,
        )

    def _progress_stage_sequence(self, job_type: str) -> List[Dict[str, str]]:
        if job_type == "login":
            return [
                {"key": "queued", "label": "Đã nhận yêu cầu"},
                {"key": "launching_browser", "label": "Mở Chromium"},
                {"key": "awaiting_login", "label": "Chờ đăng nhập xong"},
                {"key": "completed", "label": "Hoàn tất"},
            ]

        return [
            {"key": "queued", "label": "Đã nhận yêu cầu"},
            {"key": "connecting", "label": "Kết nối Flow"},
            {"key": "sending_request", "label": "Gửi yêu cầu"},
            {"key": "awaiting_response", "label": "Chờ Flow phản hồi"},
            {"key": "polling", "label": "Polling tiến trình"},
            {"key": "saving_artifacts", "label": "Lưu artifact"},
            {"key": "completed", "label": "Hoàn tất"},
        ]

    def _progress_stage_label(self, job_type: str, stage: str) -> str:
        if stage == "failed":
            return "Tác vụ đã lỗi"
        if stage == "interrupted":
            return "Tác vụ bị ngắt"

        for item in self._progress_stage_sequence(job_type):
            if item["key"] == stage:
                return item["label"]
        return self._job_status_label(stage)

    def _default_progress_detail(self, job_type: str, stage: str, remote_status: str) -> str:
        if job_type == "login":
            mapping = {
                "queued": "Yêu cầu đăng nhập đã được thêm vào hàng chờ.",
                "launching_browser": "Em đang mở Chromium để đi tới Google Flow.",
                "awaiting_login": "Chromium đã mở. Đang chờ chủ nhân hoàn tất đăng nhập Google Flow.",
                "completed": "Đăng nhập Google Flow đã hoàn tất.",
            }
            return mapping.get(stage, "")

        mapping = {
            "queued": "Yêu cầu đã được xếp hàng và sẽ được xử lý ngay khi Flow rảnh.",
            "connecting": "Em đang khởi tạo client và kết nối tới project Flow hiện tại.",
            "sending_request": "Em đang gửi payload từ form hiện tại sang Flow.",
            "awaiting_response": "Flow đã nhận yêu cầu. Đang chờ tín hiệu tiến trình đầu tiên.",
            "polling": f"Em đang polling trạng thái job từ Flow{f': {remote_status}' if remote_status else ''}.",
            "saving_artifacts": "Kết quả đã về. Em đang lưu artifact vào lịch sử tác vụ.",
            "completed": "Tác vụ đã hoàn tất.",
        }
        return mapping.get(stage, "")

    def _infer_progress_stage_from_log(self, job: JobRecord, message: str) -> tuple[str, str]:
        text = str(message or "").strip()
        lowered = text.lower()
        if not text:
            return "", ""

        if "đang mở chromium" in lowered:
            return ("launching_browser" if job.type == "login" else "connecting"), text
        if "đang khởi tạo kết nối tới flow" in lowered:
            return "connecting", text
        if "đã đăng nhập với tài khoản" in lowered:
            return "completed", text
        if "đã gửi" in lowered or "đã gửi chuyển động camera" in lowered or "đã gửi vị trí camera" in lowered:
            return "awaiting_response", text
        if "đã tạo " in lowered and " ảnh" in lowered:
            return "saving_artifacts", text
        if lowered.startswith("video ") or lowered.startswith("tác vụ "):
            if "đã hoàn tất" in lowered:
                return "saving_artifacts", text
            return "polling", text
        if "đang lưu kết quả vào" in lowered:
            return "saving_artifacts", text
        if "tác vụ đã hoàn tất" in lowered:
            return "completed", text
        if "thất bại" in lowered:
            return "failed", text
        return "", text

    def _resolve_progress_signal(self, job: JobRecord, detail: str) -> tuple[str, str]:
        hint = getattr(job, "progress_hint", JobProgressHint())
        last_log = job.logs[-1] if job.logs else None
        candidates = [
            (str(getattr(hint, "updated_at", "") or "").strip(), str(getattr(hint, "detail", "") or "").strip()),
            (str(getattr(last_log, "at", "") or "").strip(), str(getattr(last_log, "message", "") or "").strip()),
            (str(job.updated_at or "").strip(), str(detail or "").strip()),
        ]
        candidates = [candidate for candidate in candidates if candidate[0]]
        if not candidates:
            return "", ""
        best_at, best_message = max(candidates, key=lambda item: item[0])
        return best_at, best_message

    def _build_replay_recovery_input(self, job: JobRecord) -> Dict[str, Any]:
        input_payload = job.input if isinstance(job.input, dict) else {}
        raw_references = input_payload.get("reference_media_names", [])
        if not isinstance(raw_references, (list, tuple)):
            raw_references = [raw_references]

        def _as_int(value: Any, default: int = 0) -> int:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                return default
            return parsed

        def _as_float(value: Any, default: float = 0.0) -> float:
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                return default
            return parsed

        return {
            "type": str(input_payload.get("type", job.type) or job.type).strip(),
            "prompt": str(input_payload.get("prompt", "") or "").strip(),
            "aspect": str(input_payload.get("aspect", "") or "").strip(),
            "count": _as_int(input_payload.get("count"), 0),
            "start_image_path": str(input_payload.get("start_image_path", "") or "").strip(),
            "reference_media_names": [
                str(item).strip()
                for item in raw_references
                if str(item).strip()
            ],
            "media_id": str(input_payload.get("media_id", "") or "").strip(),
            "workflow_id": str(input_payload.get("workflow_id", "") or "").strip(),
            "motion": str(input_payload.get("motion", "") or "").strip(),
            "position": str(input_payload.get("position", "") or "").strip(),
            "resolution": str(input_payload.get("resolution", "") or "").strip(),
            "mask_x": _as_float(input_payload.get("mask_x"), 0.5),
            "mask_y": _as_float(input_payload.get("mask_y"), 0.5),
            "brush_size": _as_int(input_payload.get("brush_size"), 40),
            "timeout_s": _as_int(input_payload.get("timeout_s"), 0),
            "source_job_id": str(input_payload.get("source_job_id", "") or job.source_job_id or "").strip(),
        }

    def _build_replay_fields(self, job_type: str, recovery_input: Dict[str, Any]) -> List[JobReplayField]:
        fields: List[JobReplayField] = []
        aspect = str(recovery_input.get("aspect", "")).strip()
        count = int(recovery_input.get("count", 0) or 0)
        timeout_s = int(recovery_input.get("timeout_s", 0) or 0)
        start_image_path = str(recovery_input.get("start_image_path", "")).strip()
        media_id = str(recovery_input.get("media_id", "")).strip()
        workflow_id = str(recovery_input.get("workflow_id", "")).strip()
        references = recovery_input.get("reference_media_names", [])
        motion = str(recovery_input.get("motion", "")).strip()
        position = str(recovery_input.get("position", "")).strip()
        resolution = str(recovery_input.get("resolution", "")).strip()
        source_job_id = str(recovery_input.get("source_job_id", "")).strip()

        if aspect:
            fields.append(JobReplayField(label="Tỉ lệ", value=self._aspect_label(aspect)))
        if count > 0:
            fields.append(JobReplayField(label="Số lượng", value=str(count)))
        if start_image_path:
            fields.append(JobReplayField(label="Ảnh đầu vào", value=self._basename(start_image_path)))
        if references:
            fields.append(JobReplayField(label="Media tham chiếu", value=f"{len(references)} media id"))
        if media_id:
            fields.append(JobReplayField(label="Media ID", value=media_id))
        if workflow_id:
            fields.append(JobReplayField(label="Workflow ID", value=workflow_id))
        if motion:
            fields.append(JobReplayField(label="Chuyển động", value=motion))
        if position:
            fields.append(JobReplayField(label="Vị trí camera", value=position))
        if resolution and job_type == "upscale":
            fields.append(JobReplayField(label="Resolution", value=resolution.upper()))
        if job_type == "remove":
            fields.append(
                JobReplayField(
                    label="Mask",
                    value=f"x={recovery_input.get('mask_x', 0.5)}, y={recovery_input.get('mask_y', 0.5)}, cọ={recovery_input.get('brush_size', 40)}",
                )
            )
        if timeout_s > 0:
            fields.append(JobReplayField(label="Timeout", value=f"{timeout_s} giây"))
        if source_job_id:
            fields.append(JobReplayField(label="Nguồn retry", value=source_job_id[:8]))

        return fields

    def _replay_group(self, job_type: str) -> tuple[str, str]:
        normalized = str(job_type or "").strip()
        if normalized == "login":
            return "auth", "Cụm đăng nhập bị ngắt"
        if normalized == "video":
            return "video", "Cụm tạo video"
        if normalized == "image":
            return "image", "Cụm tạo ảnh"
        if normalized in {"extend", "upscale", "camera_motion", "camera_position", "insert", "remove"}:
            return "edit", "Cụm chỉnh sửa media"
        return "other", "Cụm interrupted work khác"

    def _replay_summary(self, job_type: str, previous_status_label: str) -> str:
        stage = (previous_status_label or "đang xử lý").lower()
        if job_type == "login":
            return f"Bị ngắt khi {stage}. Phiên đăng nhập cuối đã được giữ log để chủ nhân mở lại đăng nhập Google Flow ngay."
        if job_type == "video":
            return f"Bị ngắt khi {stage}. Prompt, tỉ lệ, ảnh đầu vào và timeout cuối đã được giữ để chủ nhân mở retry nhanh."
        if job_type == "image":
            return f"Bị ngắt khi {stage}. Prompt, tỉ lệ, media tham chiếu và timeout cuối đã được giữ để chủ nhân khôi phục nhanh."
        if job_type not in {"extend", "upscale", "camera_motion", "camera_position", "insert", "remove"}:
            return f"Bị ngắt khi {stage}. Log cuối và input recovery đã được giữ để chủ nhân tiếp tục công việc an toàn."
        return f"Bị ngắt khi {stage}. Media ID, workflow và tham số chỉnh sửa cuối đã được giữ để chủ nhân mở lại retry đúng form."

    def _job_status_label(self, status: str) -> str:
        mapping = {
            "queued": "Đang xếp hàng",
            "running": "Đang chạy",
            "polling": "Đang xử lý",
            "interrupted": "Bị ngắt",
        }
        return mapping.get(str(status or "").strip(), "")

    def _aspect_label(self, aspect: str) -> str:
        mapping = {
            "landscape": "Ngang 16:9",
            "portrait": "Dọc 9:16",
            "square": "Vuông 1:1",
        }
        return mapping.get(str(aspect or "").strip(), str(aspect or "").strip())

    def _basename(self, value: str) -> str:
        return str(value or "").replace("\\", "/").split("/")[-1]

    def _trim_text(self, value: str, limit: int) -> str:
        raw = str(value or "").strip().replace("\n", " ")
        if len(raw) <= limit:
            return raw
        return f"{raw[: max(0, limit - 3)].rstrip()}..."
