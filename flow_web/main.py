from __future__ import annotations

import asyncio
import mimetypes
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .paths import DOWNLOADS_DIR, STATIC_DIR, UPLOADS_DIR, ensure_app_dirs
from .schemas import (
    ArtifactOpenRequest,
    CleanupRequest,
    ConfigUpdateRequest,
    CreateJobRequest,
    DownloadRequest,
    EtsyAccountDeleteRequest,
    EtsyAccountUpsertRequest,
    EtsyConfigUpdateRequest,
    EtsySectionSyncRequest,
    ExtensionAutoTrelloArchiveRequest,
    ExtensionAutoTrelloPlanRequest,
    FlowOperatorRequest,
    IntegrationConfigUpdateRequest,
    MasterBotRequest,
    PromptBatchRequest,
    PromptCreateRequest,
    ResetReadyTrelloRequest,
    ReplayCleanupRequest,
    StoryboardPlanRequest,
    TrelloConfigUpdateRequest,
    UserAssistantRequest,
)
from .service import FlowWebService
from .store import StateStore


ENV_FILE = Path(__file__).resolve().parent.parent / ".env.local"
_EXTENSION_SMOKE_REPORTS: list[Dict[str, Any]] = []


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


def _oauth_result_page(ok: bool, message: str) -> HTMLResponse:
    """Tiny page shown in the OAuth popup: notify the opener, then auto-close."""
    import html
    import json

    payload = json.dumps({"type": "etsy-oauth", "ok": bool(ok), "error": message or ""})
    title = "Đã kết nối Etsy" if ok else "Kết nối Etsy thất bại"
    detail = "Bạn có thể đóng cửa sổ này." if ok else html.escape(message or "Có lỗi xảy ra.")
    accent = "#1f8a4c" if ok else "#c0392b"
    body = f"""<!doctype html>
<html lang=\"vi\"><head><meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0;
         display: grid; place-items: center; min-height: 100vh; background: #0f1115; color: #e8eaed; }}
  .card {{ max-width: 420px; padding: 32px 28px; text-align: center; }}
  .dot {{ width: 14px; height: 14px; border-radius: 50%; background: {accent}; display: inline-block; margin-right: 8px; }}
  h1 {{ font-size: 20px; margin: 8px 0 12px; }}
  p {{ color: #aab1bb; line-height: 1.5; }}
</style></head>
<body><div class=\"card\">
  <h1><span class=\"dot\"></span>{html.escape(title)}</h1>
  <p>{detail}</p>
</div>
<script>
  (function () {{
    var result = {payload};
    var posted = false;
    try {{
      if (window.opener) {{
        window.opener.postMessage(result, "*");
        posted = true;
      }}
    }} catch (e) {{}}
    setTimeout(function () {{
      if (posted) {{
        try {{ window.close(); }} catch (e) {{}}
        return;
      }}
      if (result.ok) window.location.replace("/");
    }}, result.ok ? 800 : 4000);
  }})();
</script>
</body></html>"""
    return HTMLResponse(body, headers={"Cache-Control": "no-store"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_app_dirs()
    load_local_env()
    store = StateStore()
    app.state.flow_service = FlowWebService(store)
    sync_task = asyncio.create_task(app.state.flow_service.ensure_media_skill_library())
    telegram_approval_task = asyncio.create_task(app.state.flow_service.run_telegram_approval_sync_loop())
    try:
        yield
    finally:
        for task in (sync_task, telegram_approval_task):
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await app.state.flow_service.close()


app = FastAPI(
    title="Flow v2",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

mimetypes.add_type("application/x-chrome-extension", ".crx")
mimetypes.add_type("application/xml", ".xml")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/files/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/files/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")


def service(request: Request) -> FlowWebService:
    return request.app.state.flow_service


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(
        (STATIC_DIR / "index.html").read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store"},
    )


def _static_html(filename: str) -> HTMLResponse:
    return HTMLResponse(
        (STATIC_DIR / filename).read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/flow", response_class=HTMLResponse)
async def flow_tool() -> HTMLResponse:
    return _static_html("flow-tool.html")


@app.get("/etsy", response_class=HTMLResponse)
async def etsy_tool() -> HTMLResponse:
    return _static_html("etsy-tool.html")


@app.get("/amazon", response_class=HTMLResponse)
async def amazon_tool() -> HTMLResponse:
    return _static_html("amazon-tool.html")


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/extension/smoke-test-report")
async def extension_smoke_test_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    _EXTENSION_SMOKE_REPORTS.append(payload)
    del _EXTENSION_SMOKE_REPORTS[:-20]
    return {"ok": True, "count": len(_EXTENSION_SMOKE_REPORTS)}


@app.get("/api/extension/smoke-test-report/latest")
async def latest_extension_smoke_test_report() -> Dict[str, Any]:
    return {"ok": True, "report": _EXTENSION_SMOKE_REPORTS[-1] if _EXTENSION_SMOKE_REPORTS else None}


@app.get("/api/state")
async def get_state(request: Request) -> Dict[str, Any]:
    return service(request).get_state_payload()


@app.get("/api/etsy/status")
async def get_etsy_status(request: Request) -> Dict[str, Any]:
    flow_service = service(request)
    snapshot = flow_service.store.snapshot()
    return {"etsy": flow_service._etsy_config_snapshot(snapshot.etsy_config)}


@app.put("/api/config")
async def update_config(request: Request, payload: ConfigUpdateRequest) -> Dict[str, Any]:
    flow_service = service(request)
    config = await flow_service.update_config(payload)
    return {"config": config}


@app.put("/api/integrations/trello")
async def update_trello_config(request: Request, payload: TrelloConfigUpdateRequest) -> Dict[str, Any]:
    return {"trello": await service(request).update_trello_config(payload)}


@app.post("/api/trello/ready/reset")
async def reset_ready_trello_outputs(request: Request, payload: ResetReadyTrelloRequest) -> Dict[str, Any]:
    return await service(request).reset_ready_trello_outputs(payload)


@app.post("/api/trello/ready/status")
async def ready_trello_status(request: Request, payload: ResetReadyTrelloRequest) -> Dict[str, Any]:
    return await service(request).ready_trello_status(payload)


@app.get("/api/trello/board/lists")
async def list_trello_board_lists(request: Request, board: str = "") -> Dict[str, Any]:
    return await service(request).list_trello_board_lists(board)


@app.get("/api/trello/cards/{card_id}/attachments/{attachment_id}/preview")
async def trello_attachment_preview(request: Request, card_id: str, attachment_id: str) -> Response:
    payload = await service(request).trello_attachment_preview(card_id, attachment_id)
    return Response(
        content=payload["content"],
        media_type=payload["media_type"],
        headers={"Cache-Control": "private, max-age=300"},
    )


@app.put("/api/integrations/settings")
async def update_integration_config(request: Request, payload: IntegrationConfigUpdateRequest) -> Dict[str, Any]:
    return {"integrations": await service(request).update_integration_config(payload)}


@app.put("/api/integrations/etsy")
async def update_etsy_config(request: Request, payload: EtsyConfigUpdateRequest) -> Dict[str, Any]:
    return {"etsy": await service(request).update_etsy_config(payload)}


@app.get("/api/etsy/accounts")
async def list_etsy_accounts(request: Request) -> Dict[str, Any]:
    return {"etsy_accounts": service(request).etsy_accounts_snapshot()}


@app.post("/api/etsy/accounts")
async def upsert_etsy_account(request: Request, payload: EtsyAccountUpsertRequest) -> Dict[str, Any]:
    return {"etsy_accounts": await service(request).upsert_etsy_account(payload)}


@app.post("/api/etsy/accounts/delete")
async def delete_etsy_account(request: Request, payload: EtsyAccountDeleteRequest) -> Dict[str, Any]:
    return {"etsy_accounts": await service(request).delete_etsy_account(payload)}


@app.post("/api/etsy/preview")
async def preview_etsy_listing(request: Request, payload: CreateJobRequest) -> Dict[str, Any]:
    return {"etsy_preview": await service(request).preview_etsy_listing(payload)}


@app.post("/api/etsy/browser-copy/prepare")
async def prepare_etsy_browser_copy(request: Request, payload: CreateJobRequest) -> Dict[str, Any]:
    job_id = (payload.source_job_id or "preview").strip() or "preview"
    return {"etsy_browser_copy": await service(request).prepare_etsy_browser_copy(job_id, payload)}


@app.post("/api/etsy/browser-copy/enqueue")
async def enqueue_etsy_browser_copy(request: Request, payload: CreateJobRequest) -> Dict[str, Any]:
    job_id = (payload.source_job_id or "manual").strip() or "manual"
    return {"etsy_browser_copy": await service(request).enqueue_etsy_browser_copy(job_id, payload)}


@app.post("/api/jobs/{job_id}/etsy-browser-copy/enqueue")
async def enqueue_job_etsy_browser_copy(request: Request, job_id: str) -> Dict[str, Any]:
    return {"etsy_browser_copy": await service(request).enqueue_etsy_browser_copy_from_job(job_id)}


@app.get("/api/etsy/browser-copy/queue")
async def etsy_browser_copy_queue(request: Request) -> Dict[str, Any]:
    return service(request).etsy_browser_copy_queue_snapshot()


@app.post("/api/amazon/browser-copy/prepare")
async def prepare_amazon_browser_copy(request: Request, payload: CreateJobRequest) -> Dict[str, Any]:
    job_id = (payload.source_job_id or "preview").strip() or "preview"
    return {"amazon_browser_copy": await service(request).prepare_amazon_browser_copy(job_id, payload)}


@app.post("/api/amazon/browser-copy/enqueue")
async def enqueue_amazon_browser_copy(request: Request, payload: CreateJobRequest) -> Dict[str, Any]:
    job_id = (payload.source_job_id or "manual").strip() or "manual"
    return {"amazon_browser_copy": await service(request).enqueue_amazon_browser_copy(job_id, payload)}


@app.post("/api/jobs/{job_id}/amazon-browser-copy/enqueue")
async def enqueue_job_amazon_browser_copy(request: Request, job_id: str) -> Dict[str, Any]:
    return {"amazon_browser_copy": await service(request).enqueue_amazon_browser_copy_from_job(job_id)}


@app.get("/api/amazon/browser-copy/queue")
async def amazon_browser_copy_queue(request: Request) -> Dict[str, Any]:
    return service(request).amazon_browser_copy_queue_snapshot()


@app.post("/api/extension/amazon-browser-copy/next")
async def next_extension_amazon_browser_copy(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await service(request).next_amazon_browser_copy_task(payload)


@app.post("/api/extension/amazon-browser-copy/smoke/enqueue")
async def enqueue_extension_amazon_browser_copy_smoke(request: Request) -> Dict[str, Any]:
    account_id = ""
    try:
        body = await request.json()
        if isinstance(body, dict):
            account_id = str(body.get("accountId") or body.get("account_id") or "")
    except Exception:
        account_id = ""
    return await service(request).enqueue_amazon_browser_copy_smoke(account_id)


@app.post("/api/extension/amazon-browser-copy/report")
async def report_extension_amazon_browser_copy(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await service(request).report_amazon_browser_copy_task(payload)


@app.post("/api/etsy/sections/sync")
async def sync_etsy_sections_from_trello(request: Request, payload: EtsySectionSyncRequest) -> Dict[str, Any]:
    return {"etsy_sections": await service(request).sync_etsy_sections_from_trello(payload)}


@app.post("/api/extension/etsy-browser-copy/next")
async def next_extension_etsy_browser_copy(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await service(request).next_etsy_browser_copy_task(payload)


@app.post("/api/extension/etsy-browser-copy/smoke/enqueue")
async def enqueue_extension_etsy_browser_copy_smoke(request: Request) -> Dict[str, Any]:
    # Optional JSON body {"accountId": "..."} routes the smoke task to a specific
    # fleet account; an empty/absent body keeps the legacy default-account behavior.
    account_id = ""
    try:
        body = await request.json()
        if isinstance(body, dict):
            account_id = str(body.get("accountId") or body.get("account_id") or "")
    except Exception:
        account_id = ""
    return await service(request).enqueue_etsy_browser_copy_smoke(account_id)


@app.post("/api/extension/etsy-browser-copy/report")
async def report_extension_etsy_browser_copy(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await service(request).report_etsy_browser_copy_task(payload)


@app.post("/api/etsy/oauth/start")
async def start_etsy_oauth(request: Request) -> Dict[str, Any]:
    redirect_uri = f"{str(request.base_url).rstrip('/')}/api/etsy/oauth/callback"
    try:
        return service(request).start_etsy_oauth(redirect_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/etsy/oauth/open")
async def open_etsy_oauth(request: Request) -> RedirectResponse:
    redirect_uri = f"{str(request.base_url).rstrip('/')}/api/etsy/oauth/callback"
    try:
        result = service(request).start_etsy_oauth(redirect_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(str(result["authorize_url"]))


@app.get("/api/etsy/oauth/callback", response_class=HTMLResponse)
async def etsy_oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    error_description: str = "",
) -> HTMLResponse:
    if error:
        return _oauth_result_page(False, error_description or error)
    try:
        await service(request).complete_etsy_oauth(code, state)
    except Exception as exc:  # noqa: BLE001 - surface a friendly page, never a stack trace
        return _oauth_result_page(False, str(exc))
    return _oauth_result_page(True, "")


@app.post("/api/telegram/approvals/sync")
async def sync_telegram_approvals(request: Request) -> Dict[str, Any]:
    return {"telegram_approvals": await service(request).sync_telegram_approvals()}


@app.post("/api/prompt-sources/preview")
async def preview_prompt_source(
    request: Request,
    source_url: str = Form(""),
    text: str = Form(""),
    file: UploadFile | None = File(None),
) -> Dict[str, Any]:
    return await service(request).preview_prompt_source(file=file, text=text, source_url=source_url)


@app.post("/api/auth/login")
async def login(request: Request) -> Dict[str, Any]:
    flow_service = service(request)
    job = await flow_service.enqueue_login()
    return {"job": job}


@app.post("/api/auth/logout")
async def logout(request: Request) -> Dict[str, Any]:
    return await service(request).logout_flow()


@app.post("/api/flow/open-login")
async def open_login_surface(request: Request) -> Dict[str, Any]:
    return await service(request).open_flow_login_surface()


@app.post("/api/flow/open-project")
async def open_project_surface(request: Request) -> Dict[str, Any]:
    return await service(request).open_flow_project_surface()


@app.get("/api/credits")
async def credits(request: Request) -> Dict[str, Any]:
    return await service(request).get_credits()


@app.get("/api/workflows")
async def workflows(request: Request) -> Dict[str, Any]:
    return {"items": await service(request).get_workflows()}


@app.get("/api/flow/project-debug")
async def flow_project_debug(request: Request) -> Dict[str, Any]:
    return await service(request).get_project_debug()


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


@app.post("/api/jobs/batch")
async def create_prompt_batch(request: Request, payload: PromptBatchRequest) -> Dict[str, Any]:
    job = await service(request).enqueue_prompt_batch(payload)
    return {"job": job}


@app.post("/api/jobs/auto-trello-one-click")
async def create_auto_trello_one_click(request: Request, payload: PromptBatchRequest) -> Dict[str, Any]:
    return await service(request).enqueue_auto_trello_one_click(payload)


@app.post("/api/extension/auto-trello/plan")
async def plan_extension_auto_trello(request: Request, payload: ExtensionAutoTrelloPlanRequest) -> Dict[str, Any]:
    return await service(request).plan_extension_auto_trello(payload)


@app.post("/api/extension/auto-trello/archive")
async def archive_extension_auto_trello(request: Request, payload: ExtensionAutoTrelloArchiveRequest) -> Dict[str, Any]:
    return await service(request).archive_extension_auto_trello(payload)


@app.post("/api/jobs/{job_id}/stop")
async def stop_job(request: Request, job_id: str) -> Dict[str, Any]:
    job = await service(request).request_stop_prompt_batch(job_id)
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


@app.post("/api/assistant/help")
async def assistant_help(request: Request, payload: UserAssistantRequest) -> Dict[str, Any]:
    return await service(request).answer_user_assistant(payload)


@app.post("/api/flow-ai/plan")
async def plan_flow_ai_operator(request: Request, payload: FlowOperatorRequest) -> Dict[str, Any]:
    return await service(request).plan_flow_operator(payload)


@app.get("/api/extensions")
async def list_extensions(request: Request) -> Dict[str, Any]:
    return service(request).extension_registry()


@app.get("/api/extension/download")
async def download_extension(request: Request) -> Response:
    archive = service(request).build_extension_archive(str(request.base_url).rstrip("/"))
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="flow-v2-extension.zip"'},
    )


@app.post("/api/master-bot/plan")
async def plan_master_bot(request: Request, payload: MasterBotRequest) -> Dict[str, Any]:
    return await service(request).plan_master_bot(payload)


@app.post("/api/master-bot/preflight")
async def preflight_master_bot(request: Request, payload: MasterBotRequest) -> Dict[str, Any]:
    return service(request).master_bot_preflight(payload)


@app.post("/api/storyboard/plan")
async def plan_storyboard(request: Request, payload: StoryboardPlanRequest) -> Dict[str, Any]:
    return await service(request).plan_storyboard(payload)


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
