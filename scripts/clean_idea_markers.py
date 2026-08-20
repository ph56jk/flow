#!/usr/bin/env python3
"""Xoá dòng ``[FLOW_V2_IDEA src=...]`` bot từng viết lên thẻ con.

Thẻ là chỗ người ta đọc, không phải sổ tay của bot. Dòng ấy từng là cách bot
nhớ ảnh nào đã có thẻ; nay chỗ giữ chỗ là chính tấm ảnh - ảnh bìa và tệp đính
kèm của thẻ con vẫn trỏ về đúng đường dẫn ảnh gốc trên thẻ cha.

Vì thế script chỉ xoá chữ khi tấm ảnh **vẫn còn giữ chỗ được**: mất cả hai thì
lượt quét sau sẽ tạo lại một thẻ đã có. Bình luận không bị xoá - chỉ nội dung
chữ bị làm trống, tệp đính kèm ở nguyên đó.

    python scripts/clean_idea_markers.py TASK-2026-00254        # chạy khô
    python scripts/clean_idea_markers.py TASK-2026-00254 --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flow_web.main import load_local_env


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="+", help="Mã thẻ cha, ví dụ TASK-2026-00254")
    parser.add_argument("--apply", action="store_true", help="Ghi thật, mặc định chỉ in ra")
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

        cleaned = held = 0
        for parent_id in args.tasks:
            parent = service._erp_task_detail(key, token, parent_id)
            print(f"\n{parent_id} — {parent.get('subject')!r}")
            for row in parent.get("children") or []:
                child_id = service._normalize_erp_task_id(str(row.get("name") or ""))
                if not child_id:
                    continue
                child = service._erp_task_detail(key, token, child_id)
                marked = [
                    comment
                    for comment in child.get("comments") or []
                    if isinstance(comment, dict)
                    and service.ERP_IDEA_INTAKE_MARKER.search(
                        service._erp_plain_text(comment.get("content"))
                    )
                ]
                if not marked:
                    continue
                # Bỏ hết chữ đi thì tấm ảnh có còn giữ được chỗ không?
                stripped = dict(child)
                stripped["comments"] = [
                    dict(comment, content="") if comment in marked else comment
                    for comment in child.get("comments") or []
                ]
                still = service._erp_idea_intake_claims([stripped])
                wanted = set()
                for comment in marked:
                    for match in service.ERP_IDEA_INTAKE_MARKER.finditer(
                        service._erp_plain_text(comment.get("content"))
                    ):
                        wanted |= service._erp_idea_claim_variants(match.group(1).strip())
                if not (wanted & still):
                    held += 1
                    print(f"  {child_id}: GIỮ LẠI — bỏ chữ là mất chỗ, thẻ sẽ bị tạo lại")
                    continue
                cleaned += 1
                print(f"  {child_id}: xoá chữ trên {len(marked)} bình luận")
                if not args.apply:
                    continue
                for comment in marked:
                    service._erp_graphql(
                        "mutation UpdateTaskComment($name: String!, $comment: String!, $content: String!) "
                        "{ updateTaskComment(name: $name, comment: $comment, content: $content) }",
                        {"name": child_id, "comment": str(comment.get("name") or ""), "content": ""},
                        "UpdateTaskComment",
                        key=key,
                        token=token,
                    )

        print(f"\n{'Đã xoá' if args.apply else 'Sẽ xoá'} chữ trên {cleaned} thẻ; giữ lại {held} thẻ.")
        if not args.apply and cleaned:
            print("Chạy lại với --apply để ghi thật.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
