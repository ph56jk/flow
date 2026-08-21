"""Agent bot: thả bot vào một dự án ERP rồi để thẻ tự chạy.

Đây là một module đứng riêng chứ không phải một nhánh nữa của ``service.py``,
và lý do nằm ở chỗ nó chạy bằng **danh tính khác**.

``service.py`` gọi ERP bằng cặp API key/secret của một người thật: mọi bình
luận nó đăng đều mang tên người đó. Nhưng ``deleteTaskComment`` chỉ xoá được
bình luận **của chính mình**, nên một tiến trình mang danh người A không bao
giờ dọn được thứ do người B đăng. Muốn "👎 là xoá" thành sự thật thì đúng một
danh tính phải vừa đăng ảnh vừa xoá ảnh — và đó là việc của một ``HVG Agent
Bot`` với token riêng.

Token bot mở đúng một đường: endpoint GraphQL. Nó không mở REST của Frappe,
nên module này cố tình đi trọn vẹn qua GraphQL (``uploadTaskFile`` +
``addTaskComment`` + ``deleteTaskComment``) thay vì mượn các helper REST của
``service.py``.

Phạm vi của bot được quyết định **trên chính ERP**, không phải trong file cấu
hình: bot chỉ đọc những dự án mà nó là ``Project User``, và trong mỗi dự án đó
nó nhận mọi thẻ Idea còn mở. Thả agent vào một dự án là toàn bộ thao tác cần
làm; gỡ agent ra là tắt. Gắn agent vào một thẻ cụ thể bằng ``addTaskAgent`` là
cách nói "chỉ chạy thẻ này thôi": hễ một dự án có thẻ gắn đích danh bot thì dự
án ấy thu về đúng những thẻ đó.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import threading
import time
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterator, List, Sequence, Tuple
from urllib.error import HTTPError, URLError

from urllib.request import Request, urlopen

from .erp_meta import task_meta
from .paths import DATA_DIR

log = logging.getLogger(__name__)


GRAPHQL_PATH = "/api/method/hvg_workspace.graphql.endpoint.graphql"
DEFAULT_BASE_URL = "https://erp.havigroup.llc"

# Cùng tiền tố mà service.py dùng cho ảnh chờ duyệt, để bot nhận ra bài đăng
# của luồng cũ chứ không chỉ bài của chính nó.
REVIEW_PREFIX = "FLOW_V2_REVIEW"
RESULT_PREFIX = f"{REVIEW_PREFIX}_RESULT"
# Ghi chú do chính bot để lại. Bot không được coi ghi chú của mình là một ảnh
# chờ duyệt, nếu không vòng sau nó sẽ tự dọn dấu vết của vòng trước.
BOT_NOTE_MARK = "[AGENT_BOT]"

DECISION_KEEP = "keep"
DECISION_DELETE = "delete"
DECISION_PENDING = ""

# Trần thật là 60 request/phút cho token bot (mục 8 của tài liệu API). Chừa
# một khoảng đệm: một lượt quét không đáng để đánh đổi lấy HTTP 429 làm hỏng
# cả vòng lặp.
RATE_LIMIT_PER_MINUTE = 50
# ``taskFull`` là field "nặng", trần 3 field nặng mỗi request — nên mỗi lượt
# gọi ở đây luôn chỉ hỏi đúng một cái.
TASK_FULL_DEPTH = 1

DEFAULT_POLL_SECONDS = 120
DEFAULT_AUTORUN_COOLDOWN_SECONDS = 900

# Phạm vi nhận việc.
SCOPE_BOARD = "board"  # thêm bot vào dự án là đủ; bot tự tìm thẻ Idea trong đó
SCOPE_CARD = "card"  # chỉ chạy thẻ có gắn bot
# Thẻ đã đóng thì không phải việc đang chờ, dù nó còn thẻ con chưa có ảnh.
#
# So khớp sau khi nén tên cột (bỏ dấu, bỏ mọi ký tự không phải chữ/số) chứ
# không so nguyên văn: bot được thiết kế để chạy trên *bất kỳ* board nào nó
# được thêm vào, và một board HaviGroup hoàn toàn có thể đặt tên cột bằng
# tiếng Việt. Nếu chỉ so đúng chữ tiếng Anh thì trên board như thế, một thẻ
# người ta đã huỷ vẫn được đếm là việc đang chờ và bot vẫn đốt quota tạo ảnh
# cho nó.
CLOSED_STATUSES = (
    "completed", "complete", "done", "cancelled", "canceled", "cancel", "closed",
    "hoanthanh", "dahoanthanh", "huy", "dahuy", "huybo", "dadong",
)
# Trần số thẻ Idea được khởi động trong một lượt quét. Cả app chỉ có một phiên
# Flow, nên xếp cả board vào hàng chỉ làm hàng đợi dài chứ không nhanh hơn; và
# một board mới thêm bot vào không nên biến thành hàng trăm job trong một phút.
DEFAULT_MAX_CARDS_PER_SCAN = 3
# Quyết định đã ghi thì giữ đủ lâu để một lần khởi động lại không làm bot
# quyết lại từ đầu, nhưng không giữ mãi để file state khỏi phình vô hạn.
HANDLED_RETENTION_DAYS = 45


class AgentBotError(RuntimeError):
    """Lỗi đã được diễn giải sang tiếng Việt cho người vận hành."""


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _truthy(value: str, default: bool) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return default
    if text in {"0", "false", "no", "off", "tat", "tắt"}:
        return False
    if text in {"1", "true", "yes", "on", "bat", "bật"}:
        return True
    return default


def _positive_int(value: str, default: int) -> int:
    text = str(value or "").strip()
    if not text:
        return default
    try:
        return max(0, int(text))
    except ValueError:
        return default


@dataclass(frozen=True)
class AgentBotConfig:
    """Cấu hình của bot. Chỉ ``token`` là bắt buộc."""

    token: str = ""
    base_url: str = DEFAULT_BASE_URL
    # Bỏ trống thì bot tự nhận ra chính mình (xem ``AgentBot.resolve_bot_user``).
    bot_user: str = ""
    # Bỏ trống nghĩa là "mọi dự án bot nhìn thấy" — đúng tinh thần "thả agent
    # vào dự án nào thì nó chạy ở đó". Điền vào để thu hẹp lại.
    projects: Tuple[str, ...] = ()
    poll_seconds: int = DEFAULT_POLL_SECONDS
    autorun: bool = True
    autorun_cooldown_seconds: int = DEFAULT_AUTORUN_COOLDOWN_SECONDS
    # ``board``: thêm bot vào dự án là xong, bot tự tìm thẻ Idea trong dự án đó.
    # ``card``: chỉ chạy thẻ có gắn bot. Ngay cả ở ``board``, hễ trong một dự án
    # có thẻ gắn bot thì dự án đó thu về đúng những thẻ ấy — nói rõ vẫn thắng suy
    # đoán, và đó là cách chỉ định "chỉ chạy thẻ này thôi".
    scope: str = SCOPE_BOARD
    # Cột nguồn của phạm vi ``board``: bỏ trống = mọi cột chưa đóng, đúng như
    # trước. Điền vào thì kéo thẻ sang cột ấy mới là lời giao việc, còn cột
    # nháp bên trái vẫn là chỗ gõ dở mà bot không đụng vào. Chỉ chặn phạm vi
    # ``board``: thẻ đã gắn đích danh bot vẫn chạy dù nằm ở cột nào, vì gắn bot
    # là cách duy nhất cứu một thẻ lỡ nhịp — chặn cả chỗ đó thì mất lối cứu.
    source_statuses: Tuple[str, ...] = ()
    max_cards_per_scan: int = DEFAULT_MAX_CARDS_PER_SCAN
    # Chạy khô: ghi log quyết định nhưng không xoá gì. Dùng khi mới cắm bot
    # vào một dự án lạ và chưa tin phạm vi của nó.
    dry_run: bool = False
    timeout_s: int = 60

    @property
    def enabled(self) -> bool:
        return bool(self.token.strip())

    @classmethod
    def from_env(cls, base_url: str = "") -> "AgentBotConfig":
        raw_projects = os.getenv("ERP_AGENT_PROJECTS", "")
        names = [
            item.strip().upper()
            for item in raw_projects.replace(";", ",").split(",")
            if item.strip()
        ]
        # Narrowing the bot must never push it out of the project the rest of
        # the app already works in: listing the extra projects is meant to add
        # to the scope, and silently dropping the home project instead would
        # stop the bot exactly where it is most expected to run.
        home = os.getenv("ERP_PROJECT_ID", "").strip().upper()
        if names and home and home not in names:
            names.append(home)
        projects = tuple(names)
        raw_source = os.getenv("ERP_AGENT_SOURCE_STATUS", "").replace(";", ",")
        source_statuses = tuple(item.strip() for item in raw_source.split(",") if item.strip())
        for wanted in source_statuses:
            if compact_status(wanted) in CLOSED_STATUSES:
                # Đặt cột nguồn vào một cột đã đóng là hỏng câm: ``is_idea_card``
                # loại thẻ ở cột đóng trước cả bước này, nên bot sẽ quét mãi mà
                # không bao giờ nhận việc, và không có lỗi nào để mà đọc.
                log.warning(
                    "ERP_AGENT_SOURCE_STATUS=%r trỏ vào một cột đã đóng — bot sẽ "
                    "không bao giờ nhận được thẻ nào từ phạm vi board.",
                    wanted,
                )
        configured_base = (
            str(base_url or "").strip()
            or os.getenv("ERP_BASE_URL", "").strip()
            or DEFAULT_BASE_URL
        )
        return cls(
            token=os.getenv("ERP_AGENT_TOKEN", "").strip(),
            base_url=configured_base.rstrip("/"),
            bot_user=os.getenv("ERP_AGENT_BOT_USER", "").strip(),
            projects=projects,
            poll_seconds=_positive_int(os.getenv("ERP_AGENT_POLL_SECONDS", ""), DEFAULT_POLL_SECONDS),
            autorun=_truthy(os.getenv("ERP_AGENT_AUTORUN", ""), True),
            autorun_cooldown_seconds=_positive_int(
                os.getenv("ERP_AGENT_AUTORUN_COOLDOWN_SECONDS", ""),
                DEFAULT_AUTORUN_COOLDOWN_SECONDS,
            ),
            scope=SCOPE_CARD
            if os.getenv("ERP_AGENT_SCOPE", "").strip().lower() == SCOPE_CARD
            else SCOPE_BOARD,
            source_statuses=source_statuses,
            max_cards_per_scan=_positive_int(
                os.getenv("ERP_AGENT_MAX_CARDS_PER_SCAN", ""), DEFAULT_MAX_CARDS_PER_SCAN
            ),
            dry_run=_truthy(os.getenv("ERP_AGENT_DRY_RUN", ""), False),
        )


class _RateLimiter:
    """Cửa sổ trượt cho trần 60 request/phút của token bot.

    Chặn thay vì ném lỗi: một lượt quét chậm vài giây vẫn tốt hơn một lượt
    quét hỏng giữa chừng vì 429.
    """

    def __init__(self, limit: int = RATE_LIMIT_PER_MINUTE, window_s: float = 60.0) -> None:
        self._limit = max(1, int(limit))
        self._window_s = float(window_s)
        self._hits: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                while self._hits and now - self._hits[0] >= self._window_s:
                    self._hits.popleft()
                if len(self._hits) < self._limit:
                    self._hits.append(now)
                    return
                wait_s = self._window_s - (now - self._hits[0])
            time.sleep(max(0.05, wait_s))


class AgentBotClient:
    """Client GraphQL thuần, xác thực bằng ``Authorization: HVGToken <token>``.

    Đồng bộ (urllib) giống các helper ERP sẵn có trong ``service.py``; phía
    async gọi nó qua ``asyncio.to_thread``.
    """

    def __init__(self, config: AgentBotConfig, limiter: _RateLimiter | None = None) -> None:
        if not config.enabled:
            raise AgentBotError("Chưa có ERP_AGENT_TOKEN nên không dựng được client cho agent bot.")
        self._config = config
        self._limiter = limiter or _RateLimiter()

    # ── nền ────────────────────────────────────────────────────────────

    def _redact(self, value: Any) -> str:
        """Không bao giờ để token bot rơi vào log hay thông điệp lỗi."""
        text = str(value or "")
        token = self._config.token.strip()
        return text.replace(token, "[redacted]") if token else text

    def graphql(
        self,
        query: str,
        variables: Dict[str, Any] | None = None,
        operation_name: str = "",
        *,
        retries: int = 2,
    ) -> Dict[str, Any]:
        endpoint = f"{self._config.base_url}{GRAPHQL_PATH}"
        body = json.dumps(
            {
                "query": query,
                "variables": variables or {},
                "operationName": operation_name or None,
            },
            ensure_ascii=False,
        ).encode("utf-8")

        attempt = 0
        while True:
            self._limiter.acquire()
            request = Request(
                endpoint,
                data=body,
                method="POST",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    # Lớp Cloudflare của ERP chặn chữ ký urllib mặc định.
                    "User-Agent": "Flow-v2-HaviGroup-ERP/1.0",
                    "Authorization": f"HVGToken {self._config.token}",
                },
            )
            try:
                with urlopen(request, timeout=self._config.timeout_s) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                break
            except HTTPError as exc:
                detail = self._redact(exc.read().decode("utf-8", errors="replace") or exc.reason)
                if exc.code == 401:
                    # Sáu điều kiện làm token vô hiệu, và phản hồi cố ý không
                    # nói rõ điều nào — nên liệt kê cả sáu cho người vận hành.
                    raise AgentBotError(
                        "ERP từ chối token agent bot (HTTP 401). Kiểm tra: token đã thu hồi, "
                        "bot bị tắt (kill-switch), hoặc người chịu trách nhiệm của bot bị khoá."
                    ) from exc
                if exc.code == 429 and attempt < retries:
                    attempt += 1
                    time.sleep(min(30.0, 5.0 * attempt))
                    continue
                if exc.code == 429:
                    raise AgentBotError(
                        "ERP đang giới hạn tốc độ token bot (HTTP 429). Hãy giãn ERP_AGENT_POLL_SECONDS."
                    ) from exc
                raise AgentBotError(f"ERP HTTP {exc.code}: {detail}") from exc
            except URLError as exc:
                if attempt < retries:
                    attempt += 1
                    time.sleep(min(15.0, 3.0 * attempt))
                    continue
                raise AgentBotError(self._redact(exc.reason or exc)) from exc

        try:
            envelope = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise AgentBotError("ERP trả dữ liệu không phải JSON.") from exc
        errors = envelope.get("errors") if isinstance(envelope, dict) else None
        if isinstance(errors, list) and errors:
            messages = [str(item.get("message") or "GraphQL error") for item in errors if isinstance(item, dict)]
            raise AgentBotError(self._redact("ERP GraphQL: " + "; ".join(messages)))
        data = envelope.get("data") if isinstance(envelope, dict) else None
        if not isinstance(data, dict):
            raise AgentBotError("ERP GraphQL không trả data hợp lệ.")
        return data

    # ── query ──────────────────────────────────────────────────────────

    def task_projects(self) -> List[Dict[str, Any]]:
        payload = self.graphql("query TaskProjects { taskProjects }", {}, "TaskProjects")
        projects = (payload.get("taskProjects") or {}).get("projects")
        return [item for item in (projects or []) if isinstance(item, dict)]

    def task_board(self, project: str) -> List[Dict[str, Any]]:
        """Mọi task chưa lưu trữ của một dự án, đã trải phẳng khỏi các cột."""
        payload = self.graphql(
            "query TaskBoard($project: String!) { taskBoard(project: $project, includeArchived: false) }",
            {"project": project},
            "TaskBoard",
        )
        board = payload.get("taskBoard") or {}
        tasks: List[Dict[str, Any]] = []
        for column in board.get("columns") or []:
            if not isinstance(column, dict):
                continue
            for task in column.get("tasks") or []:
                if isinstance(task, dict):
                    tasks.append(task)
        return tasks

    def task_full(self, name: str, depth: int = TASK_FULL_DEPTH) -> Dict[str, Any]:
        payload = self.graphql(
            "query TaskFull($name: String!, $depth: Int) { taskFull(name: $name, depth: $depth) }",
            {"name": name, "depth": int(depth)},
            "TaskFull",
        )
        return payload.get("taskFull") or {}

    # ── mutation ───────────────────────────────────────────────────────

    def add_comment(
        self,
        task: str,
        content: str,
        attachments: Sequence[str] | None = None,
        parent: str = "",
    ) -> Dict[str, Any]:
        variables: Dict[str, Any] = {"name": task, "content": content}
        if attachments:
            variables["attachments"] = list(attachments)
        if parent:
            variables["parent"] = parent
        payload = self.graphql(
            "mutation AddTaskComment($name: String!, $content: String!, "
            "$attachments: [String!], $parent: String) "
            "{ addTaskComment(name: $name, content: $content, attachments: $attachments, parent: $parent) }",
            variables,
            "AddTaskComment",
        )
        return payload.get("addTaskComment") or {}

    def upload_file(self, task: str, file_name: str, content: bytes, purpose: str = "comment") -> Dict[str, Any]:
        """Tải tệp lên task và trả về bản ghi File (có ``file_url``).

        ``purpose`` phải là ``comment`` nếu tệp sắp đi kèm một bình luận: tải
        bằng ``attachment`` rồi truyền vào ``addTaskComment`` vẫn ra HTTP 200
        nhưng ``linked = 0`` và tệp không hiện trong bình luận.
        """
        payload = self.graphql(
            "mutation UploadTaskFile($task: String!, $fileName: String!, "
            "$contentBase64: String!, $purpose: String) "
            "{ uploadTaskFile(task: $task, fileName: $fileName, "
            "contentBase64: $contentBase64, purpose: $purpose) }",
            {
                "task": task,
                "fileName": file_name,
                "contentBase64": base64.b64encode(content).decode("ascii"),
                "purpose": purpose,
            },
            "UploadTaskFile",
        )
        uploaded = payload.get("uploadTaskFile") or {}
        if not str(uploaded.get("file_url") or "").strip():
            raise AgentBotError(f"ERP không trả file_url khi tải {file_name} lên {task}.")
        return uploaded

    def delete_comment(self, task: str, comment: str) -> Dict[str, Any]:
        payload = self.graphql(
            "mutation DeleteTaskComment($name: String!, $comment: String!) "
            "{ deleteTaskComment(name: $name, comment: $comment) }",
            {"name": task, "comment": comment},
            "DeleteTaskComment",
        )
        return payload.get("deleteTaskComment") or {}

    def set_comment_vote(self, task: str, comment: str, vote: str) -> Dict[str, Any]:
        """Đặt phiếu theo trạng thái đích.

        Cố ý dùng ``setTaskCommentVote`` chứ không phải ``toggle``: toggle đọc
        rồi ghi ngoài một đoạn tuần tự hoá, nên hai lượt song song có thể nuốt
        mất một thao tác. Đặt trạng thái đích thì miễn nhiễm với ca đó.
        """
        payload = self.graphql(
            "mutation SetTaskCommentVote($name: String!, $comment: String!, $vote: String!) "
            "{ setTaskCommentVote(name: $name, comment: $comment, vote: $vote) }",
            {"name": task, "comment": comment, "vote": vote},
            "SetTaskCommentVote",
        )
        return payload.get("setTaskCommentVote") or {}

    def add_task_agent(self, task: str, bot_user: str) -> Dict[str, Any]:
        """Gắn bot vào một thẻ — đúng thao tác chọn agent ở ô Người phụ trách."""
        payload = self.graphql(
            "mutation AddTaskAgent($task: String!, $botUser: String!) "
            "{ addTaskAgent(task: $task, botUser: $botUser) }",
            {"task": task, "botUser": bot_user},
            "AddTaskAgent",
        )
        result = payload.get("addTaskAgent")
        return result if isinstance(result, dict) else {}

    def publish_image(
        self,
        task: str,
        file_name: str,
        content: bytes,
        body: str,
        parent: str = "",
    ) -> Dict[str, Any]:
        """Đăng một ảnh thành bình luận **của bot** để người ta bấm 👍/👎.

        Đây là điểm mấu chốt của cả module: chỉ khi bình luận thuộc về bot thì
        ``deleteTaskComment`` mới xoá được nó lúc bị 👎.
        """
        uploaded = self.upload_file(task, file_name, content, purpose="comment")
        file_url = str(uploaded.get("file_url") or "")
        result = self.add_comment(task, body, attachments=[file_url], parent=parent)
        linked = int(result.get("linked") or 0)
        if linked < 1:
            # HTTP 200 mà tệp vẫn rơi mất là ca đã biết của addTaskComment; đối
            # chiếu ``linked`` là cách duy nhất phát hiện.
            raise AgentBotError(
                f"ERP nhận bình luận nhưng không gắn được ảnh {file_name} vào (linked=0)."
            )
        return {"file_url": file_url, "file": uploaded, "linked": linked}


# ── Đọc phiếu ──────────────────────────────────────────────────────────


def plain_text(content: Any) -> str:
    """Nội dung bình luận về dưới dạng HTML của trình soạn thảo."""
    text = re.sub(r"<[^>]+>", " ", str(content or ""))
    return re.sub(r"\s+", " ", unescape(text)).strip()


def vote_decision(node: Dict[str, Any]) -> str:
    """Đọc 👍/👎 của một bình luận thành quyết định.

    Hoà phiếu — kể cả 3-3 — cố ý là **chưa ngã ngũ**, không phải "giữ". Xoá là
    thao tác không hoàn tác được, nên nó chỉ xảy ra khi phía 👎 thực sự thắng.
    """
    like = int(node.get("like_count") or 0)
    dislike = int(node.get("dislike_count") or 0)
    if dislike > like:
        return DECISION_DELETE
    if like > dislike:
        return DECISION_KEEP
    return DECISION_PENDING


def node_markers(node: Dict[str, Any]) -> str:
    """Dấu của app trên một bình luận, dù nó nằm ở ``meta`` hay ở thân.

    Bình luận ảnh bây giờ không mang chữ nào - dấu chuyển hết sang ``meta`` để
    thẻ chỉ còn tấm ảnh - nhưng bình luận của các lượt chạy cũ vẫn mang dấu
    trong thân, nên đọc cả hai chỗ.
    """
    if not isinstance(node, dict):
        return ""
    parts = (str(node.get("meta") or ""), plain_text(node.get("content")))
    return " ".join(part for part in parts if part)


def is_bot_note(node: Dict[str, Any]) -> bool:
    """Ghi chú kết quả do chính bot để lại, không phải một ảnh chờ duyệt."""
    text = node_markers(node)
    return BOT_NOTE_MARK in text or RESULT_PREFIX in text


def is_review_post(node: Dict[str, Any]) -> bool:
    """Một bình luận có phải là "ảnh đang chờ duyệt" hay không.

    Hai điều kiện, và điều kiện quyền là điều kiện cứng:

    * ``mine`` — bot phải là tác giả, vì nó chỉ xoá được bình luận của chính
      mình. Ảnh do luồng cũ đăng dưới danh tính người thật thì bot đọc được
      phiếu nhưng **không** dọn được, nên không nhận là việc của mình.
    * có tệp đính kèm, hoặc mang thẻ ``[FLOW_V2_REVIEW ...]`` của luồng cũ.
    """
    if int(node.get("mine") or 0) != 1:
        return False
    if is_bot_note(node):
        return False
    if node.get("attachments"):
        return True
    return REVIEW_PREFIX in node_markers(node)


def iter_tree_nodes(root: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Duyệt task gốc cùng toàn bộ cây việc con mà ``taskFull`` trả về.

    ``children`` chỉ là danh sách mỏng (tên, tiêu đề, trạng thái); cây đầy đủ
    kèm bình luận nằm ở ``subtasks``. Ảnh thường nằm trên thẻ con chứ không
    phải thẻ cha, nên đi nhầm nhánh là bỏ sót toàn bộ việc.
    """
    if not isinstance(root, dict):
        return
    yield root
    for child in root.get("subtasks") or []:
        if isinstance(child, dict):
            yield from iter_tree_nodes(child)


def iter_review_posts(task_node: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Mọi bình luận (cấp task lẫn phản hồi trong thread) đang chờ phán quyết."""
    for comment in task_node.get("comments") or []:
        if not isinstance(comment, dict):
            continue
        if is_review_post(comment):
            yield comment
        for reply in comment.get("replies") or []:
            if isinstance(reply, dict) and is_review_post(reply):
                yield reply


IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif")

# Chỗ cất dòng bảng dự án của thẻ ngay trong cây ``taskFull``. Gạch dưới ở đầu
# để không đụng field nào của ERP, hôm nay hay mai kia.
BOARD_ROW_KEY = "_board_row"


def count_card_images(task_node: Dict[str, Any], board_row: Dict[str, Any] | None = None) -> int:
    """Bao nhiêu ảnh đang nằm trên chính thẻ này (bìa + ảnh trong bình luận).

    Dùng để nhận ra thẻ Idea vừa được thả thêm ảnh: ảnh đầu là ảnh sản phẩm,
    từ ảnh thứ hai trở đi là idea người dùng vừa đưa vào và chưa thành thẻ con.
    Ảnh Flow tự sinh ra không tính - chúng nằm ở thẻ con chứ không ở đây, và
    đếm nhầm chúng sẽ khiến thẻ nào chạy xong cũng trông như vừa có ảnh mới.

    ``taskFull`` **không** trả về tệp treo thẳng trên thẻ, mà kéo-thả một tấm
    ảnh vào thẻ thì nó nằm đúng ở đó: thẻ vừa được thả ba tấm đọc về không bìa,
    không bình luận, không gì cả. Dòng của thẻ trên bảng dự án thì có
    ``attachment_count``, nên nếu gọi kèm dòng đó thì lấy số nào lớn hơn. Con
    số ấy đếm cả tệp không phải ảnh, nhưng đây là bước *nhận thẻ đáng đọc*, còn
    việc lọc ảnh thật thì ``enqueue_erp_idea_jobs`` làm sau và làm đúng.
    """
    hung_on_card = int((board_row or {}).get("attachment_count") or 0)
    seen: set[str] = set()
    cover = str(task_node.get("cover_image") or "").strip()
    if cover:
        seen.add(cover)
    for comment in task_node.get("comments") or []:
        if not isinstance(comment, dict):
            continue
        if "FLOW_V2_ARTIFACT" in node_markers(comment):
            continue
        for attachment in comment.get("attachments") or []:
            if not isinstance(attachment, dict):
                continue
            name = str(attachment.get("file_name") or attachment.get("name") or "").strip()
            url = str(attachment.get("file_url") or attachment.get("url") or "").strip()
            if not name.lower().endswith(IMAGE_SUFFIXES) or name.lower().startswith("flow-"):
                continue
            seen.add(url or name)
        # ``taskFull`` trả bình luận với ``attachments`` **rỗng** và chỉ giữ một
        # ``image`` đại diện, trong khi ``taskDetail`` của đúng bình luận ấy trả
        # đủ cả mười tấm. Thẻ có ảnh idea dán trong bình luận vì thế đọc về vỏn
        # vẹn một tấm bìa và bị từ chối ngay tại cửa. Đếm thêm ảnh đại diện đó:
        # bước này chỉ hỏi "thẻ này có gì ngoài ảnh sản phẩm không", còn đếm cho
        # đủ là việc của ``enqueue_erp_idea_jobs`` — nó đọc ``taskDetail``.
        image = str(comment.get("image") or "").strip()
        if image.lower().endswith(IMAGE_SUFFIXES) and not image.rsplit("/", 1)[-1].lower().startswith("flow-"):
            seen.add(image)
    return max(len(seen), hung_on_card)


def compact_status(value: Any) -> str:
    """Tên cột ERP nén lại để so khớp: bỏ dấu, bỏ ký tự thừa, còn chữ thường.

    ``"Đã hủy"`` → ``"dahuy"``, ``"Pending Review"`` → ``"pendingreview"``.

    ``đ`` được đổi thành ``d`` *trước* khi bỏ dấu, vì ``unicodedata`` không
    tách được nó: nó là một chữ cái riêng chứ không phải ``d`` cộng dấu. Bỏ
    bước này thì ``"Đã hủy"`` nén thành ``"ahuy"`` — vẫn khớp được nếu ta viết
    đúng chuỗi đó vào bảng, nhưng người đọc sau sẽ tưởng là gõ nhầm và "sửa"
    nó thành ``"dahuy"``, lúc ấy hàng rào im lặng thủng.
    """
    text = str(value or "").strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if ch.isascii() and ch.isalnum())


def is_idea_card(task: Dict[str, Any], board_row: Dict[str, Any] | None = None) -> bool:
    """Thẻ Idea: thẻ cha còn mở, có thẻ con - hoặc sắp có.

    Đây là bộ lọc của chế độ ``board``, và nó cố ý hẹp. Thẻ đã Hoàn thành/Huỷ
    thì việc của nó đã xong, và tự chạy lại một thẻ người ta vừa đóng là cách
    nhanh nhất để bot bị tắt.

    Thẻ chưa có con vẫn được nhận trong hai trường hợp: nó là thẻ nhóm
    (``is_group``), hoặc nó đang mang từ hai tệp trở lên. Cái sau mới là đường
    của người dùng thật - kéo ảnh sản phẩm cùng mấy ảnh idea vào một thẻ trắng
    - và ``attachment_count`` của bảng dự án là chỗ duy nhất đếm được chúng mà
    không tốn thêm request. Một tệp thì chưa có gì để làm: đó là ảnh sản phẩm
    đứng một mình.
    """
    if not isinstance(task, dict):
        return False
    # ``taskFull`` không có ``attachment_count``; chỉ dòng của thẻ trên bảng dự
    # án mới có, nên khi xét một cây thì phải đưa kèm dòng đó vào.
    attachments = max(
        int(task.get("attachment_count") or 0),
        int((board_row or {}).get("attachment_count") or 0),
    )
    if int(task.get("child_total") or 0) <= 0 and not task.get("is_group") and attachments < 2:
        return False
    return compact_status(task.get("status")) not in CLOSED_STATUSES


def card_is_in_source_column(task: Dict[str, Any], wanted: Sequence[str]) -> bool:
    """Thẻ có đang nằm ở cột nguồn không. ``wanted`` rỗng = mọi cột đều tính.

    So bằng ``compact_status`` ở *cả hai* đầu, nên ``Working`` trong file cấu
    hình khớp cả ``working`` lẫn ``WORKING``, và một board đặt tên cột bằng
    tiếng Việt vẫn khớp được. So nguyên văn thì người ta gõ đúng tên cột mình
    đang nhìn thấy mà bot vẫn đứng im — đúng kiểu hỏng không ai đọc ra.
    """
    keys = {compact_status(name) for name in wanted}
    keys.discard("")
    if not keys:
        return True
    return compact_status(task.get("status")) in keys


def is_listing_card(task_node: Dict[str, Any]) -> bool:
    """Thẻ này có tự nhận mình là việc listing Etsy không.

    Hai nửa của hệ — làm ảnh và lên listing Etsy — dùng chung một ERP và sẽ
    dùng chung một agent. Thứ phân biệt chúng là khối *Thuộc tính* của thẻ::

        action_1: listing
        acc: acc32

    Thẻ ảnh không viết ``action_*`` nào cả (``sku`` / ``product`` /
    ``fatheridea`` / ``prompt``), nên "không nói gì" bắt buộc phải có nghĩa là
    *làm như cũ*, không bao giờ là *từ chối*. Nhờ vậy thêm khả năng listing
    không đụng một thẻ ảnh nào đang chạy.

    ``taskFull`` trả sẵn ``meta`` trong ``root`` (đo thật trên
    TASK-2026-00202), nên bước phân loại này không tốn thêm request nào.
    """
    return task_meta(task_node).is_listing


def listing_readiness(task_node: Dict[str, Any]) -> Tuple[bool, str]:
    """Thẻ listing này đã đăng được chưa, và nếu chưa thì còn thiếu gì.

    Nửa listing không tạo ảnh: nó lấy đúng bộ ảnh đang nằm trên thẻ, chép sang
    máy Etsy rồi dựng bản nháp. Nên "đăng được" nghĩa là bộ ảnh trên thẻ đã
    chốt — mọi ảnh đều đã có người bấm 👍 hoặc 👎, và còn lại ít nhất một ảnh
    được giữ.

    Chỉ ảnh *chờ* mới chặn. Ảnh bị 👎 coi như đã chốt: cùng lượt quét này
    ``janitor_pass`` gỡ nó khỏi thẻ, nên thứ bản Listing tải về sẽ không còn
    nó nữa.

    Chưa có ảnh nào cũng là "chưa xong", không phải hỏng: thẻ vừa được gắn
    agent thì nửa làm ảnh chạy trước, xong rồi mới tới lượt đăng.
    """
    posts = list(iter_review_posts(task_node))
    if not posts:
        return False, "thẻ chưa có ảnh nào để đăng"
    decisions = [vote_decision(post) for post in posts]
    waiting = sum(1 for decision in decisions if decision == DECISION_PENDING)
    if waiting:
        return False, f"còn {waiting} ảnh chờ 👍/👎"
    if not any(decision == DECISION_KEEP for decision in decisions):
        return False, "không còn ảnh nào được giữ"
    return True, ""


def task_has_agent(task_node: Dict[str, Any], bot_user: str) -> bool:
    if not bot_user:
        return False
    for agent in task_node.get("agents") or []:
        if isinstance(agent, dict) and str(agent.get("bot_user") or "").strip() == bot_user:
            return True
    return False


# ── Trạng thái ─────────────────────────────────────────────────────────


@dataclass
class AgentBotState:
    """Sổ ghi của bot, để một lần khởi động lại không quyết lại từ đầu."""

    path: Path
    bot_user: str = ""
    handled: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    runs: Dict[str, str] = field(default_factory=dict)
    # Thẻ đã giao sang bản Listing. Cố ý **không** nằm trong ``handled`` vì sổ
    # đó tự hết hạn sau ít ngày: quên một thẻ đã đăng nghĩa là đăng lần hai,
    # tức là hai bản nháp trong shop cho cùng một sản phẩm.
    listed: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Những dự án lượt quét gần nhất thấy được. Ghi ra đĩa để phần còn lại của
    # app biết ngay từ lúc khởi động là bot đang đứng ở những board nào, thay
    # vì phải đợi hết một chu kỳ quét mới biết.
    projects: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> "AgentBotState":
        target = Path(path) if path is not None else DATA_DIR / "agent_bot_state.json"
        state = cls(path=target)
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return state
        if not isinstance(raw, dict):
            return state
        state.bot_user = str(raw.get("bot_user") or "").strip()
        handled = raw.get("handled")
        if isinstance(handled, dict):
            state.handled = {str(k): v for k, v in handled.items() if isinstance(v, dict)}
        runs = raw.get("runs")
        if isinstance(runs, dict):
            state.runs = {str(k): str(v) for k, v in runs.items()}
        listed = raw.get("listed")
        if isinstance(listed, dict):
            state.listed = {str(k): v for k, v in listed.items() if isinstance(v, dict)}
        projects = raw.get("projects")
        if isinstance(projects, list):
            state.projects = [
                name for name in (str(item).strip().upper() for item in projects) if name
            ]
        return state

    def save(self) -> None:
        self.prune()
        payload = {
            "bot_user": self.bot_user,
            "handled": self.handled,
            "runs": self.runs,
            "listed": self.listed,
            "projects": self.projects,
            "saved_at": _utc_now_text(),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Ghi qua tệp tạm rồi thay chỗ: một lần tắt máy giữa chừng không
            # được phép để lại file state cụt làm bot quyết lại từ đầu.
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.path)
        except OSError as exc:
            log.warning("Không ghi được state của agent bot: %s", exc)

    def prune(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=HANDLED_RETENTION_DAYS)
        for comment_id, entry in list(self.handled.items()):
            stamp = str(entry.get("at") or "")
            try:
                when = datetime.fromisoformat(stamp)
            except ValueError:
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when < cutoff:
                self.handled.pop(comment_id, None)

    def already_handled(self, comment_id: str) -> bool:
        return bool(comment_id) and comment_id in self.handled

    def record(self, comment_id: str, task: str, decision: str) -> None:
        if not comment_id:
            return
        self.handled[comment_id] = {"task": task, "decision": decision, "at": _utc_now_text()}

    def already_listed(self, task: str) -> bool:
        return bool(task) and task in self.listed

    def record_listing(self, task: str, outcome: Dict[str, Any]) -> None:
        if not task:
            return
        self.listed[task] = {
            "queue_task": str(outcome.get("queue_task_id") or ""),
            "machine": str(outcome.get("machine_id") or ""),
            "at": _utc_now_text(),
        }

    def autorun_is_cool(self, task: str, cooldown_s: int) -> bool:
        stamp = self.runs.get(task)
        if not stamp or cooldown_s <= 0:
            return True
        try:
            when = datetime.fromisoformat(stamp)
        except ValueError:
            return True
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - when >= timedelta(seconds=cooldown_s)

    def mark_autorun(self, task: str) -> None:
        self.runs[task] = _utc_now_text()


# ── Bot ────────────────────────────────────────────────────────────────

# Hook chạy việc: nhận id task cha đã gắn agent, trả về payload tuỳ ý.
AutorunHook = Callable[[str], Awaitable[Dict[str, Any]]]
# Hook listing nhận thêm chính thẻ đã đọc: bên kia cần ``meta`` để biết máy
# Etsy nào nhận, và đọc lại thẻ lần nữa chỉ để lấy thứ đang cầm trên tay là
# tốn một request của trần 60/phút.
ListingHook = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]


class AgentBot:
    """Một lượt quét: tìm task đã gắn agent → dọn theo phiếu → chạy việc."""

    def __init__(
        self,
        config: AgentBotConfig,
        client: AgentBotClient | None = None,
        state: AgentBotState | None = None,
        autorun_hook: AutorunHook | None = None,
        listing_hook: ListingHook | None = None,
    ) -> None:
        self.config = config
        self.client = client or AgentBotClient(config)
        self.state = state if state is not None else AgentBotState.load()
        self.autorun_hook = autorun_hook
        self.listing_hook = listing_hook

    # ── phạm vi ────────────────────────────────────────────────────────

    def scope_projects(self) -> List[str]:
        """Các dự án bot được phép quét.

        Không cấu hình thì lấy đúng danh sách ERP trả về — tức là những dự án
        bot đã được thêm vào ``Project User``. Phạm vi do ERP quyết, không do
        file cấu hình, nên gỡ bot khỏi dự án là nó hết thấy dự án đó ngay.
        """
        visible = [
            str(item.get("name") or "").strip().upper()
            for item in self.client.task_projects()
            if str(item.get("name") or "").strip()
        ]
        if not self.config.projects:
            return self._remember(visible)
        wanted = set(self.config.projects)
        allowed = [name for name in visible if name in wanted]
        for missing in sorted(wanted - set(visible)):
            log.warning(
                "Agent bot được cấu hình cho %s nhưng ERP không cho nó thấy dự án đó "
                "(chưa thêm bot vào Project User?).",
                missing,
            )
        return self._remember(allowed)

    def _remember(self, projects: List[str]) -> List[str]:
        """Ghi lại phạm vi vừa thấy, cho phần còn lại của app dùng chung.

        Thêm bot vào một board trên ERP là xong — không phải khai lại board đó
        ở đâu nữa. Nhưng hàng rào dự án của app lại là một sổ riêng, nên nó đọc
        đúng cái sổ này để hai bên không bao giờ lệch nhau.
        """
        self.state.projects = list(projects)
        return projects

    @staticmethod
    def _drop_inherited_children(attached: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bỏ thẻ con khi thẻ cha của chính nó cũng đang gắn bot.

        Gắn bot vào thẻ cha là lan xuống cả thẻ con (``inherit_pass``), mà cây
        của thẻ cha vốn đã chứa sẵn bình luận của con. Không lọc thì trần
        ``max_cards_per_scan`` bị chính đám con ăn hết còn thẻ cha phải đợi
        lượt sau — gắn bot vào một thẻ hoá ra làm thẻ ấy chạy chậm đi.

        Thẻ con được gắn *một mình*, cha không gắn, thì vẫn giữ: đó là người
        dùng cố ý chỉ đúng một thẻ.
        """
        names = {
            name for name in (str(task.get("name") or "").strip() for task in attached) if name
        }
        return [
            task
            for task in attached
            if str(task.get("parent_task") or "").strip() not in names
        ]

    def candidate_tasks(self, projects: Sequence[str], bot_user: str = "") -> List[Dict[str, Any]]:
        """Những thẻ bot nhận là việc của mình, xét theo từng dự án.

        Thêm bot vào một dự án đã là lời giao việc rồi — đó là điều người dùng
        thấy trên trang Agent Bot — nên mặc định bot nhận mọi thẻ Idea của dự án
        đó. Nhưng nếu trong dự án có thẻ được gắn đích danh bot, thì dự án ấy
        thu về đúng những thẻ đó: gắn vào một thẻ chỉ có nghĩa duy nhất là "chạy
        thẻ này", và hiểu ngược lại thì thao tác gắn thẻ hoá ra không làm gì cả.

        Bảng dự án đã trả sẵn ``child_total`` và ``status`` nên bước lọc này
        không tốn thêm request nào — ``taskFull`` chỉ được tiêu cho thẻ đã chọn.
        """
        found: List[Dict[str, Any]] = []
        for project in projects:
            try:
                tasks = self.client.task_board(project)
            except AgentBotError as exc:
                log.warning("Không đọc được bảng %s: %s", project, exc)
                continue
            if bot_user:
                attached = [task for task in tasks if task_has_agent(task, bot_user)]
            else:
                # Chưa biết mình là ai thì thẻ gắn agent bất kỳ vẫn đáng đọc:
                # chính nó là chỗ rẻ nhất để nhận ra danh tính của bot.
                attached = [task for task in tasks if task.get("agents")]
            if attached:
                found.extend(self._drop_inherited_children(attached))
                continue
            if self.config.scope != SCOPE_BOARD:
                continue
            wanted = self.config.source_statuses
            open_cards = [task for task in tasks if is_idea_card(task)]
            picked = [task for task in open_cards if card_is_in_source_column(task, wanted)]
            if wanted and open_cards and not picked:
                # Gõ sai tên cột thì bot im lặng bỏ cả board, và im lặng ấy đọc
                # y hệt một board đã làm xong. Kể tên các cột đang thật sự có
                # để người đọc log sửa được ngay mà không phải mở ERP ra dò.
                log.warning(
                    "Cột nguồn %s không khớp thẻ đang mở nào của %s; đang có: %s.",
                    ", ".join(wanted),
                    project,
                    ", ".join(
                        sorted(
                            {str(task.get("status") or "").strip() or "(trống)" for task in open_cards}
                        )
                    ),
                )
            found.extend(picked)
        return found

    def resolve_bot_user(self, trees: Sequence[Dict[str, Any]] = ()) -> str:
        """Danh tính của chính bot, ưu tiên cách không phải ghi gì lên ERP.

        GraphQL không có field "tôi là ai", nên thứ tự là: cấu hình → sổ ghi →
        suy ra từ ``mine = 1`` của một bình luận bot từng đăng. Chỉ khi cả ba
        đều trắng mới cần dò bằng cách ghi (``probe_bot_user``), vì lượt dò đó
        để lại một bình luận trên thẻ của người khác dù chỉ trong chốc lát.
        """
        if self.config.bot_user:
            return self.config.bot_user
        if self.state.bot_user:
            return self.state.bot_user
        for tree in trees:
            for node in iter_tree_nodes(tree.get("root") or {}):
                for comment in node.get("comments") or []:
                    if not isinstance(comment, dict):
                        continue
                    candidates = [comment, *(comment.get("replies") or [])]
                    for item in candidates:
                        if isinstance(item, dict) and int(item.get("mine") or 0) == 1:
                            owner = str(item.get("owner") or "").strip()
                            if owner:
                                self.state.bot_user = owner
                                return owner
        return ""

    def probe_bot_user(self, task: str) -> str:
        """Hỏi ERP "tôi là ai" bằng một bình luận rồi xoá ngay.

        Cách cuối cùng, và cố ý gây tiếng động nhỏ nhất có thể: một bình luận
        mang dấu riêng, đọc ``owner`` ở đúng bản ghi có ``mine = 1``, rồi xoá.
        Đặt ``ERP_AGENT_BOT_USER`` là khỏi cần lượt này.
        """
        mark = f"{BOT_NOTE_MARK} nhận diện agent {int(time.time())}"
        self.client.add_comment(task, f"{mark} — bình luận kỹ thuật, sẽ tự xoá.")
        owner = ""
        comment_id = ""
        root = (self.client.task_full(task, depth=0) or {}).get("root") or {}
        for comment in root.get("comments") or []:
            if not isinstance(comment, dict) or mark not in plain_text(comment.get("content")):
                continue
            comment_id = str(comment.get("name") or "")
            owner = str(comment.get("owner") or "").strip()
            break
        if comment_id:
            try:
                self.client.delete_comment(task, comment_id)
            except AgentBotError as exc:
                log.warning("Không xoá được bình luận nhận diện trên %s: %s", task, exc)
        if owner:
            self.state.bot_user = owner
        return owner

    # ── dọn theo phiếu ─────────────────────────────────────────────────

    def janitor_pass(self, tree: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Áp 👍 giữ / 👎 xoá lên mọi ảnh bot đã đăng trong cây task này."""
        applied: List[Dict[str, Any]] = []
        if tree.get("truncated"):
            # Hai trần độc lập (số node, ngân sách hàng) có thể cắt cây; im
            # lặng bỏ qua phần bị cắt sẽ trông y hệt "không có gì để làm".
            log.warning(
                "taskFull cắt bớt cây của %s (node=%s/%s, row=%s/%s) — lượt này chưa quét hết.",
                ((tree.get("root") or {}).get("name")),
                tree.get("node_count"),
                tree.get("max_nodes"),
                tree.get("row_count"),
                tree.get("max_rows"),
            )
        for node in iter_tree_nodes(tree.get("root") or {}):
            task_id = str(node.get("name") or "").strip()
            if not task_id:
                continue
            for post in iter_review_posts(node):
                comment_id = str(post.get("name") or "").strip()
                if not comment_id or self.state.already_handled(comment_id):
                    continue
                decision = vote_decision(post)
                if decision == DECISION_PENDING:
                    continue
                outcome = self._apply_decision(task_id, post, decision)
                if outcome is not None:
                    applied.append(outcome)
        return applied

    def _apply_decision(self, task_id: str, post: Dict[str, Any], decision: str) -> Dict[str, Any] | None:
        comment_id = str(post.get("name") or "")
        label = self._post_label(post)
        record = {
            "task": task_id,
            "comment": comment_id,
            "decision": decision,
            "label": label,
            "like": int(post.get("like_count") or 0),
            "dislike": int(post.get("dislike_count") or 0),
        }
        if self.config.dry_run:
            record["dry_run"] = True
            log.info("[chạy khô] %s %s trên %s (%s)", decision, label, task_id, comment_id)
            return record

        # Quyết định cố ý **không** để lại ghi chú trên thẻ. Bot từng viết một
        # dòng "đã gỡ / đã giữ" cho mỗi ảnh, và trên thẻ nhiều ảnh thì đúng thứ
        # người duyệt phải cuộn qua lại là những dòng đó. Người duyệt vừa tự tay
        # bấm 👍/👎 nên đã biết mình quyết gì rồi; chỗ cần lưu vết là log của
        # app, không phải thẻ.
        if decision == DECISION_DELETE:
            try:
                self.client.delete_comment(task_id, comment_id)
            except AgentBotError as exc:
                log.warning("Không gỡ được %s khỏi %s: %s", label, task_id, exc)
                return None
            log.info(
                "Đã gỡ %s khỏi %s theo phiếu %s 👎 / %s 👍.",
                label,
                task_id,
                record["dislike"],
                record["like"],
            )
        else:
            log.info(
                "Giữ %s trên %s theo phiếu %s 👍 / %s 👎.",
                label,
                task_id,
                record["like"],
                record["dislike"],
            )

        self.state.record(comment_id, task_id, decision)
        return record

    @staticmethod
    def _post_label(post: Dict[str, Any]) -> str:
        for attachment in post.get("attachments") or []:
            if isinstance(attachment, dict):
                name = str(attachment.get("file_name") or "").strip()
                if name:
                    return f"ảnh {name}"
        text = plain_text(post.get("content"))
        return f"bình luận “{text[:40]}”" if text else "bình luận"

    # ── chạy việc ──────────────────────────────────────────────────────

    def inherit_pass(self, tree: Dict[str, Any], bot_user: str) -> List[Dict[str, Any]]:
        """Thẻ cha đã gắn bot thì mọi thẻ con cũng được gắn theo.

        Chọn agent ở ô "Người phụ trách" của thẻ cha là người dùng đã nói xong ý
        mình: cả cụm việc này là của bot. Thẻ con thì không tự có — kể cả thẻ
        vừa do phần nhận ảnh sinh ra — nên bot tự khâu lại, để thẻ con hiện
        đúng người phụ trách như thẻ cha thay vì trống trơn.

        Chỉ lan xuống, không bao giờ lan lên: gắn bot vào một thẻ con là cố ý
        chỉ đúng thẻ ấy, và tự tiện gắn ngược lên thẻ cha sẽ kéo theo cả những
        thẻ con khác mà người dùng không hề chọn.
        """
        root = tree.get("root") or {}
        if not bot_user or not task_has_agent(root, bot_user):
            return []
        attached: List[Dict[str, Any]] = []
        for node in iter_tree_nodes(root):
            if node is root or task_has_agent(node, bot_user):
                continue
            task_id = str(node.get("name") or "").strip()
            if not task_id:
                continue
            if self.config.dry_run:
                attached.append({"task": task_id, "dry_run": True})
                continue
            try:
                self.client.add_task_agent(task_id, bot_user)
            except AgentBotError as exc:
                log.warning("Không gắn được bot vào thẻ con %s: %s", task_id, exc)
                continue
            agents = node.get("agents")
            if not isinstance(agents, list):
                agents = []
                node["agents"] = agents
            agents.append({"bot_user": bot_user})
            attached.append({"task": task_id})
            log.info("Gắn bot vào thẻ con %s theo thẻ cha %s.", task_id, root.get("name"))
        return attached

    async def autorun_pass(self, tree: Dict[str, Any]) -> Dict[str, Any] | None:
        """Giao thẻ cha đã gắn agent cho hook chạy việc.

        Bot cố ý **không** tự quyết thẻ con nào cần chạy: ``enqueue_erp_idea_jobs``
        đã bỏ qua thẻ con đã có ảnh rồi, nên nhân đôi phép lọc đó ở đây chỉ tạo
        thêm một chỗ để hai bên lệch nhau.

        Thẻ chưa có con vẫn được giao nếu nó đang mang từ hai ảnh trở lên: ảnh
        đầu là ảnh sản phẩm, những ảnh sau là idea vừa thả vào và hook sẽ biến
        chúng thành thẻ con. Một thẻ chỉ có mỗi ảnh bìa thì không có gì để làm.
        """
        if not self.config.autorun or self.autorun_hook is None:
            return None
        root = tree.get("root") or {}
        task_id = str(root.get("name") or "").strip()
        if not task_id:
            return None
        images = count_card_images(root, tree.get(BOARD_ROW_KEY))
        if int(root.get("child_total") or 0) <= 0 and images < 2:
            return None
        if not self.state.autorun_is_cool(task_id, self.config.autorun_cooldown_seconds):
            return None
        if self.config.dry_run:
            return {"task": task_id, "dry_run": True}
        self.state.mark_autorun(task_id)
        try:
            outcome = await self.autorun_hook(task_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # hook là mã của app, lỗi của nó không được giết vòng lặp
            log.warning("Không chạy được việc của %s: %s", task_id, exc)
            return {"task": task_id, "error": str(exc)}
        return {"task": task_id, "result": outcome}

    async def listing_pass(self, tree: Dict[str, Any]) -> Dict[str, Any] | None:
        """Giao thẻ đã duyệt xong ảnh cho nửa Etsy đăng lên shop.

        Gọi sau ``janitor_pass`` của chính lượt này, vì phán quyết 👍/👎 vừa
        áp xong mới cho biết bộ ảnh đã chốt hay chưa.

        Mọi ngả rẽ ở đây đều trả về một dòng chứ không im lặng: thẻ bị bỏ qua
        âm thầm trông y hệt thẻ hỏng, mà người dùng thì vừa gắn agent vào nó.

        Sổ nguội dùng khoá riêng ``listing:<thẻ>``: một thẻ listing vẫn đi qua
        ``autorun_pass`` để có ảnh, nên hai đường không được giẫm lên dấu thời
        gian của nhau.
        """
        root = tree.get("root") or {}
        task_id = str(root.get("name") or "").strip()
        if not task_id:
            return None
        if self.state.already_listed(task_id):
            # Đăng lần hai là hai bản nháp trong shop cho cùng một sản phẩm.
            return None
        ready, missing = listing_readiness(root)
        if not ready:
            return {"task": task_id, "waiting": missing}
        if self.listing_hook is None:
            return {"task": task_id, "skipped": "chưa cấu hình ERP_LISTING_API_URL"}
        cooldown_key = f"listing:{task_id}"
        if not self.state.autorun_is_cool(cooldown_key, self.config.autorun_cooldown_seconds):
            return {"task": task_id, "skipped": "vừa giao xong, đang chờ nguội"}
        if self.config.dry_run:
            return {"task": task_id, "dry_run": True}
        self.state.mark_autorun(cooldown_key)
        try:
            outcome = await self.listing_hook(task_id, root)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # bản Listing tắt không được làm chết vòng quét
            log.warning("Không giao được thẻ listing %s: %s", task_id, exc)
            return {"task": task_id, "error": str(exc)}
        if isinstance(outcome, dict) and outcome.get("queue_task_id"):
            # Chỉ ghi sổ khi bên kia thật sự xếp hàng được. Một lượt bị từ chối
            # ("thẻ đã ở cột Done") phải còn đường quay lại nếu người dùng sửa.
            self.state.record_listing(task_id, outcome)
        return {"task": task_id, "result": outcome}

    # ── một lượt ───────────────────────────────────────────────────────

    def _is_mine(self, tree: Dict[str, Any], bot_user: str) -> bool:
        """Cây này có phải việc của bot không.

        Ở chế độ ``card`` thì phải gắn đích danh. Ở ``board`` thì thẻ đã lọt qua
        ``candidate_tasks`` rồi — hoặc vì gắn bot, hoặc vì là thẻ Idea của một
        dự án bot đang ở trong — nên kiểm lại lần nữa chỉ để loại đúng những thẻ
        gắn bot khác.
        """
        root = tree.get("root") or {}
        if self.config.scope == SCOPE_CARD:
            return task_has_agent(root, bot_user)
        agents = root.get("agents") or []
        return (
            task_has_agent(root, bot_user)
            if agents
            else is_idea_card(root, tree.get(BOARD_ROW_KEY))
        )

    async def run_once(self) -> Dict[str, Any]:
        """Quét một vòng. Không ném lỗi vì một dự án hỏng, chỉ bỏ qua nó."""
        if not self.config.enabled:
            return {"enabled": False, "reason": "chưa cấu hình ERP_AGENT_TOKEN"}

        projects = await asyncio.to_thread(self.scope_projects)
        if not projects:
            return {"enabled": True, "projects": [], "reason": "bot chưa được thêm vào dự án nào"}

        # Danh tính trước, để bước chọn thẻ biết thẻ nào gắn đích danh bot này
        # thay vì gắn một bot khác.
        bot_user = self.resolve_bot_user()
        candidates = await asyncio.to_thread(self.candidate_tasks, projects, bot_user)

        trees: List[Dict[str, Any]] = []
        for task in candidates:
            task_id = str(task.get("name") or "").strip()
            if not task_id:
                continue
            try:
                tree = await asyncio.to_thread(self.client.task_full, task_id, TASK_FULL_DEPTH)
            except AgentBotError as exc:
                log.warning("Không đọc được task %s: %s", task_id, exc)
                continue
            # Dòng của thẻ trên bảng biết số tệp treo thẳng trên thẻ; taskFull
            # thì không. Giữ nó lại để bước giao việc còn thấy ảnh vừa kéo vào.
            tree[BOARD_ROW_KEY] = task
            trees.append(tree)

        if not bot_user:
            bot_user = self.resolve_bot_user(trees)
        if not bot_user and candidates:
            bot_user = await asyncio.to_thread(
                self.probe_bot_user, str(candidates[0].get("name") or "")
            )
        if not bot_user:
            self.state.save()
            return {
                "enabled": True,
                "projects": projects,
                "tasks": [],
                "reason": "chưa xác định được danh tính bot; đặt ERP_AGENT_BOT_USER",
            }
        self.state.bot_user = bot_user

        mine = [tree for tree in trees if self._is_mine(tree, bot_user)]
        applied: List[Dict[str, Any]] = []
        queued: List[Dict[str, Any]] = []
        inherited: List[Dict[str, Any]] = []
        listing: List[Dict[str, Any]] = []
        deferred: List[str] = []
        ceiling = max(1, self.config.max_cards_per_scan)
        for tree in mine:
            # Lan xuống trước: thẻ con phải mang đúng người phụ trách của thẻ
            # cha, kể cả khi lượt này không còn suất chạy việc nào.
            inherited.extend(await asyncio.to_thread(self.inherit_pass, tree, bot_user))
            root = tree.get("root") or {}
            # Dọn phiếu cho mọi thẻ: nó rẻ, và trần dưới đây là trần của việc
            # tạo ảnh chứ không phải của việc đọc 👍/👎.
            applied.extend(await asyncio.to_thread(self.janitor_pass, tree))
            if is_listing_card(root):
                # Một agent, hai chặng của **cùng một thẻ**: làm ảnh ở đây, rồi
                # đăng bộ ảnh ấy lên Etsy. Chặng đăng chỉ chạy khi ảnh đã chốt,
                # nên thẻ mới gắn agent vẫn rơi xuống nửa làm ảnh bên dưới —
                # nếu nửa listing chiếm luôn thẻ thì sẽ không bao giờ có ảnh
                # nào để nó đăng.
                outcome = await self.listing_pass(tree)
                if outcome is not None:
                    listing.append(outcome)
                if outcome is None or "waiting" not in outcome:
                    continue
            if len(queued) >= ceiling:
                deferred.append(str(root.get("name") or ""))
                continue
            outcome = await self.autorun_pass(tree)
            if outcome is not None:
                queued.append(outcome)
        if deferred:
            # Nói ra chỗ bị cắt: im lặng dừng lại trông y hệt "board này không
            # còn thẻ nào để chạy".
            log.info(
                "Agent bot chạy %s thẻ trong lượt này; để lượt sau: %s.",
                len(queued),
                ", ".join(deferred),
            )

        self.state.save()
        summary = {
            "enabled": True,
            "bot_user": bot_user,
            "scope": self.config.scope,
            "projects": projects,
            "tasks": [str((tree.get("root") or {}).get("name") or "") for tree in mine],
            "applied": applied,
            "kept": sum(1 for item in applied if item["decision"] == DECISION_KEEP),
            "deleted": sum(1 for item in applied if item["decision"] == DECISION_DELETE),
            "autorun": queued,
            "inherited": inherited,
            "listing": listing,
            "dry_run": self.config.dry_run,
        }
        if listing:
            # Nói ra từng thẻ listing và nó đang đứng ở chặng nào: im lặng bỏ
            # qua trông y hệt thẻ hỏng.
            log.info(
                "Agent bot: %s thẻ listing — %s.",
                len(listing),
                "; ".join(
                    "{} {}".format(
                        item.get("task") or "",
                        item.get("waiting")
                        or item.get("skipped")
                        or item.get("error")
                        or ("đã giao" if item.get("result") else "chạy khô"),
                    )
                    for item in listing
                ),
            )
        if applied or queued or inherited:
            log.info(
                "Agent bot: %s thẻ, giữ %s, gỡ %s, chạy %s, gắn thêm %s thẻ con.",
                len(mine),
                summary["kept"],
                summary["deleted"],
                len(queued),
                len(inherited),
            )
        return summary

    async def run_forever(self, immediate: bool = False) -> None:
        """Vòng lặp nền. ``poll_seconds = 0`` là tắt hẳn.

        Mặc định ngủ trước rồi mới quét: khi chạy trong app, lượt đầu không nên
        tranh tài nguyên với lúc khởi động. Chạy tay bằng script thì ``immediate``
        cho kết quả ngay thay vì im lặng cả chu kỳ đầu.
        """
        interval = self.config.poll_seconds
        if not self.config.enabled or interval <= 0:
            return
        # Máy trung tâm chạy 24/7 không ai ngồi trước màn hình, nên phải có một
        # dòng nói rõ bot đã bật và đang đứng ở đâu. Các dòng còn lại chỉ hiện
        # khi bot thật sự làm gì; im lặng khi không có việc là đúng, nhưng im
        # lặng ngay từ lúc khởi động thì không phân biệt được với chết hẳn.
        log.info(
            "Agent bot bật: quét mỗi %ss, phạm vi %s%s, tự chạy %s%s.",
            interval,
            self.config.scope,
            # Cột nguồn là thứ dễ làm bot trông như chết nhất: gõ sai một chữ
            # là không thẻ nào lọt. Nói ngay ở dòng khởi động thì người đọc log
            # đối chiếu được với board mà không phải mở file cấu hình ra.
            f" (cột nguồn: {', '.join(self.config.source_statuses)})"
            if self.config.source_statuses
            else "",
            "bật" if self.config.autorun else "tắt",
            " (chạy khô)" if self.config.dry_run else "",
        )
        first = True
        while True:
            if not (first and immediate):
                await asyncio.sleep(interval)
            first = False
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except AgentBotError as exc:
                log.warning("Agent bot bỏ lượt này: %s", exc)
            except Exception as exc:
                log.exception("Agent bot gặp lỗi ngoài dự tính: %s", exc)


def build_agent_bot(
    config: AgentBotConfig | None = None,
    autorun_hook: AutorunHook | None = None,
    state_path: Path | None = None,
    listing_hook: ListingHook | None = None,
) -> AgentBot | None:
    """Dựng bot, hoặc ``None`` khi chưa cấu hình token."""
    resolved = config or AgentBotConfig.from_env()
    if not resolved.enabled:
        return None
    return AgentBot(
        resolved,
        state=AgentBotState.load(state_path),
        autorun_hook=autorun_hook,
        listing_hook=listing_hook,
    )
