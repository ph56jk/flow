#!/usr/bin/env python3
"""Agent điều phối — runner sửa code trên máy trung tâm.

Nó nhận yêu cầu từ Automation Center, hỏi model cách sửa, ghi file, chạy
test, rồi báo diff ngược lại để người có quyền duyệt.  Máy cá nhân không tham
gia bước nào.

Model được hỏi qua một trong hai đường: HTTP tới OpenAI bằng ``OPENAI_API_KEY``,
hoặc Codex CLI đã đăng nhập sẵn trên máy này.  Đường thứ hai là mặc định khi
không có khoá — nó bỏ được việc phải cất một khoá API trên máy trung tâm.
Dù đi đường nào, CLI cũng chỉ là **đường truyền chữ**: nó chạy với sandbox
``read-only`` và thư mục làm việc rỗng, nên thứ duy nhất ghi file vẫn là runner.

Ba thứ giữ cho việc này an toàn, và không thứ nào nằm trong lời nhắc gửi cho
ChatGPT — một mô hình ngôn ngữ có thể bị thuyết phục, một allowlist thì không:

1.  Phạm vi.  Center gửi kèm ``scope.allow_globs`` của đúng người gửi.  File
    nằm ngoài đó không được ghi, và Center kiểm lại lần nữa khi nhận báo cáo.
2.  Danh sách bảo vệ.  Bí mật, hạ tầng triển khai và chính phần phân quyền
    không bao giờ được ĐỌC gửi sang OpenAI, cũng không bao giờ được ghi.
3.  Nhánh riêng.  Mọi thay đổi nằm trên ``agent/<id>``; nhánh chính chỉ nhận
    sau khi có quyết định duyệt (hoặc phạm vi cho phép áp thẳng).

Repo mà runner đụng vào là một bản clone riêng (``AGENT_REPO_DIR``), không
phải bản đang chạy dịch vụ.  Việc triển khai bản đã merge vẫn là bước tay.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):  # Windows mặc định cp1252; log có tiếng Việt.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


CENTER_URL = os.environ.get("AUTOMATION_CENTER_URL", "https://automation.havigroup.llc").rstrip("/")
RUNNER_KEY = os.environ.get("AUTOMATION_RUNNER_KEY", "orchestrator-runner").strip()
RUNNER_SECRET = os.environ.get("AUTOMATION_RUNNER_SECRET", "").strip()
RUNNER_LABEL = os.environ.get("AUTOMATION_RUNNER_LABEL", "Agent điều phối (máy trung tâm)").strip()
POLL_SECONDS = max(1.0, float(os.environ.get("AUTOMATION_RUNNER_POLL_SECONDS", "3")))
ACCESS_CLIENT_ID = os.environ.get("CF_ACCESS_CLIENT_ID", "").strip()
ACCESS_CLIENT_SECRET = os.environ.get("CF_ACCESS_CLIENT_SECRET", "").strip()

REPO_DIR = Path(os.environ.get("AGENT_REPO_DIR", "")).expanduser()
BASE_BRANCH = os.environ.get("AGENT_BASE_BRANCH", "main").strip() or "main"
PUSH_AFTER_MERGE = os.environ.get("AGENT_PUSH_REMOTE", "").strip().lower() in {"1", "true", "yes"}
TEST_COMMAND = os.environ.get("AGENT_TEST_COMMAND", "").strip()
TEST_TIMEOUT = max(30, int(os.environ.get("AGENT_TEST_TIMEOUT_SECONDS", "900")))
# Trần độ dài diff gửi lên Center.  Phải khớp trần bên Worker: bên đó cắt lần
# nữa, và nếu bên đó cắt trước thì cờ "đã cắt" runner gửi lên là cờ sai.
DIFF_LIMIT = 60000

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5").strip()
OPENAI_TIMEOUT = max(30, int(os.environ.get("OPENAI_TIMEOUT_SECONDS", "300")))

# auto = có OPENAI_API_KEY thì đi HTTP, không thì dùng Codex CLI đã đăng nhập.
# Đặt thẳng "codex" hay "openai" khi muốn hỏng to thay vì âm thầm đổi đường.
MODEL_PROVIDER = os.environ.get("AGENT_MODEL_PROVIDER", "auto").strip().lower() or "auto"
# Để trống thì tìm "codex" trong PATH.  Scheduled Task chạy kiểu S4U có PATH
# hẹp hơn PATH của phiên đăng nhập, nên trỏ tuyệt đối là chắc chắn hơn.
CODEX_BIN = os.environ.get("CODEX_BIN", "").strip()
# Để trống thì dùng model mặc định của codex.  Đừng nhét OPENAI_MODEL vào đây:
# tên model của API và tên model của codex không cùng một bộ.
CODEX_MODEL = os.environ.get("CODEX_MODEL", "").strip()

RUNNER_VERSION = "1.0.0"
# Cloudflare WAF chặn User-Agent mặc định của urllib (lỗi 1010).
USER_AGENT = f"HaviGroupOrchestratorRunner/{RUNNER_VERSION} (+{RUNNER_KEY})"

# Bản sao cứng của danh sách bảo vệ phía Worker.  Trùng lặp là cố ý: nếu
# Center bị cấu hình sai, runner vẫn không đọc và không ghi những file này.
PROTECTED_GLOBS = (
    ".env", ".env.*", "*/.env", "*/.env.*", "*.env",
    "*.pem", "*.key", "*credentials*", "*secret*",
    ".gitignore", ".github/*",
    "wrangler.jsonc", "wrangler.toml", "*/wrangler.jsonc", "*/wrangler.toml",
    "automation_center/src/worker.js",
    "automation_center/migrations/*",
    "automation_center/runner/*",
    "automation_center/scripts/*",
)

MAX_CONTEXT_FILES = 400
MAX_READ_BYTES = 120_000
MAX_WRITE_BYTES = 400_000
MAX_ROUNDS = 4


# ─── Nói chuyện với Automation Center ───────────────────────────────────────

def request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None,
                 headers: dict[str, str] | None = None, timeout: int = 60) -> dict[str, Any]:
    all_headers = {"accept": "application/json", "user-agent": USER_AGENT, **(headers or {})}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        all_headers["content-type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=all_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            content_type = str(response.headers.get("content-type") or "")
            if "json" not in content_type.lower():
                final_url = response.geturl()
                if "cloudflareaccess.com" in final_url or "/cdn-cgi/access/" in final_url:
                    raise RuntimeError(
                        "Cloudflare Access chặn runner: thiếu hoặc sai CF_ACCESS_CLIENT_ID/"
                        "CF_ACCESS_CLIENT_SECRET, hoặc Service Token chưa gắn vào policy."
                    )
                raise RuntimeError(f"Phản hồi không phải JSON (content-type: {content_type or 'không rõ'}).")
            return json.loads(body or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:600]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Không kết nối được {url}: {exc.reason}") from exc


def center_request(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"x-automation-runner-secret": RUNNER_SECRET}
    if ACCESS_CLIENT_ID and ACCESS_CLIENT_SECRET:
        headers["CF-Access-Client-Id"] = ACCESS_CLIENT_ID
        headers["CF-Access-Client-Secret"] = ACCESS_CLIENT_SECRET
    return request_json(f"{CENTER_URL}{path}", method=method, payload=payload, headers=headers)


def heartbeat() -> None:
    center_request("/api/runner/heartbeat", method="POST", payload={
        "runner_key": RUNNER_KEY, "label": RUNNER_LABEL, "version": RUNNER_VERSION,
    })


def report(request_id: str, status: str, **extra: Any) -> dict[str, Any]:
    return center_request(f"/api/runner/code/{urllib.parse.quote(request_id)}", method="POST", payload={
        "runner_key": RUNNER_KEY, "status": status, **extra,
    })


def is_cancelled(request_id: str) -> bool:
    state = center_request(
        f"/api/runner/code/{urllib.parse.quote(request_id)}?runner_key={urllib.parse.quote(RUNNER_KEY)}"
    )
    return str(state.get("request", {}).get("status") or "") == "cancelled"


# ─── Git ────────────────────────────────────────────────────────────────────

def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} hỏng: {(result.stderr or result.stdout).strip()[:600]}")
    return result.stdout


def repo_prefix() -> str:
    """Chỗ REPO_DIR nằm, tính từ gốc git — rỗng nếu REPO_DIR chính là gốc."""
    return git("rev-parse", "--show-prefix").strip()


def require_repo_root() -> None:
    """REPO_DIR phải là *gốc* git, không được là một thư mục con.

    Hai lệnh git mà runner này dùng đếm đường dẫn theo hai hệ quy chiếu khác
    nhau — đo chứ không đoán:

        git ls-files                 → tính từ THƯ MỤC ĐANG ĐỨNG
        git diff --cached --numstat  → tính từ GỐC GIT

    REPO_DIR là gốc thì hai hệ trùng nhau và không ai để ý.  REPO_DIR là thư
    mục con (clone thành ``agent-workspace/flow-v2`` chẳng hạn) thì cùng một
    file mang hai tên khác nhau ở hai chỗ trong cùng một tiến trình:
    ``repo_files`` gọi nó là ``automation_center/src/worker.js`` còn
    ``staged_stats`` gọi nó là ``flow-v2/automation_center/src/worker.js``.

    Chỗ chết người là bốn mục trong ``PROTECTED_GLOBS`` —
    ``automation_center/src/worker.js``, ``automation_center/migrations/**``,
    ``runner/**``, ``scripts/**`` — neo ở gốc repo, không mở đầu bằng ``**/``.
    Tên thứ hai không khớp mục nào, nên lớp bảo vệ biến mất **im lặng**: không
    lỗi, không cảnh báo, worker.js và migrations thành file sửa tự do.  Đúng
    thứ PRD §0 cấm.

    Và nó không lộ ra trong một dàn test đường dẫn thường: mọi mục còn lại đều
    có anh em ``**/`` (``**/.env``, ``**/wrangler.jsonc``, ``**/*credentials*``)
    che mất khác biệt ở mức gốc — ``flow-v2/.env`` vẫn được bảo vệ.  Phải lấy
    đúng worker.js hay migrations mới thấy đỏ.

    Thà không khởi động còn hơn chạy mà không còn lớp bảo vệ.
    """
    if not REPO_DIR or not (REPO_DIR / ".git").exists():
        raise RuntimeError(f"AGENT_REPO_DIR không phải một repo git: {REPO_DIR or '(chưa đặt)'}")
    prefix = repo_prefix()
    if prefix:
        raise RuntimeError(
            f"AGENT_REPO_DIR ({REPO_DIR}) là thư mục con '{prefix.rstrip('/')}' của một "
            "repo git lớn hơn. Đường dẫn git khi ấy mang thêm tiền tố đó và không còn "
            "khớp PROTECTED_GLOBS, tức worker.js cùng migrations mất lớp bảo vệ mà "
            "không báo gì. Hãy trỏ AGENT_REPO_DIR vào đúng gốc repo."
        )


def require_clean_repo() -> None:
    require_repo_root()
    if git("status", "--porcelain").strip():
        raise RuntimeError(
            "Bản làm việc của agent còn thay đổi chưa dọn. Hãy vào máy trung tâm "
            f"dọn {REPO_DIR} trước khi agent chạy tiếp."
        )


# ─── Phạm vi ────────────────────────────────────────────────────────────────

def is_protected(path: str) -> bool:
    # Không phân biệt hoa thường, giống Worker: máy này chạy Windows, ở đó
    # "Secrets.json" và "secrets.json" là cùng một file.  fnmatch.fnmatch đã tự
    # hạ hoa thường trên Windows nhưng không làm thế trên máy dev, nên hạ tay
    # để hai nơi cho cùng một kết quả.
    lowered = path.lower()
    return any(fnmatch.fnmatchcase(lowered, pattern)
               or fnmatch.fnmatchcase(f"x/{lowered}", pattern)
               for pattern in PROTECTED_GLOBS)


def glob_to_regex(glob: str) -> re.Pattern[str]:
    """Cùng ngữ nghĩa với Worker: ``**`` đi qua dấu /, ``*`` thì không."""
    pattern = ["^"]
    index = 0
    while index < len(glob):
        char = glob[index]
        if char == "*":
            if glob[index + 1:index + 2] == "*":
                if glob[index + 2:index + 3] == "/":
                    pattern.append("(?:.*/)?")
                    index += 3
                    continue
                pattern.append(".*")
                index += 2
                continue
            pattern.append("[^/]*")
        elif char == "?":
            pattern.append("[^/]")
        else:
            pattern.append(re.escape(char))
        index += 1
    pattern.append("$")
    return re.compile("".join(pattern))


def normalise_path(value: Any) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw or len(raw) > 400 or raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        return ""
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return ""
    # Giống Worker: loại ký tự điều khiển.  Một đường dẫn có \n vẫn đi lọt qua
    # fnmatch (fnmatch dịch sang chế độ DOTALL) và làm hỏng việc đọc
    # ``git diff --numstat`` theo dòng, nên phải chặn ngay từ đây thay vì trông
    # vào việc Worker sẽ bắt được sau khi file đã bị ghi.
    if re.search(r"[\0\n\r]", raw):
        return ""
    return "/".join(parts)


def in_scope(path: str, allow_globs: list[str]) -> bool:
    return any(glob_to_regex(glob).match(path) for glob in allow_globs)


def repo_files() -> list[str]:
    """Chỉ file git đang theo dõi — bỏ qua build, venv và mọi thứ đã ignore."""
    return [line for line in git("ls-files").splitlines() if line.strip()]


def read_repo_file(path: str) -> str:
    target = REPO_DIR / path
    if not target.is_file():
        return f"(không có file {path})"
    data = target.read_bytes()[:MAX_READ_BYTES]
    return data.decode("utf-8", "replace")


# ─── ChatGPT ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Bạn là agent điều phối của HaviGroup, sửa code trong repo flow-v2 theo yêu cầu của nhân viên.

Bạn LUÔN trả lời bằng một đối tượng JSON duy nhất, không kèm chữ nào khác, theo một trong bốn dạng:

1. Cần đọc thêm file:
   {"action": "read", "paths": ["duong/dan/file.py", ...]}
2. Yêu cầu chỉ là câu hỏi, không cần sửa file:
   {"action": "answer", "summary": "câu trả lời bằng tiếng Việt"}
3. Đã biết cần sửa gì:
   {"action": "edit", "summary": "giải thích ngắn bằng tiếng Việt cho người không đọc diff",
    "files": [{"path": "duong/dan/file.py", "content": "TOÀN BỘ nội dung mới của file"}]}
4. Yêu cầu là điều khiển một agent/bot khác, không phải sửa code:
   {"action": "bot", "summary": "nói rõ bằng tiếng Việt bạn sắp làm gì",
    "commands": [{"bot_id": "id-cua-bot", "command": "run|pause|resume",
                  "prompt": "chỉ khi command=run", "count": 1, "aspect": "landscape"}]}

Quy tắc bắt buộc:
- "content" phải là toàn bộ nội dung file sau khi sửa, không phải diff, không dùng "..." để lược bớt.
- Chỉ được ghi vào những đường dẫn nằm trong danh sách phạm vi được cấp ở dưới. Ghi ra ngoài sẽ bị chặn và yêu cầu coi như thất bại.
- Tôn trọng giới hạn số file và số dòng được nêu. Nếu yêu cầu không thể làm trong giới hạn đó, dùng "answer" để nói rõ vì sao.
- Viết code khớp với phong cách xung quanh: cách đặt tên, mật độ chú thích, thành ngữ của file đang sửa.
- Nếu yêu cầu mơ hồ tới mức sửa sai sẽ gây hại, dùng "answer" để hỏi lại.
- Đừng bịa nội dung file bạn chưa đọc. Hãy "read" trước.
- Chỉ dùng "bot" khi danh sách bot ở dưới có mặt và yêu cầu đúng là chạy/dừng/tiếp tục một bot. "bot_id" phải lấy đúng từ danh sách đó, không được bịa.
- Một yêu cầu hoặc là sửa code, hoặc là điều khiển bot — đừng gộp cả hai vào một lượt."""


def call_chatgpt(messages: list[dict[str, str]]) -> dict[str, Any]:
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    body = request_json(
        f"{OPENAI_BASE_URL}/chat/completions",
        method="POST",
        payload=payload,
        headers={"authorization": f"Bearer {OPENAI_API_KEY}"},
        timeout=OPENAI_TIMEOUT,
    )
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("ChatGPT không trả về nội dung nào.")
    content = str(choices[0].get("message", {}).get("content") or "").strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ChatGPT trả về thứ không phải JSON: {content[:300]}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("ChatGPT trả về JSON nhưng không phải một đối tượng.")
    return parsed


# ─── Hỏi model qua Codex CLI ────────────────────────────────────────────────

# Structured output đòi mọi khoá đều nằm trong "required", nên khoá không dùng
# tới ở một action được khai nullable thay vì bỏ đi.  Bốn action phải khớp với
# SYSTEM_PROMPT ở trên: thiếu một cái nghĩa là model không nói ra được nó, và
# nhánh xử lý tương ứng trong plan_change() thành mã chết mà không ai hay.
CODEX_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["action", "summary", "paths", "files", "commands"],
    "properties": {
        "action": {"type": "string", "enum": ["read", "answer", "edit", "bot"]},
        "summary": {"type": ["string", "null"]},
        "paths": {"type": ["array", "null"], "items": {"type": "string"}},
        "files": {
            "type": ["array", "null"],
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["path", "content"],
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        },
        "commands": {
            "type": ["array", "null"],
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["bot_id", "command", "prompt", "count", "aspect"],
                "properties": {
                    "bot_id": {"type": "string"},
                    "command": {"type": "string", "enum": ["run", "pause", "resume"]},
                    "prompt": {"type": ["string", "null"]},
                    "count": {"type": ["integer", "null"]},
                    "aspect": {"type": ["string", "null"]},
                },
            },
        },
    },
}

NHAN_VAI = {"system": "[Hệ thống]", "user": "[Người dùng]", "assistant": "[Bạn đã trả lời]"}

# Codex chạy với sandbox read-only, và trên Windows lệnh shell trong sandbox ấy
# chết ngay lúc khởi tạo tiến trình (đo 2026-08-26: mã -1073741502).  Model
# không biết vậy nên sẽ thử, thử lại, và đốt hết timeout — cùng lần đo đó một
# lượt để nó tự loay hoay chạy quá 5 phút mà không ra gì.  Nói thẳng rẻ hơn.
NHAC_KHONG_CONG_CU = (
    "Bạn không có công cụ nào dùng được ở đây: không shell, không đọc file, không mạng. "
    "Đừng thử chạy lệnh — lệnh sẽ chết và bạn chỉ mất thời gian. "
    "Mọi thứ cần biết đã nằm trong lời nhắc này; muốn xem thêm file thì trả về "
    'action "read", phía gọi sẽ đọc hộ và gửi lại ở lượt sau. '
    "Trả lời bằng đúng một đối tượng JSON theo lược đồ đã cho, không kèm lời dẫn."
)


def tim_codex(duong_dan: str = "") -> str | None:
    if duong_dan:
        return duong_dan if Path(duong_dan).exists() else None
    return shutil.which("codex")


def chon_nha_cung_cap(cai_dat: str, api_key: str, codex: str | None) -> str:
    """Chốt đường gọi model, và hỏng to ngay nếu không có đường nào.

    Chọn bừa ở đây nghĩa là runner khởi động bình thường rồi mới hỏng ở yêu cầu
    đầu tiên của một người thật.
    """
    cai_dat = (cai_dat or "auto").strip().lower() or "auto"
    if cai_dat == "openai":
        if not api_key:
            raise RuntimeError("AGENT_MODEL_PROVIDER=openai nhưng OPENAI_API_KEY trống.")
        return "openai"
    if cai_dat == "codex":
        if not codex:
            raise RuntimeError(
                "AGENT_MODEL_PROVIDER=codex nhưng không tìm thấy codex CLI; "
                "đặt CODEX_BIN trỏ tới đường dẫn tuyệt đối của nó.")
        return "codex"
    if cai_dat != "auto":
        raise RuntimeError(f"AGENT_MODEL_PROVIDER không hiểu được: {cai_dat}")
    if api_key:
        return "openai"
    if codex:
        return "codex"
    raise RuntimeError(
        "Không gọi được model: OPENAI_API_KEY trống và cũng không tìm thấy codex CLI.")


def codex_argv(binary: str, *, work_dir: Path, schema_path: Path, out_path: Path,
               model: str = "") -> list[str]:
    """Cờ dòng lệnh cho một lượt hỏi codex.

    ``--sandbox read-only`` không phải cho đẹp: nó là thứ giữ cho codex chỉ là
    đường truyền chữ.  Đổi nó thành ``workspace-write`` — hoặc thêm ``--add-dir``,
    ``--approve-for-me``, một cờ ``--dangerously-*`` — là đã lặng lẽ cho model một
    đường ghi file không đi qua ``in_scope()`` và ``is_protected()``.
    """
    argv = [
        binary, "exec",
        "--sandbox", "read-only",
        "--cd", str(work_dir),
        "--skip-git-repo-check",
        # Không để lại bản sao lời nhắc (có nội dung file của repo) trong ~/.codex.
        "--ephemeral",
        # config.toml của người dùng không được đổi sandbox, model hay hook của
        # một tiến trình chạy không người trông.  Auth vẫn lấy từ CODEX_HOME.
        "--ignore-user-config",
        "--color", "never",
        "--output-schema", str(schema_path),
        "--output-last-message", str(out_path),
    ]
    if model:
        argv += ["--model", model]
    # Lời nhắc đọc từ stdin: vòng "read" gửi lại cả lịch sử mỗi lượt, mà dòng
    # lệnh Windows cắt ở ~32k ký tự và agent sẽ lặng lẽ mất ngữ cảnh.
    argv.append("-")
    return argv


def gop_loi_nhac(messages: list[dict[str, str]]) -> str:
    khuc = [
        f"{NHAN_VAI.get(m.get('role'), m.get('role'))}\n{m.get('content') or ''}"
        for m in messages
    ]
    khuc.append(f"[Hệ thống]\n{NHAC_KHONG_CONG_CU}")
    return "\n\n".join(khuc)


def doc_ket_qua_codex(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise RuntimeError("Codex không trả về nội dung nào.")
    ung_vien = [raw]
    # --output-schema thường chặn được, nhưng model vẫn có lúc bọc JSON trong
    # ```json … ``` hoặc kẹp nó giữa hai câu dẫn.
    rao = re.search(r"```(?:json)?\s*(.+?)\s*```", raw, re.DOTALL)
    if rao:
        ung_vien.insert(0, rao.group(1))
    dau, cuoi = raw.find("{"), raw.rfind("}")
    if dau >= 0 and cuoi > dau:
        ung_vien.append(raw[dau:cuoi + 1])
    for manh in ung_vien:
        try:
            parsed = json.loads(manh)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError(f"Codex trả về thứ không phải JSON: {raw[:300]}")


def call_codex(messages: list[dict[str, str]], *, chay=None) -> dict[str, Any]:
    binary = tim_codex(CODEX_BIN)
    if not binary:
        raise RuntimeError("Không tìm thấy codex CLI; đặt CODEX_BIN nếu nó không nằm trong PATH.")
    chay = chay or subprocess.run
    # Thư mục làm việc RỖNG, và cố tình không phải AGENT_REPO_DIR: codex chỉ
    # được thấy những gì runner đã lọc qua is_protected() rồi đưa vào lời nhắc.
    # Trỏ nó thẳng vào bản repo là mở một đường đọc không ai kiểm.
    tam = Path(tempfile.mkdtemp(prefix="agent-codex-"))
    try:
        schema_path = tam / "luoc-do.json"
        out_path = tam / "tra-loi.json"
        schema_path.write_text(json.dumps(CODEX_OUTPUT_SCHEMA), encoding="utf-8")
        argv = codex_argv(binary, work_dir=tam, schema_path=schema_path,
                          out_path=out_path, model=CODEX_MODEL)
        try:
            ket_qua = chay(
                argv, input=gop_loi_nhac(messages), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=OPENAI_TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Codex CLI quá {OPENAI_TIMEOUT}s chưa trả lời (OPENAI_TIMEOUT_SECONDS)."
            ) from exc
        if ket_qua.returncode != 0:
            loi = (ket_qua.stderr or ket_qua.stdout or "").strip()[-1500:]
            raise RuntimeError(
                f"Codex CLI thoát với mã {ket_qua.returncode}: {loi or 'không có thông báo'}")
        if not out_path.exists():
            raise RuntimeError("Codex CLI chạy xong nhưng không ghi câu trả lời cuối.")
        return doc_ket_qua_codex(out_path.read_text(encoding="utf-8", errors="replace"))
    finally:
        shutil.rmtree(tam, ignore_errors=True)


def call_model(messages: list[dict[str, str]]) -> dict[str, Any]:
    if chon_nha_cung_cap(MODEL_PROVIDER, OPENAI_API_KEY, tim_codex(CODEX_BIN)) == "codex":
        return call_codex(messages)
    return call_chatgpt(messages)


def build_context(request: dict[str, Any], allow_globs: list[str], scope: dict[str, Any]) -> str:
    tracked = repo_files()
    editable = [path for path in tracked if in_scope(path, allow_globs) and not is_protected(path)]
    listing = editable[:MAX_CONTEXT_FILES]
    history_lines = []
    for message in request.get("history") or []:
        who = {"user": "Người dùng", "agent": "Agent", "system": "Hệ thống"}.get(message.get("kind"), "?")
        history_lines.append(f"[{who}] {str(message.get('content') or '')[:1500]}")
    return "\n".join([
        f"Người gửi: {request.get('requested_by')} (vai trò {request.get('requested_role')})",
        f"Phạm vi được cấp: {', '.join(allow_globs)}",
        f"Giới hạn: tối đa {scope.get('max_files')} file, {scope.get('max_lines')} dòng thay đổi.",
        "",
        f"File bạn được phép sửa ({len(editable)} file, liệt kê {len(listing)}):",
        *(f"  {path}" for path in listing),
        "" if len(editable) <= len(listing) else f"  … và {len(editable) - len(listing)} file nữa.",
        "",
        "Trao đổi trong luồng:",
        *history_lines,
        "",
        f"Yêu cầu cần xử lý: {request.get('instruction')}",
        "",
        *bot_context_lines(request),
    ])


def bot_context_lines(request: dict[str, Any]) -> list[str]:
    """Model chỉ thấy bot khi Center nói người gửi có quyền điều khiển bot.

    Không thấy thì không gọi tên được, và kể cả có bịa ra một bot_id thì Center
    vẫn kiểm quyền lần nữa lúc thực thi.
    """
    bots = request.get("bots") or []
    if not request.get("may_control_bots") or not bots:
        return ["Người gửi không có quyền điều khiển bot, nên đừng dùng action \"bot\"."]
    lines = ["Các bot trong chương trình này (dùng cho action \"bot\"):"]
    for bot in bots:
        lines.append(
            f"  bot_id={bot.get('id')} · {bot.get('name')} · đang {bot.get('status')}"
        )
    return lines


def plan_change(request: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    """Hỏi model tới khi nó chốt "edit", "answer" hay "bot"; tối đa MAX_ROUNDS lượt."""
    allow_globs = [glob for glob in (scope.get("allow_globs") or []) if glob]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_context(request, allow_globs, scope)},
    ]
    for _ in range(MAX_ROUNDS):
        reply = call_model(messages)
        action = str(reply.get("action") or "").lower()
        if action in {"answer", "edit", "bot"}:
            return reply
        if action != "read":
            raise RuntimeError(f"Model trả về action lạ: {action or '(trống)'}")
        wanted = [normalise_path(path) for path in (reply.get("paths") or [])][:12]
        chunks = []
        for path in wanted:
            if not path:
                continue
            # Đọc rộng hơn quyền ghi là có chủ ý — agent cần hiểu chỗ xung
            # quanh mới sửa đúng — nhưng file được bảo vệ thì không rời máy.
            if is_protected(path):
                chunks.append(f"### {path}\n(file được bảo vệ, không gửi nội dung)")
                continue
            chunks.append(f"### {path}\n```\n{read_repo_file(path)}\n```")
        messages.append({"role": "assistant", "content": json.dumps(reply, ensure_ascii=False)})
        messages.append({"role": "user", "content": "\n\n".join(chunks) or "(không đọc được file nào)"})
    raise RuntimeError("Model chỉ đòi đọc file mà không đưa ra thay đổi nào sau nhiều lượt.")


# ─── Thực thi ───────────────────────────────────────────────────────────────

def run_tests() -> tuple[bool, str]:
    if not TEST_COMMAND:
        return False, "Chưa cấu hình AGENT_TEST_COMMAND nên không có test nào chạy; thay đổi luôn cần người duyệt."
    try:
        result = subprocess.run(
            TEST_COMMAND, cwd=REPO_DIR, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TEST_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, f"Test quá {TEST_TIMEOUT}s nên bị dừng."
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    return result.returncode == 0, output[-6000:] or "(test không in ra gì)"


def write_files(entries: list[dict[str, Any]], allow_globs: list[str], max_files: int) -> list[str]:
    if len(entries) > max_files:
        raise RuntimeError(f"Agent muốn sửa {len(entries)} file, vượt mức {max_files} của phạm vi.")
    written = []
    for entry in entries:
        path = normalise_path(entry.get("path"))
        if not path:
            raise RuntimeError(f"Đường dẫn không hợp lệ: {entry.get('path')!r}")
        if is_protected(path):
            raise RuntimeError(f"{path} nằm trong danh sách bảo vệ, agent không được ghi.")
        if not in_scope(path, allow_globs):
            raise RuntimeError(f"{path} nằm ngoài phạm vi được cấp.")
        content = entry.get("content")
        if not isinstance(content, str):
            raise RuntimeError(f"Nội dung mới của {path} không phải văn bản.")
        if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
            raise RuntimeError(f"Nội dung mới của {path} quá lớn.")
        target = REPO_DIR / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def staged_stats() -> tuple[list[str], int, str]:
    # ``--numstat`` đếm từ gốc git, không từ thư mục đang đứng, nên quy về khung
    # của repo trước khi trả ra: mọi thứ phía sau — ``is_protected``, báo cáo lên
    # Center — đều nói bằng khung repo.  ``require_repo_root`` khiến tiền tố này
    # luôn rỗng trên máy cấu hình đúng; giữ bước quy đổi để nếu ngày nào đó cái
    # chốt kia bị nới ra thì đường dẫn vẫn nằm trong đúng một khung.
    prefix = repo_prefix()
    paths, lines = [], 0
    for row in git("diff", "--cached", "--numstat").splitlines():
        parts = row.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        if prefix:
            if not path.startswith(prefix):
                raise RuntimeError(
                    f"File {path} nằm ngoài {REPO_DIR}; runner không nhận thay đổi "
                    "ở ngoài repo của chính nó."
                )
            path = path[len(prefix):]
        paths.append(path)
        for value in (added, deleted):
            if value.isdigit():
                lines += int(value)
    # Trả diff đầy đủ.  Cắt ở đây là vứt mất thông tin "đã cắt" ngay tại chỗ
    # duy nhất còn biết điều đó — sau bước này không ai suy ngược ra được nữa.
    return paths, lines, git("diff", "--cached")


def handle_request(request: dict[str, Any]) -> None:
    request_id = str(request["id"])
    scope = request.get("scope") or {}
    allow_globs = [glob for glob in (scope.get("allow_globs") or []) if glob]
    if not allow_globs:
        report(request_id, "failed", error="Yêu cầu không kèm phạm vi nào nên bị bỏ qua.")
        return

    branch = f"agent/{request_id[:12]}"
    plan = plan_change(request, scope)
    action = str(plan.get("action") or "").lower()

    if action == "answer":
        report(request_id, "answered", plan_summary=str(plan.get("summary") or "").strip())
        return

    if action == "bot":
        # Điều khiển bot không sinh diff nên không chạm git: runner chỉ chuyển
        # lệnh, còn quyền thì Center kiểm lại bằng đúng lõi mà nút bấm trên web
        # dùng.  Không tự lọc theo danh sách bot ở đây — lọc hai nơi thì một
        # ngày nào đó hai nơi sẽ khác nhau, và bên nới hơn sẽ là bên có hiệu lực.
        commands = plan.get("commands")
        summary = str(plan.get("summary") or "").strip() or "Agent điều khiển bot."
        if not isinstance(commands, list) or not commands:
            report(request_id, "failed", plan_summary=summary,
                   error="Agent nói sẽ điều khiển bot nhưng không đưa ra lệnh nào.")
            return
        report(request_id, "bot_action", plan_summary=summary, bot_commands=commands[:5])
        return

    summary = str(plan.get("summary") or "").strip() or "Agent không mô tả thay đổi."
    entries = plan.get("files")
    if not isinstance(entries, list) or not entries:
        report(request_id, "failed", plan_summary=summary, error="Agent nói sẽ sửa nhưng không đưa ra file nào.")
        return

    # Chỉ đòi repo sạch khi sắp thật sự ghi file.  Trả lời câu hỏi hay dừng một
    # bot không nên bị chặn vì bản làm việc còn dở.
    require_clean_repo()
    git("checkout", "-B", branch, BASE_BRANCH)
    try:
        written = write_files(entries, allow_globs, int(scope.get("max_files") or 1))
        git("add", "--", *written)
        paths, lines, full_diff = staged_stats()
        if not paths:
            git("checkout", BASE_BRANCH)
            report(request_id, "answered", plan_summary=f"{summary}\n\n(Không có gì thay đổi so với bản hiện tại.)")
            return
        max_lines = int(scope.get("max_lines") or 1)
        if lines > max_lines:
            raise RuntimeError(f"Thay đổi {lines} dòng, vượt mức {max_lines} của phạm vi.")
        if is_cancelled(request_id):
            raise RuntimeError("Người gửi đã rút lại yêu cầu trước khi test chạy xong.")
        passed, output = run_tests()
        diff_text = full_diff[:DIFF_LIMIT]
        diff_truncated = 1 if len(full_diff) > DIFF_LIMIT else 0
        git("commit", "--no-verify", "-m", f"agent: {summary[:70]}\n\nYêu cầu {request_id} · {request.get('requested_by')}")
        commit = git("rev-parse", "HEAD").strip()
    except Exception as exc:
        # Nhánh agent bị bỏ dở; dọn sạch để lượt sau không gặp repo bẩn.
        git("reset", "--hard", check=False)
        git("clean", "-fd", check=False)
        git("checkout", BASE_BRANCH, check=False)
        git("branch", "-D", branch, check=False)
        report(request_id, "failed", plan_summary=summary, error=str(exc)[:2000])
        return

    git("checkout", BASE_BRANCH)
    response = report(
        request_id, "awaiting_approval",
        plan_summary=summary,
        files=[{"path": path} for path in paths],
        lines_changed=lines,
        diff_text=diff_text,
        # Cờ đi kèm diff, không để Worker đoán: thứ gửi đi đã cắt sẵn nên bên
        # kia đo bao nhiêu cũng chỉ thấy một diff vừa khít trần.
        diff_truncated=diff_truncated,
        test_output=output,
        tests_passed=passed,
        branch=branch,
    )
    if response.get("blocked"):
        git("branch", "-D", branch, check=False)
        return
    print(f"[{request_id}] {len(paths)} file, {lines} dòng, test {'xanh' if passed else 'chưa xanh'} → {response.get('status')} (commit {commit[:8]})")


def apply_approved(request: dict[str, Any]) -> None:
    request_id = str(request["id"])
    branch = str(request.get("branch") or "").strip()
    if not branch:
        report(request_id, "failed", error="Yêu cầu đã được duyệt nhưng không có nhánh nào để áp.")
        return
    report(request_id, "applying")
    try:
        require_clean_repo()
        git("checkout", BASE_BRANCH)
        git("merge", "--no-edit", branch)
        commit = git("rev-parse", "HEAD").strip()
        if PUSH_AFTER_MERGE:
            git("push", "origin", BASE_BRANCH)
    except Exception as exc:
        git("merge", "--abort", check=False)
        git("checkout", BASE_BRANCH, check=False)
        report(request_id, "failed", error=f"Không merge được nhánh {branch}: {exc}"[:2000])
        return
    # Nhánh đã merge không còn nghĩa gì.  Để lại thì mỗi lượt bồi thêm một
    # nhánh vào ``git branch`` của máy trung tâm, và ngày nào 12 ký tự đầu của
    # một id trùng lại thì ``checkout -B`` ở lượt sau ghi đè im lặng lên nhánh
    # cũ.  ``check=False``: không xoá được cũng không được phép biến một lần
    # merge đã thành công thành thất bại.
    git("branch", "-D", branch, check=False)
    report(request_id, "applied", branch=branch, commit_sha=commit)
    print(f"[{request_id}] đã merge {branch} vào {BASE_BRANCH} ({commit[:8]})")


def main() -> int:
    missing = [name for name, value in (
        ("AUTOMATION_RUNNER_SECRET", RUNNER_SECRET),
        ("AGENT_REPO_DIR", str(REPO_DIR)),
    ) if not value]
    if missing:
        print(f"Thiếu {', '.join(missing)}; runner không khởi động.", file=sys.stderr)
        return 2
    # Chốt đường gọi model ngay lúc khởi động.  Để tới yêu cầu đầu tiên mới
    # phát hiện là hỏng trước mặt một người đang chờ.
    try:
        nha = chon_nha_cung_cap(MODEL_PROVIDER, OPENAI_API_KEY, tim_codex(CODEX_BIN))
        require_repo_root()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    mo_ta = OPENAI_MODEL if nha == "openai" else (CODEX_MODEL or "mặc định của codex")
    print(f"{RUNNER_LABEL} · repo {REPO_DIR} · nhánh nền {BASE_BRANCH} · model {mo_ta} qua {nha}")
    print(f"Poll {CENTER_URL} với runner key {RUNNER_KEY}")
    while True:
        try:
            heartbeat()
            approved = center_request(
                f"/api/runner/code/approved?runner_key={urllib.parse.quote(RUNNER_KEY)}"
            ).get("requests") or []
            if approved:
                apply_approved(approved[0])
                continue
            claimed = center_request("/api/runner/code/claim", method="POST", payload={"runner_key": RUNNER_KEY})
            request = claimed.get("request")
            if request:
                handle_request(request)
            else:
                time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f"Runner lỗi: {exc}", file=sys.stderr)
            time.sleep(max(POLL_SECONDS, 5))


if __name__ == "__main__":
    raise SystemExit(main())
