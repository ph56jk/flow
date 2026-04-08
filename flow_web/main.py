from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .paths import DOWNLOADS_DIR, STATIC_DIR, UPLOADS_DIR, ensure_app_dirs
from .schemas import (
    ArtifactOpenRequest,
    CleanupRequest,
    ConfigUpdateRequest,
    CreateJobRequest,
    DownloadRequest,
    PromptCreateRequest,
    ReplayCleanupRequest,
)
from .service import FlowWebService
from .store import StateStore


ENV_FILE = Path(__file__).resolve().parent.parent / ".env.local"


def _strip_env_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    return text


def load_local_env() -> None:
    if not ENV_FILE.exists():
        return
    try:
        raw_text = ENV_FILE.read_text(encoding="utf-8")
    except OSError:
        return
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _strip_env_quotes(value)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_app_dirs()
    load_local_env()
    store = StateStore()
    app.state.flow_service = FlowWebService(store)
    sync_task = asyncio.create_task(app.state.flow_service.ensure_media_skill_library())
    try:
        yield
    finally:
        sync_task.cancel()
        with suppress(asyncio.CancelledError):
            await sync_task


app = FastAPI(
    title="Flow Web UI",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/files/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/files/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")


def service(request: Request) -> FlowWebService:
    return request.app.state.flow_service


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/state")
async def get_state(request: Request) -> Dict[str, Any]:
    return service(request).get_state_payload()


@app.put("/api/config")
async def update_config(request: Request, payload: ConfigUpdateRequest) -> Dict[str, Any]:
    flow_service = service(request)
    config = await flow_service.update_config(payload)
    return {"config": config}


@app.post("/api/auth/login")
async def login(request: Request) -> Dict[str, Any]:
    flow_service = service(request)
    job = await flow_service.enqueue_login()
    return {"job": job}


@app.get("/api/credits")
async def credits(request: Request) -> Dict[str, Any]:
    return await service(request).get_credits()


@app.get("/api/workflows")
async def workflows(request: Request) -> Dict[str, Any]:
    return {"items": await service(request).get_workflows()}


@app.get("/api/models")
async def models(request: Request) -> Dict[str, Any]:
    return await service(request).get_model_config()


@app.post("/api/uploads")
async def upload_file(request: Request, file: UploadFile = File(...)) -> Dict[str, Any]:
    return await service(request).save_upload(file)


@app.post("/api/jobs")
async def create_job(request: Request, payload: CreateJobRequest) -> Dict[str, Any]:
    job = await service(request).enqueue_job(payload)
    return {"job": job}


@app.get("/api/skills")
async def list_skills(request: Request) -> Dict[str, Any]:
    return {"items": service(request).get_state()["skills"]}


@app.post("/api/skills/sync-media")
async def sync_media_skills(request: Request) -> Dict[str, Any]:
    return await service(request).sync_media_skills()


@app.post("/api/prompt-ai/generate")
async def generate_prompt_ai(request: Request, payload: PromptCreateRequest) -> Dict[str, Any]:
    return await service(request).generate_prompt_draft(payload)


@app.post("/api/jobs/{job_id}/download")
async def download_job_output(request: Request, job_id: str, payload: DownloadRequest) -> Dict[str, Any]:
    return await service(request).download_artifact(job_id, payload)


@app.post("/api/jobs/{job_id}/artifacts/open")
async def open_job_artifact(request: Request, job_id: str, payload: ArtifactOpenRequest) -> Dict[str, Any]:
    return await service(request).open_artifact(job_id, payload)


@app.get("/api/jobs/{job_id}/artifacts/{artifact_index}/file")
async def open_job_artifact_file(request: Request, job_id: str, artifact_index: int) -> FileResponse:
    return FileResponse(service(request).artifact_file_path(job_id, artifact_index))


@app.post("/api/replay-pack/cleanup")
async def cleanup_replay_pack(request: Request, payload: ReplayCleanupRequest) -> Dict[str, Any]:
    return await service(request).cleanup_replay_pack(payload)


@app.post("/api/cleanup")
async def cleanup_scope(request: Request, payload: CleanupRequest) -> Dict[str, Any]:
    return await service(request).cleanup_scope(payload)


@app.get("/api/jobs")
async def list_jobs(request: Request) -> Dict[str, Any]:
    return {"items": service(request).get_state()["jobs"]}


@app.get("/api/jobs/{job_id}")
async def get_job(request: Request, job_id: str) -> Dict[str, Any]:
    job = service(request).store.get_job(job_id)
    if job is None:
        return {"item": None}
    return {"item": job}


@app.get("/download/{file_name}")
async def download_file(file_name: str) -> FileResponse:
    target = (DOWNLOADS_DIR / file_name).resolve()
    if not str(target).startswith(str(DOWNLOADS_DIR.resolve())) or not target.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp.")
    return FileResponse(target)
