#!/usr/bin/env python3
"""Outbound runner cho bot "Listing 2 · ERP / Etsy".

Cùng mô hình với content_image_runner.py: runner tự gọi ra Automation Center,
Flow không bao giờ mở cổng vào từ Internet.

Khác một điểm quan trọng: runner này KHÔNG tự nói chuyện GraphQL với ERP.
Flow đã có sẵn toàn bộ phần ERP (đọc Task nguồn, upscale, đính ảnh, ghi
title/description) trong flow_web/service.py, và endpoint

    POST /api/jobs/{job_id}/artifacts/{index}/approval

được viết đúng để "record a local review decision and resume the ERP step".
Nên việc của runner chỉ là hai vòng:

  1. claim lệnh từ Center -> tạo job Flow với erp_enabled=True
  2. lấy quyết định duyệt từ Center -> chuyển tiếp vào Flow

Nhờ vậy credential ERP nằm nguyên trong Flow, runner không cần biết token ERP.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


CENTER_URL = os.environ.get("AUTOMATION_CENTER_URL", "https://automation.havigroup.llc").rstrip("/")
FLOW_URL = os.environ.get("FLOW_API_URL", "http://127.0.0.1:8000").rstrip("/")
RUNNER_KEY = os.environ.get("AUTOMATION_RUNNER_KEY", "listing2-erp-runner").strip()
RUNNER_SECRET = os.environ.get("AUTOMATION_RUNNER_SECRET", "").strip()
RUNNER_LABEL = os.environ.get("AUTOMATION_RUNNER_LABEL", "Listing 2 ERP Runner").strip()
POLL_SECONDS = max(1.0, float(os.environ.get("AUTOMATION_RUNNER_POLL_SECONDS", "2.5")))
ACCESS_CLIENT_ID = os.environ.get("CF_ACCESS_CLIENT_ID", "").strip()
ACCESS_CLIENT_SECRET = os.environ.get("CF_ACCESS_CLIENT_SECRET", "").strip()


RUNNER_VERSION = "1.0.0"
# Cloudflare WAF chặn User-Agent mặc định của urllib (lỗi 1010
# browser_signature_banned), nên runner phải tự định danh rõ ràng.
USER_AGENT = f"HaviGroupAutomationRunner/{RUNNER_VERSION} (+{RUNNER_KEY})"


def request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None, center: bool = False) -> dict[str, Any]:
    headers = {"accept": "application/json", "user-agent": USER_AGENT}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    if center:
        headers["x-automation-runner-secret"] = RUNNER_SECRET
        if ACCESS_CLIENT_ID and ACCESS_CLIENT_SECRET:
            headers["CF-Access-Client-Id"] = ACCESS_CLIENT_ID
            headers["CF-Access-Client-Secret"] = ACCESS_CLIENT_SECRET
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8", "replace")
            content_type = str(response.headers.get("content-type") or "")
            # Cloudflare Access trả 302 về trang đăng nhập; urllib đi theo redirect
            # nên ta nhận HTML 200 chứ không phải lỗi.
            if "json" not in content_type.lower():
                final_url = response.geturl()
                if "cloudflareaccess.com" in final_url or "/cdn-cgi/access/" in final_url:
                    raise RuntimeError(
                        "Cloudflare Access chặn runner: thiếu hoặc sai CF_ACCESS_CLIENT_ID/"
                        "CF_ACCESS_CLIENT_SECRET, hoặc Service Token chưa được gắn vào policy."
                    )
                raise RuntimeError(f"Phản hồi không phải JSON (content-type: {content_type or 'không rõ'}).")
            return json.loads(body or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:600]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Không kết nối được {url}: {exc.reason}") from exc


def center_request(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return request_json(f"{CENTER_URL}{path}", method=method, payload=payload, center=True)


def flow_request(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return request_json(f"{FLOW_URL}{path}", method=method, payload=payload)


def heartbeat() -> None:
    center_request("/api/runner/heartbeat", method="POST", payload={
        "runner_key": RUNNER_KEY,
        "label": RUNNER_LABEL,
        "version": RUNNER_VERSION,
    })


def update_run(run_id: str, status: str, **extra: Any) -> None:
    center_request(f"/api/runner/runs/{urllib.parse.quote(run_id)}", method="POST", payload={
        "runner_key": RUNNER_KEY,
        "status": status,
        **extra,
    })


def is_cancel_requested(run_id: str) -> bool:
    state = center_request(f"/api/runner/runs/{urllib.parse.quote(run_id)}?runner_key={urllib.parse.quote(RUNNER_KEY)}")
    return state.get("run", {}).get("status") == "cancel_requested"


def run_erp_image(run: dict[str, Any]) -> None:
    run_id = str(run["id"])
    payload = {
        "type": "image",
        "title": str(run.get("title") or "Ảnh Listing 2"),
        "prompt": str(run.get("prompt") or ""),
        "aspect": str(run.get("aspect") or "landscape"),
        "count": max(1, min(4, int(run.get("count") or 1))),
        "telegram_enabled": False,
        # Bật nhánh ERP của Flow.  Flow giữ credential ERP và tự giới hạn trong
        # PROJ-0049; runner không cầm token ERP.
        "erp_enabled": True,
        "flow_agent_enabled": True,
        # Bắt buộc False: yêu cầu nghiệp vụ là CHỈ ghi ảnh đã duyệt về Task nguồn.
        # Bật auto approve ở đây sẽ đẩy ảnh chưa ai xem vào ERP.
        "flow_agent_auto_approve": False,
    }
    # Để trống thì Flow tự chọn Task từ danh sách nguồn của PROJ-0049.
    erp_task_id = str(run.get("erp_task_id") or "").strip()
    if erp_task_id:
        payload["erp_source_task_id"] = erp_task_id

    flow_job = flow_request("/api/jobs", method="POST", payload=payload).get("job") or {}
    flow_job_id = str(flow_job.get("id") or "")
    if not flow_job_id:
        raise RuntimeError("Flow không trả về mã tác vụ tạo ảnh.")
    update_run(run_id, "running", runner_job_id=flow_job_id)

    while True:
        if is_cancel_requested(run_id):
            try:
                flow_request(f"/api/jobs/{urllib.parse.quote(flow_job_id)}/stop", method="POST", payload={})
            finally:
                update_run(run_id, "cancelled", runner_job_id=flow_job_id)
            return
        item = flow_request(f"/api/jobs/{urllib.parse.quote(flow_job_id)}").get("item") or {}
        status = str(item.get("status") or "")
        if status == "completed":
            artifacts = [
                {"label": artifact.get("label", "Ảnh"), "url": artifact.get("url", ""), "mime_type": artifact.get("mime_type", "")}
                for artifact in item.get("artifacts", [])
            ]
            update_run(run_id, "completed", runner_job_id=flow_job_id, result={
                "flow_job_id": flow_job_id,
                "erp_task_id": erp_task_id,
                "artifacts": artifacts,
            })
            return
        if status in {"failed", "cancelled"}:
            update_run(
                run_id,
                "cancelled" if status == "cancelled" else "failed",
                runner_job_id=flow_job_id,
                error=str(item.get("error") or "Flow không tạo được ảnh."),
            )
            return
        time.sleep(2)


def forward_approvals() -> int:
    """Chuyển quyết định duyệt từ Automation Center vào Flow.

    Flow là nơi thực sự ghi ảnh về Task ERP; nó chỉ chạy tiếp bước đó khi nhận
    được quyết định duyệt.  Trả về số quyết định đã xử lý trong vòng này.
    """
    response = center_request(f"/api/runner/approvals?runner_key={urllib.parse.quote(RUNNER_KEY)}")
    approvals = response.get("approvals") or []
    for approval in approvals:
        approval_id = str(approval.get("id") or "")
        flow_job_id = str(approval.get("runner_job_id") or "")
        decision = str(approval.get("status") or "").strip().lower()
        try:
            index = int(approval.get("artifact_index") or 0)
        except (TypeError, ValueError):
            index = -1
        if not approval_id:
            continue
        if not flow_job_id or index < 0 or decision not in {"approved", "rejected"}:
            # Không đoán: báo lỗi về Center và để nguyên pushed_at cho vòng sau.
            center_request(
                f"/api/runner/approvals/{urllib.parse.quote(approval_id)}/pushed",
                method="POST",
                payload={"runner_key": RUNNER_KEY, "error": "Thiếu flow job id, artifact index hoặc quyết định không hợp lệ."},
            )
            continue
        try:
            flow_request(
                f"/api/jobs/{urllib.parse.quote(flow_job_id)}/artifacts/{index}/approval",
                method="POST",
                payload={"status": decision, "reviewer": "Automation Center"},
            )
        except Exception as exc:  # noqa: BLE001 - lỗi được ghi lại rồi thử lại vòng sau
            center_request(
                f"/api/runner/approvals/{urllib.parse.quote(approval_id)}/pushed",
                method="POST",
                payload={"runner_key": RUNNER_KEY, "error": str(exc)[:600]},
            )
            continue
        center_request(
            f"/api/runner/approvals/{urllib.parse.quote(approval_id)}/pushed",
            method="POST",
            payload={"runner_key": RUNNER_KEY},
        )
    return len(approvals)


def main() -> int:
    if not RUNNER_SECRET:
        print("Thiếu AUTOMATION_RUNNER_SECRET; runner không khởi động.", file=sys.stderr)
        return 2
    if not RUNNER_KEY:
        print("Thiếu AUTOMATION_RUNNER_KEY; runner không khởi động.", file=sys.stderr)
        return 2
    print(f"{RUNNER_LABEL} đang poll {CENTER_URL} và dùng Flow tại {FLOW_URL}")
    while True:
        try:
            heartbeat()
            # Đẩy quyết định duyệt trước: ảnh đã duyệt xong không nên phải chờ
            # một lệnh tạo ảnh dài kết thúc mới được ghi về ERP.
            forward_approvals()
            response = center_request("/api/runner/claim", method="POST", payload={"runner_key": RUNNER_KEY})
            run = response.get("run")
            if run:
                run_erp_image(run)
            else:
                time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f"Runner lỗi: {exc}", file=sys.stderr)
            time.sleep(max(POLL_SECONDS, 5))


if __name__ == "__main__":
    raise SystemExit(main())
