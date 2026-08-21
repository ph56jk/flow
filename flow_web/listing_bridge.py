"""Giao thẻ listing sang bản Listing để đăng ảnh đã duyệt lên Etsy.

Một agent, hai loại việc. Thẻ nào viết ``action_1: listing`` trong khối
*Thuộc tính* là việc lên Etsy, và phần đuôi của việc đó — chép ảnh sang máy
Etsy rồi để extension dựng bản nháp trong shop — nằm ở bản Listing, không nằm
ở đây. Module này là chỗ duy nhất hai bên chạm nhau.

Vì sao là "đăng" chứ không phải "làm lại từ đầu": nửa làm ảnh đã tạo ảnh trên
đúng thẻ ERP đó và đã có người bấm 👍 duyệt. Bảo bản Listing chạy
``/api/jobs`` là bắt nó mở Google Flow tạo một bộ ảnh khác — tốn quota, và
người duyệt sẽ phải duyệt lại một bộ ảnh mà họ chưa từng thấy. Nên bridge gọi
``/api/etsy/browser-copy/enqueue``: đầu kia đọc chính thẻ ấy, tải ảnh đính kèm
đã duyệt, chép sang máy ảo và xếp hàng cho extension. Không có lượt tạo ảnh
thứ hai, và cũng không có tiến trình thứ hai tranh Chrome trên cùng cái máy.

Hệ quả về quyền: bản Listing chỉ *đọc* thẻ, ở đúng dự án mà thẻ đang nằm
(``ERP_LISTING_PROJECT``, mặc định trùng dự án của nửa làm ảnh). Nó không cần
thêm quyền ghi nào ngoài những gì nó vốn có.

``ERP_LISTING_API_URL`` để trống là tắt: bot vẫn nhận ra thẻ listing và vẫn
không đụng vào nó, chỉ là không giao đi đâu cả. Đó là trạng thái đúng cho một
máy chưa dựng bản Listing.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .erp_meta import resolve_routing, task_meta

log = logging.getLogger(__name__)


# Thẻ nằm ở dự án nào thì bản Listing phải đọc ở đúng dự án ấy. Mặc định trùng
# dự án của nửa làm ảnh vì đây là cùng một thẻ, chỉ khác nửa nào đang cầm.
DEFAULT_PROJECT = "PROJ-0013"
DEFAULT_TIMEOUT_S = 120

# Đường bản Listing dùng để chuẩn bị + xếp hàng một thẻ, không tạo ảnh mới.
ENQUEUE_PATH = "/api/etsy/browser-copy/enqueue"

# Bản Listing bỏ qua thẻ vì chính nó, không phải vì hỏng. Giữ nguyên tên lý do
# của đầu kia để đọc log hai bên còn khớp nhau.
SKIP_REASONS = {
    "meta_action_not_listing": "thẻ khai action khác, không phải listing",
    "already_in_done": "thẻ đã ở cột Done",
    "card_name_equals_list_name": "tên thẻ trùng tên cột",
}


class ListingBridgeError(RuntimeError):
    """Không giao được thẻ sang bản Listing."""


@dataclass(frozen=True)
class ListingBridgeConfig:
    """Bản Listing nằm ở đâu và thẻ của nó đi về máy nào."""

    api_url: str = ""
    project_id: str = DEFAULT_PROJECT
    status_id: str = ""
    # Đội máy Etsy mà bản Listing này phục vụ. Dùng để đổi ``acc32`` trên thẻ
    # thành tên máy thật theo quy ước số.
    machines: Tuple[str, ...] = ()
    # Máy nhận khi thẻ không nói gì. Trong đợt thử một máy thì đây chính là
    # cái máy duy nhất được phép nhận việc.
    default_machine: str = ""
    timeout_s: int = DEFAULT_TIMEOUT_S

    @property
    def enabled(self) -> bool:
        return bool(self.api_url.strip())

    @classmethod
    def from_env(cls) -> "ListingBridgeConfig":
        raw_machines = os.getenv("ERP_LISTING_MACHINES", "")
        machines = tuple(
            item.strip()
            for item in raw_machines.replace(";", ",").split(",")
            if item.strip()
        )
        timeout = os.getenv("ERP_LISTING_TIMEOUT_SECONDS", "").strip()
        project = (
            os.getenv("ERP_LISTING_PROJECT", "").strip()
            or os.getenv("ERP_PROJECT_ID", "").strip()
            or DEFAULT_PROJECT
        )
        return cls(
            api_url=os.getenv("ERP_LISTING_API_URL", "").strip().rstrip("/"),
            project_id=project.upper(),
            status_id=os.getenv("ERP_LISTING_STATUS", "").strip(),
            machines=machines,
            default_machine=os.getenv("ERP_LISTING_MACHINE", "").strip(),
            timeout_s=int(timeout) if timeout.isdigit() and int(timeout) > 0 else DEFAULT_TIMEOUT_S,
        )


# Đổi request thành dict trả về. Tách ra để test không phải mở cổng nào.
Transport = Callable[[str, Dict[str, Any], int], Dict[str, Any]]


def _post_json(url: str, payload: Dict[str, Any], timeout_s: int) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=timeout_s) as response:
            raw = response.read().decode("utf-8", "replace")
    except HTTPError as exc:  # bản Listing từ chối: đọc phần thân để biết vì sao
        detail = exc.read().decode("utf-8", "replace")[:400] if exc.fp else ""
        raise ListingBridgeError(f"Bản Listing trả lỗi HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise ListingBridgeError(f"Không gọi được bản Listing tại {url}: {exc.reason}") from exc
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        raise ListingBridgeError(f"Bản Listing trả về thứ không phải JSON: {raw[:200]}") from exc


class ListingBridge:
    """Một thẻ ERP → một lượt xếp hàng đăng Etsy bên bản Listing."""

    def __init__(self, config: ListingBridgeConfig, transport: Transport | None = None) -> None:
        self.config = config
        self._post = transport or _post_json

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def machine_for(self, root: Mapping[str, Any]) -> str:
        """Máy Etsy nhận thẻ này, theo thứ tự rõ ràng nhất trước.

        ``machine:`` viết trên thẻ thắng tất cả; sau đó là quy ước số của đội
        máy (``acc32`` → ``etsy-vn32``); cuối cùng mới tới máy mặc định của
        cấu hình. Không đoán thêm gì nữa: một thẻ chỉ tay vào máy không có
        thật thì thà báo lỗi còn hơn để nó chạy ở máy khác.
        """
        routing = resolve_routing(task_meta(root), known_machines=self.config.machines)
        return routing.machine_id or self.config.default_machine

    def payload(self, task_id: str, root: Mapping[str, Any]) -> Dict[str, Any]:
        """Yêu cầu đăng đúng thẻ này, không kèm lượt tạo ảnh nào.

        Tên trường là tên lịch sử của bản Listing (``erp_*``, ``etsy_*``);
        đầu kia đọc chúng và chỉ đi qua HaviGroup ERP. Giữ nguyên tên nghĩa là
        không phải sửa gì bên đó cho đợt thử này.
        """
        meta = task_meta(root)
        machine = self.machine_for(root)
        if not machine:
            raise ListingBridgeError(
                f"Thẻ {task_id} chưa chỉ được máy Etsy nào: thẻ không ghi `machine:`/`acc:` "
                "và cấu hình cũng chưa đặt ERP_LISTING_MACHINE."
            )
        subject = str(root.get("subject") or "").strip()
        return {
            # ``type`` là trường bắt buộc của lược đồ bên kia. Ở đường này nó
            # không kích hoạt lượt tạo ảnh nào — route enqueue đọc thẳng thẻ.
            "type": "image",
            "title": subject or f"Listing {task_id}",
            # Không có job thật ở đây; chuỗi này chỉ để đầu kia gắn nhãn.
            "source_job_id": f"erp-{task_id}",
            "erp_enabled": True,
            # Đầu kia để ``telegram_enabled`` **mặc định True**, nên không gửi
            # gì tức là đã đồng ý gửi. Ảnh đã được duyệt 👍 ngay trên thẻ ERP
            # rồi; bắt người ta duyệt lại lần nữa qua Telegram là hỏi một câu
            # đã có câu trả lời. Nói thẳng ra ở đây để ý định nằm trong payload,
            # chứ không nằm ở chỗ "may mà đường enqueue bên kia không đọc tới
            # trường này" — cái may ấy tan ngay khi bên kia sửa mã.
            "telegram_enabled": False,
            "erp_project_id": self.config.project_id,
            "erp_status_id": self.config.status_id,
            "erp_task_id": task_id,
            "erp_source_task_id": task_id,
            "etsy_enabled": True,
            "etsy_browser_copy_enabled": True,
            "etsy_account_id": meta.account_id,
            "etsy_machine_id": machine,
            "etsy_keep_color_chart": True,
            "etsy_delete_existing_images": True,
            # Chỉ dựng bản nháp. Không có bước nào trong đợt thử này được phép
            # đẩy hàng lên shop thật.
            "etsy_publish": False,
        }

    def dispatch(self, task_id: str, root: Mapping[str, Any]) -> Dict[str, Any]:
        """Giao thẻ đi. Trả về mã hàng đợi bên kia để còn lần theo được."""
        if not self.enabled:
            raise ListingBridgeError(
                "Chưa đặt ERP_LISTING_API_URL nên không có chỗ nào để giao thẻ listing."
            )
        payload = self.payload(task_id, root)
        response = self._post(
            f"{self.config.api_url}{ENQUEUE_PATH}", payload, self.config.timeout_s
        )
        return self._read(task_id, payload, response)

    def _read(
        self, task_id: str, payload: Mapping[str, Any], response: Any
    ) -> Dict[str, Any]:
        """Đọc câu trả lời của bản Listing, tách "nó từ chối" khỏi "nó hỏng"."""
        body = response.get("etsy_browser_copy") if isinstance(response, Mapping) else None
        if not isinstance(body, Mapping):
            raise ListingBridgeError(
                f"Bản Listing trả về thứ không đọc được cho thẻ {task_id}: {str(response)[:200]}"
            )
        machine = payload["etsy_machine_id"]

        if not body.get("configured", True):
            missing = ", ".join(str(item) for item in (body.get("missing") or [])) or "không rõ"
            raise ListingBridgeError(f"Bản Listing chưa cấu hình xong: thiếu {missing}.")

        if body.get("skipped"):
            reason = str(body.get("skip_reason") or "").strip()
            log.info("Bản Listing bỏ qua thẻ %s: %s.", task_id, SKIP_REASONS.get(reason, reason))
            return {
                "machine_id": machine,
                "skipped": SKIP_REASONS.get(reason, reason or "bản Listing không nói lý do"),
            }

        queue_task = body.get("queue_task")
        queue_id = str((queue_task or {}).get("id") or "").strip()
        if not body.get("enqueued") or not queue_id:
            missing = ", ".join(str(item) for item in (body.get("missing") or []))
            raise ListingBridgeError(
                f"Bản Listing không xếp hàng được thẻ {task_id}"
                + (f": thiếu {missing}." if missing else ".")
            )

        log.info(
            "Giao thẻ listing %s cho máy %s, hàng đợi %s bên bản Listing (%s ảnh).",
            task_id,
            machine,
            queue_id,
            body.get("image_count") or 0,
        )
        return {
            "queue_task_id": queue_id,
            "machine_id": machine,
            "sku": str(body.get("sku") or ""),
            "image_count": int(body.get("image_count") or 0),
        }


def build_listing_hook(bridge: ListingBridge | None):
    """Hook cho agent bot. ``None``/chưa bật thì trả về ``None`` — bot bỏ qua."""
    if bridge is None or not bridge.enabled:
        return None

    async def hook(task_id: str, root: Mapping[str, Any]) -> Dict[str, Any]:
        import asyncio

        return await asyncio.to_thread(bridge.dispatch, task_id, root)

    return hook
