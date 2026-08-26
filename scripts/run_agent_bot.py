#!/usr/bin/env python3
"""Chạy agent bot đứng riêng, không cần mở giao diện Flow v2.

Bình thường bot chạy sẵn bên trong app (``flow_web/main.py`` khởi động nó
trong lifespan). Script này dành cho hai việc mà app không làm được:

* **Kiểm tra nhanh** một lượt quét rồi thoát — ``--once``, và nên đi kèm
  ``--dry-run`` ở lần đầu cắm bot vào một dự án lạ.
* **Chạy bot ở một máy khác** với máy chạy Flow. Lúc đó phần dọn phiếu
  (👍 giữ / 👎 xoá) chỉ cần token ERP nên chạy được ngay, còn phần tạo ảnh
  được chuyển tiếp qua HTTP tới máy có Flow (``--flow-web-url``).

Thẻ ``action_1: listing`` đi sang bản Listing qua ``ERP_LISTING_API_URL`` trong
``.env.local``; chưa đặt biến đó thì bot nhận diện rồi để yên, không chạy gì.

Ví dụ::

    python scripts/run_agent_bot.py --once --dry-run
    python scripts/run_agent_bot.py --flow-web-url http://127.0.0.1:3170
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flow_web.agent_bot import AgentBotConfig, AgentBotError, build_agent_bot  # noqa: E402
from flow_web.listing_bridge import (  # noqa: E402
    ListingBridge,
    ListingBridgeConfig,
    build_listing_hook,
)
from flow_web.main import load_local_env  # noqa: E402

log = logging.getLogger("agent_bot")


def _forward_autorun(flow_web_url: str, timeout_s: int = 30):
    """Hook chạy việc: đẩy thẻ cha sang cho Flow v2 tạo ảnh.

    Bot cố ý không tự chạy Flow: cả app chỉ có một phiên trình duyệt, nên việc
    xếp hàng phải nằm ở đúng một chỗ — ``enqueue_erp_idea_jobs`` của app.
    """

    base = flow_web_url.rstrip("/")

    async def hook(parent_task_id: str) -> Dict[str, Any]:
        def call() -> Dict[str, Any]:
            request = Request(
                f"{base}/api/erp/idea-batch",
                data=json.dumps({"task_id": parent_task_id}).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            try:
                with urlopen(request, timeout=timeout_s) as response:
                    return json.loads(response.read().decode("utf-8") or "{}")
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise AgentBotError(f"Flow v2 từ chối chạy {parent_task_id}: HTTP {exc.code} {detail}") from exc
            except URLError as exc:
                raise AgentBotError(
                    f"Không gọi được Flow v2 tại {base} để chạy {parent_task_id}: {exc.reason}"
                ) from exc

        return await asyncio.to_thread(call)

    return hook


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent bot của Flow v2 trên ERP HaviGroup.")
    parser.add_argument("--once", action="store_true", help="Quét đúng một lượt rồi thoát.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ghi log quyết định nhưng không xoá và không chạy gì.",
    )
    parser.add_argument(
        "--flow-web-url",
        default="",
        help="Địa chỉ Flow v2 để chuyển tiếp việc tạo ảnh. Bỏ trống là chỉ dọn phiếu.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=0,
        help="Ghi đè ERP_AGENT_POLL_SECONDS.",
    )
    parser.add_argument("--verbose", action="store_true", help="Log mức DEBUG.")
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    load_local_env()

    config = AgentBotConfig.from_env()
    if args.dry_run:
        config = replace(config, dry_run=True)
    if args.poll_seconds:
        config = replace(config, poll_seconds=args.poll_seconds)
    if not args.flow_web_url:
        # Không có nơi chuyển tiếp thì tắt hẳn phần chạy việc, thay vì để nó
        # âm thầm không làm gì và trông như bot đang hỏng.
        config = replace(config, autorun=False)

    if not config.enabled:
        log.error("Chưa đặt ERP_AGENT_TOKEN trong .env.local nên không có gì để chạy.")
        return 2

    # Một agent, hai loại thẻ — giống hệt lúc bot chạy trong app (xem
    # ``FlowService.agent_bot``). Quên nối cầu Listing ở đây thì bot vẫn sống và
    # vẫn dọn phiếu, chỉ mỗi thẻ ``action_1: listing`` là nhận "chưa cấu hình
    # ERP_LISTING_API_URL" — kể cả khi biến ấy đã có trong ``.env.local``.
    # ``build_listing_hook`` trả None khi chưa đặt biến, nên máy chưa dựng bản
    # Listing vẫn giữ nguyên hành vi cũ.
    listing = ListingBridge(ListingBridgeConfig.from_env())
    bot = build_agent_bot(
        config,
        autorun_hook=_forward_autorun(args.flow_web_url) if args.flow_web_url else None,
        listing_hook=build_listing_hook(listing),
    )
    if bot is None:
        log.error("Không dựng được agent bot.")
        return 2

    if args.once:
        summary = await bot.run_once()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    log.info(
        "Agent bot chạy mỗi %ss (dọn phiếu%s). Ctrl+C để dừng.",
        config.poll_seconds,
        " + chạy việc" if config.autorun else "",
    )
    await bot.run_forever(immediate=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(130)
