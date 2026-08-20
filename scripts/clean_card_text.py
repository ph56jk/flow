#!/usr/bin/env python3
"""Dọn chữ của bot trên thẻ ERP, chỉ để lại ảnh.

Thẻ là chỗ người ta xem ảnh. Mỗi tấm ảnh app đăng lên từng kèm một dòng dấu và
một dòng hướng dẫn, nên thẻ mười hai ảnh có hai mươi bốn dòng chữ lặp lại chen
giữa. Từ nay app không viết chữ nào nữa; script này xử nốt những thẻ đã trót
mang chữ.

Hai loại chữ, hai cách xử lý khác hẳn nhau:

* **Bình luận có ảnh** (``[FLOW_V2_REVIEW ...]``, ``[FLOW_V2_ARTIFACT] ...``):
  chỉ làm trống phần chữ, và **chuyển đúng cái dấu ấy sang trường ``meta``**
  trong cùng một lệnh ghi. Dấu là thứ app dựa vào để biết thẻ đã chạy rồi; mất
  dấu là thẻ bị chạy lại và chồng thêm một bộ ảnh nữa. Ảnh đính kèm không đụng
  tới.
* **Bình luận chỉ có chữ** (``[FLOW_V2_ERROR]``, ``[FLOW_V2_REVIEW_RESULT]``,
  ``[AGENT_BOT]``): làm trống thì còn lại một bong bóng rỗng, nên chúng phải bị
  xoá hẳn. Xoá không hoàn tác được, nên mặc định script chỉ đếm và in ra; muốn
  xoá thật thì phải nói rõ bằng ``--delete-notes``.

    python scripts/clean_card_text.py TASK-2026-00202             # chạy khô
    python scripts/clean_card_text.py TASK-2026-00202 --apply
    python scripts/clean_card_text.py TASK-2026-00202 --apply --delete-notes
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flow_web.main import load_local_env

REVIEW_TAG = re.compile(r"\[FLOW_V2_REVIEW\s+[^\]#\s]+#\d+\]")
ARTIFACT_TAG = re.compile(r"\[FLOW_V2_ARTIFACT\][^\n\r]*")
NOTE_TAGS = ("[FLOW_V2_ERROR]", "[FLOW_V2_REVIEW_RESULT]", "[AGENT_BOT]")


def _task_ids(service: Any, key: str, token: str, roots: List[str]) -> List[str]:
    """Mỗi thẻ được nêu tên, cộng thêm thẻ con của nó."""
    seen: List[str] = []
    for raw in roots:
        task_id = service._normalize_erp_task_id(str(raw))
        if not task_id or task_id in seen:
            continue
        seen.append(task_id)
        detail = service._erp_task_detail(key, token, task_id)
        for row in detail.get("children") or []:
            child = service._normalize_erp_task_id(str((row or {}).get("name") or ""))
            if child and child not in seen:
                seen.append(child)
    return seen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="+", help="Mã thẻ, ví dụ TASK-2026-00202 (kèm cả thẻ con)")
    parser.add_argument("--apply", action="store_true", help="Ghi thật, mặc định chỉ in ra")
    parser.add_argument(
        "--delete-notes",
        action="store_true",
        help="Xoá hẳn bình luận chỉ có chữ (không hoàn tác được)",
    )
    args = parser.parse_args()

    load_local_env()
    with patch("flow_web.store.ensure_app_dirs", lambda: None), patch(
        "flow_web.service.ensure_app_dirs", lambda: None
    ):
        from flow_web.service import FlowWebService
        from flow_web.store import StateStore

        service = FlowWebService(StateStore())
        key, token = service._erp_credentials()
        if not key or not token:
            print("Chưa có ERP API key/secret trong .env.local.")
            return 1

        stripped = notes = 0
        for task_id in _task_ids(service, key, token, args.tasks):
            detail = service._erp_task_detail(key, token, task_id)
            comments = [item for item in detail.get("comments") or [] if isinstance(item, dict)]
            actions: List[Dict[str, Any]] = []
            for comment in comments:
                text = service._erp_plain_text(comment.get("content"))
                if not text or text == service.ERP_SILENT_COMMENT_BODY:
                    continue
                match = REVIEW_TAG.search(text) or ARTIFACT_TAG.search(text)
                if match:
                    actions.append(
                        {
                            "kind": "strip",
                            "comment": str(comment.get("name") or ""),
                            "meta": str(comment.get("meta") or "").strip() or match.group(0).strip(),
                            "was": text[:60],
                        }
                    )
                    continue
                if any(tag in text for tag in NOTE_TAGS):
                    actions.append(
                        {"kind": "note", "comment": str(comment.get("name") or ""), "was": text[:60]}
                    )
            if not actions:
                continue
            print(f"\n{task_id} — {detail.get('subject')!r}")
            for action in actions:
                if action["kind"] == "strip":
                    stripped += 1
                    print(f"  bỏ chữ: {action['was']}…  → meta {action['meta']}")
                    if args.apply:
                        service._erp_graphql(
                            "mutation UpdateTaskComment($name: String!, $comment: String!, "
                            "$content: String!, $meta: String) "
                            "{ updateTaskComment(name: $name, comment: $comment, content: $content, meta: $meta) }",
                            {
                                "name": task_id,
                                "comment": action["comment"],
                                # Dấu và chữ đi cùng một lệnh: không có khoảnh
                                # khắc nào thẻ mất dấu mà app lại vừa quét qua.
                                "content": service.ERP_SILENT_COMMENT_BODY,
                                "meta": action["meta"],
                            },
                            "UpdateTaskComment",
                            key=key,
                            token=token,
                        )
                    continue
                notes += 1
                print(f"  {'xoá' if args.delete_notes else 'ghi chú thừa'}: {action['was']}…")
                if args.apply and args.delete_notes:
                    service._erp_delete_task_comment(key, token, task_id, action["comment"])

        done = "Đã" if args.apply else "Sẽ"
        print(f"\n{done} bỏ chữ trên {stripped} bình luận ảnh.")
        if notes:
            if args.delete_notes:
                print(f"{done} xoá {notes} bình luận chỉ có chữ.")
            else:
                print(f"Còn {notes} bình luận chỉ có chữ — thêm --delete-notes mới xoá.")
        if not args.apply and (stripped or notes):
            print("Chạy lại với --apply để ghi thật.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
