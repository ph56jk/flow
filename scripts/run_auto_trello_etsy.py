#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict


DEFAULT_BACKEND = "http://127.0.0.1:8000"
DEFAULT_PROMPT = "Flow Agent tự phân tích ảnh nguồn Trello, viết prompt và tạo bộ ảnh sản phẩm."
DEFAULT_TRELLO_BOARD_ID = "gpy5eAiG"
DEFAULT_TRELLO_READY_FOR_AI_LIST_ID = "69e2ff2a90718d242df060b7"
DEFAULT_TRELLO_IDEAS_LIST_NAME = "Ideas"


def resolve_source_list(args: argparse.Namespace, trello: Dict[str, Any]) -> tuple[str, str]:
    if args.trello_list:
        return str(args.trello_list).strip(), str(args.trello_list).strip()
    if args.source == "idea":
        return DEFAULT_TRELLO_IDEAS_LIST_NAME, "Idea"
    configured = str(trello.get("list_id") or "").strip()
    return configured or DEFAULT_TRELLO_READY_FOR_AI_LIST_ID, "Ready for AI"


def automation_graph(include_etsy: bool, image_count: int) -> Dict[str, Any]:
    modules = [
        {"id": "master-bot", "type": "master_bot", "title": "Master Bot", "enabled": True},
        {"id": "trello-source", "type": "trello_source", "title": "Trello Image Source", "enabled": True},
        {"id": "flow", "type": "flow", "title": "Google Flow", "enabled": True, "settings": {"imageCount": image_count}},
        {"id": "trello-archive", "type": "trello", "title": "Trello Archive", "enabled": True},
    ]
    edges = [
        {"source": "master-bot", "target": "trello-source", "condition": "success"},
        {"source": "trello-source", "target": "flow", "condition": "success"},
        {"source": "flow", "target": "trello-archive", "condition": "success"},
    ]
    if include_etsy:
        modules.append(
            {
                "id": "etsy-copy",
                "type": "etsy_browser_copy",
                "title": "Etsy Copy Listing",
                "enabled": True,
                "settings": {"keepColorChart": True, "deleteExistingImages": True},
            }
        )
        edges.append({"source": "trello-archive", "target": "etsy-copy", "condition": "success"})
    return {"version": 1, "selected_module_id": "flow", "modules": modules, "edges": edges}


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: Dict[str, Any] | None = None,
    timeout_s: int = 30,
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Accept": "application/json", **({} if data is None else {"Content-Type": "application/json"})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"{method} {url} timed out after {timeout_s}s") from exc
    return json.loads(body or "{}")


def build_payload(args: argparse.Namespace, state: Dict[str, Any]) -> Dict[str, Any]:
    trello = ((state.get("payload") or {}).get("trello") or {})
    image_count = max(1, min(int(args.count), 4))
    product = str(args.product or "").strip()
    trello_board_id = str(args.trello_board or trello.get("board_id") or DEFAULT_TRELLO_BOARD_ID).strip()
    trello_list_id, source_label = resolve_source_list(args, trello)
    trello_card_id = str(args.trello_card or trello.get("card_id") or "").strip()
    if trello_card_id.upper() in {"LINK_CARD_TRELLO", "TRELLO_CARD", "CARD_LINK", "LINK"}:
        raise RuntimeError("Bạn đang dùng placeholder LINK_CARD_TRELLO. Hãy thay bằng link card Trello thật.")
    items = []
    if trello_card_id:
        items.append(
            {
                "row": 1,
                "active": True,
                "prompt": args.prompt or DEFAULT_PROMPT,
                "product": product,
                "product_key": product,
                "product_name": product,
                "notes": f"Terminal one-shot Trello card: {trello_card_id}",
                "trello_card_id": trello_card_id,
                "trello_source_card_id": trello_card_id,
                "trello_list_id": trello_list_id,
            }
        )
    return {
        "title": "Auto Trello Flow",
        "limit": max(1, int(args.limit)),
        "auto_trello": True,
        "continuous": bool(args.continuous),
        "run_until_empty": bool(args.continuous),
        "poll_interval_s": max(5, int(args.poll_interval)),
        "items": items,
        "job": {
            "type": "image",
            "title": "Auto AI Trello",
            "prompt": args.prompt or DEFAULT_PROMPT,
            "count": image_count,
            "aspect": args.aspect,
            "trello_enabled": True,
            "etsy_enabled": not args.no_etsy,
            "flow_agent_enabled": True,
            "flow_agent_auto_approve": True,
            "trello_board_id": trello_board_id,
            "trello_list_id": trello_list_id,
            "trello_card_id": trello_card_id,
            "trello_source_card_id": trello_card_id,
            "prompt_product": product,
            "prompt_product_key": product,
            "prompt_notes": f"Trello search trong {source_label}: {product}" if product else source_label,
            "automation_graph": automation_graph(not args.no_etsy, image_count),
            "etsy_publish": False,
            "etsy_browser_copy_enabled": not args.no_etsy,
            "etsy_keep_color_chart": True,
            "etsy_delete_existing_images": True,
        },
    }


def print_job(job: Dict[str, Any]) -> None:
    print(f"job_id={job.get('id', '')}")
    print(f"status={job.get('status', '')}")
    print(f"title={job.get('title', '')}")


def wait_for_job(base_url: str, job_id: str, timeout_s: int, poll_s: int) -> int:
    deadline = time.time() + timeout_s
    last_line = ""
    poll_errors = 0
    while time.time() < deadline:
        try:
            item = request_json(base_url, f"/api/jobs/{job_id}", timeout_s=45).get("item") or {}
            poll_errors = 0
        except RuntimeError as exc:
            poll_errors += 1
            line = f"[job] polling retry {poll_errors}/5 | {exc}"
            if line != last_line:
                print(line, flush=True)
                last_line = line
            if poll_errors >= 5:
                print(f"ERROR: could not read job status after {poll_errors} attempts", file=sys.stderr)
                return 4
            time.sleep(poll_s)
            continue
        status = str(item.get("status") or "")
        error = str(item.get("error") or "")
        logs = item.get("logs") or []
        latest_log = ""
        if logs:
            latest = logs[-1] or {}
            latest_log = str(latest.get("message") or "")
        line = f"[job] {status}" + (f" | {latest_log}" if latest_log else "")
        if line != last_line:
            print(line, flush=True)
            last_line = line
        if status in {"completed", "failed", "cancelled", "stopped"}:
            if error:
                print(f"error={error}", flush=True)
            return 0 if status == "completed" else 2
        time.sleep(poll_s)
    print(f"Timed out waiting for job {job_id}", file=sys.stderr)
    return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full Auto Trello -> Flow -> Trello -> Etsy draft pipeline.")
    parser.add_argument("--backend", default=DEFAULT_BACKEND, help="Flow backend URL.")
    parser.add_argument("--limit", type=int, default=1, help="Number of Trello products to run.")
    parser.add_argument("--count", type=int, default=4, help="Number of Flow images per product, max 4.")
    parser.add_argument("--aspect", default="square", choices=["square", "landscape", "portrait"], help="Image aspect ratio.")
    parser.add_argument("--product", default="", help="Optional Trello/product search text.")
    parser.add_argument("--source", default="ready", choices=["ready", "idea"], help="Trello source list shortcut.")
    parser.add_argument("--trello-board", default="", help="Trello board ID or URL. Falls back to saved backend config.")
    parser.add_argument("--trello-list", default="", help="Trello list ID or name. Overrides --source.")
    parser.add_argument("--trello-card", default="", help="Specific Trello card ID/short link/URL to run.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Flow Agent instruction.")
    parser.add_argument("--continuous", action="store_true", help="Keep polling Trello instead of one batch.")
    parser.add_argument("--poll-interval", type=int, default=30, help="Continuous mode poll interval seconds.")
    parser.add_argument("--no-etsy", action="store_true", help="Run Flow/Trello only, do not enqueue Etsy draft copy.")
    parser.add_argument("--wait", action="store_true", help="Wait until the batch job reaches a terminal status.")
    parser.add_argument("--timeout", type=int, default=3600, help="Wait timeout seconds.")
    args = parser.parse_args()

    try:
        state = request_json(args.backend, "/api/state")
        payload = build_payload(args, state)
        result = request_json(args.backend, "/api/jobs/auto-trello-one-click", method="POST", payload=payload)
        job = result.get("job") or {}
        if result.get("message"):
            print(f"message={result.get('message')}")
        if result.get("mode"):
            print(f"mode={result.get('mode')}")
        for task in result.get("tasks") or []:
            print(
                "etsy_task="
                + json.dumps(
                    {
                        "card": task.get("card_name") or task.get("card_id"),
                        "enqueued": task.get("enqueued"),
                        "missing": task.get("missing") or [],
                        "task_id": ((task.get("queue_task") or {}).get("id") if isinstance(task.get("queue_task"), dict) else ""),
                    },
                    ensure_ascii=False,
                )
            )
        print_job(job)
        if result.get("mode") == "etsy_from_existing_outputs":
            return 0 if result.get("ok") else 2
        if args.wait and job.get("id"):
            return wait_for_job(args.backend, str(job["id"]), args.timeout, 5)
        return 0
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(
            "Hint: pass a specific card or product, for example:\n"
            "  cd /Users/admin/VibeCoding/flow && .venv/bin/python scripts/run_auto_trello_etsy.py --trello-card 'https://trello.com/c/XXXX' --wait\n"
            "  cd /Users/admin/VibeCoding/flow && .venv/bin/python scripts/run_auto_trello_etsy.py --source idea --product 'baby album' --wait",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
