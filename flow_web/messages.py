from __future__ import annotations

import re

from .schemas import JobErrorSnapshot, JobRecoveryAction


_IMAGE_TIMEOUT_RE = re.compile(r"Timed out \((?P<seconds>\d+)s\) waiting for batchGenerateImages", re.IGNORECASE)
_VIDEO_TIMEOUT_RE = re.compile(r"Timed out \((?P<seconds>\d+)s\) waiting for (?:batchGenerateVideos|.*video.*)", re.IGNORECASE)
_GENERIC_TIMEOUT_RE = re.compile(r"Timed out \((?P<seconds>\d+)s\) waiting for (?P<target>[^.]+)", re.IGNORECASE)
_KNOWN_PREFIXES = ("Tác vụ thất bại: ", "Đăng nhập thất bại: ")


def _strip_known_prefixes(message: str) -> str:
    raw = (message or "").strip()
    while raw:
        matched = False
        for prefix in _KNOWN_PREFIXES:
            if raw.startswith(prefix):
                raw = raw[len(prefix):].strip()
                matched = True
                break
        if not matched:
            break
    return raw


def _has_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def humanize_flow_error(message: str) -> str:
    original = (message or "").strip()
    raw = original
    prefixes = []
    while raw:
        matched = False
        for prefix in _KNOWN_PREFIXES:
            if raw.startswith(prefix):
                prefixes.append(prefix)
                raw = raw[len(prefix):].strip()
                matched = True
                break
        if not matched:
            break
    if not raw:
        return ""

    lowered = raw.lower()

    # Playwright words the same lock three different ways depending on how the
    # profile is held; the cửa sổ đăng nhập Flow itself trips the third one.
    if (
        "processsingleton" in raw
        or "singletonlock" in lowered
        or "profile directory is already in use" in lowered
        or "profile is already in use" in lowered
        or "opening in existing browser session" in lowered
    ):
        result = "Chromium đang mở với hồ sơ Flow hiện tại. Chủ nhân hãy đóng cửa sổ Chromium hoặc Chrome dùng cho Flow rồi thử lại."
        return "".join(prefixes) + result

    # Frappe caps attachments per Task, so a card reused for many runs starts
    # rejecting uploads with a wall of raw traceback JSON.
    if "attachmentlimitreached" in lowered.replace(" ", ""):
        result = (
            "Task trên ERP đã chạm giới hạn số tệp đính kèm. Chủ nhân hãy xóa bớt ảnh cũ trên card "
            "hoặc nâng giới hạn đính kèm của Task rồi chạy lại."
        )
        return "".join(prefixes) + result

    if "something went wrong" in lowered:
        result = "Google Flow báo lỗi khi mở project hoặc xử lý yêu cầu. Chủ nhân thử tải lại project trên Flow rồi chạy lại."
        return "".join(prefixes) + result

    if "not authenticated" in lowered or "authentication" in lowered and "required" in lowered:
        result = "Phiên đăng nhập Google Flow không còn hiệu lực. Chủ nhân hãy đăng nhập lại."
        return "".join(prefixes) + result

    # Without a Bearer token the Flow API falls back to the bare API key and
    # answers with a Google Cloud doc link, which tells the owner nothing about
    # the one thing that actually fixes it: signing in to Flow again.
    if "api keys are not supported by this api" in lowered or (
        "http 401" in lowered and "oauth2 access token" in lowered
    ):
        result = (
            "Phiên đăng nhập Google Flow đã hết hạn nên không lấy được token. "
            "Chủ nhân hãy bấm Đăng nhập Flow trên bảng điều khiển rồi chạy lại."
        )
        return "".join(prefixes) + result

    if "permission denied" in lowered or "forbidden" in lowered:
        result = "Tài khoản hiện tại không có quyền truy cập project hoặc tác vụ này trên Google Flow."
        return "".join(prefixes) + result

    if "project" in lowered and "not found" in lowered:
        result = "Không tìm thấy project trên Google Flow. Chủ nhân kiểm tra lại mã project hoặc quyền truy cập."
        return "".join(prefixes) + result

    if "browser has been closed" in lowered:
        result = "Cửa sổ Chromium dùng cho Google Flow đã bị đóng giữa chừng."
        return "".join(prefixes) + result

    if (
        "tools agent quota" in lowered
        or "flow agent quota" in lowered
        or ("agent" in lowered and "quota limit" in lowered)
        or ("come back tomorrow" in lowered and "quota" in lowered)
        or ("daily quota" in lowered and "agent" in lowered)
    ):
        result = (
            "Google Flow Agent/Tools Agent da het quota cho profile hien tai. "
            "App se thu chuyen sang Chrome profile khac neu da cau hinh; neu khong con profile nao, hay cho quota reset hoac dung tai khoan khac da dang nhap hop le."
        )
        return "".join(prefixes) + result

    if "audio generation failed" in lowered or "return silent videos" in lowered:
        result = (
            "Google Flow đã dựng tới bước âm thanh nhưng phần tạo audio bị lỗi. "
            "Chủ nhân thử prompt khác, bật trả video im lặng trong Flow, hoặc đổi sang model không audio như Veo 2."
        )
        return "".join(prefixes) + result

    image_timeout = _IMAGE_TIMEOUT_RE.search(raw)
    if image_timeout:
        seconds = image_timeout.group("seconds")
        result = f"Google Flow không trả về ảnh trong {seconds} giây. Chủ nhân thử chạy lại hoặc tăng thời gian chờ."
        return "".join(prefixes) + result

    video_timeout = _VIDEO_TIMEOUT_RE.search(raw)
    if video_timeout:
        seconds = video_timeout.group("seconds")
        result = f"Google Flow không trả về video trong {seconds} giây. Chủ nhân thử chạy lại hoặc tăng thời gian chờ."
        return "".join(prefixes) + result

    generic_timeout = _GENERIC_TIMEOUT_RE.search(raw)
    if generic_timeout:
        seconds = generic_timeout.group("seconds")
        target = generic_timeout.group("target").strip()
        result = f"Google Flow phản hồi quá chậm khi chờ {target} trong {seconds} giây. Chủ nhân thử chạy lại hoặc tăng thời gian chờ."
        return "".join(prefixes) + result

    return "".join(prefixes) + raw


def classify_job_error(message: str, *, job_type: str = "") -> JobErrorSnapshot:
    humanized = humanize_flow_error(message)
    raw = _strip_known_prefixes(humanized or message)
    lowered = raw.lower()
    normalized_job_type = str(job_type or "").strip().lower()

    if not raw:
        return JobErrorSnapshot(
            category="unknown",
            label="Lỗi chưa phân loại",
            title="Chưa nhận được mô tả lỗi rõ ràng",
            message="Tác vụ gặp lỗi nhưng app chưa nhận được mô tả chi tiết. Chủ nhân hãy làm mới trạng thái rồi thử lại.",
            actions=[
                JobRecoveryAction(
                    id="refresh-all",
                    label="Làm mới trạng thái",
                    description="Tải lại /api/state để xem app đã nhận thêm chi tiết lỗi hay chưa.",
                ),
            ],
        )

    if (
        _has_any(lowered, "tools agent quota", "flow agent quota", "quota limit", "come back tomorrow", "daily quota")
        and _has_any(lowered, "agent", "tools")
    ):
        return JobErrorSnapshot(
            category="flow_agent_quota",
            label="Het quota Agent",
            title="Google Flow Agent da het quota tren profile hien tai",
            message=humanized,
            is_known=True,
            actions=[
                JobRecoveryAction(
                    id="focus-login",
                    label="Mo profile Flow",
                    description="Mo Chrome profile Flow khac de dang nhap tai khoan con quota.",
                ),
                JobRecoveryAction(
                    id="view-jobs",
                    label="Theo doi auto",
                    description="Kiem tra job tiep theo xem app da chuyen sang profile khac hay chua.",
                ),
            ],
        )

    if _has_any(lowered, "processsingleton", "singletonlock", "profile directory is already in use"):
        return JobErrorSnapshot(
            category="browser_lock",
            label="Khóa browser",
            title="Hồ sơ Chromium đang bị phiên khác giữ",
            message=humanized,
            is_known=True,
            actions=[
                JobRecoveryAction(
                    id="focus-login",
                    label="Mở lại browser Flow",
                    description="Đóng mọi cửa sổ Chromium hoặc Chrome đang dùng profile Flow rồi mở lại đăng nhập.",
                ),
                JobRecoveryAction(
                    id="view-jobs",
                    label="Xem lại tác vụ lỗi",
                    description="Giữ bảng tác vụ mở để theo dõi xem phiên mới đã chạy ổn chưa.",
                ),
            ],
        )

    if _has_any(lowered, "not authenticated", "đăng nhập", "phiên đăng nhập", "authentication required"):
        return JobErrorSnapshot(
            category="auth",
            label="Lỗi đăng nhập",
            title="Phiên Google Flow không còn sẵn sàng",
            message=humanized,
            is_known=True,
            actions=[
                JobRecoveryAction(
                    id="login",
                    label="Đăng nhập lại Google Flow",
                    description="Mở lại cửa sổ đăng nhập để làm mới phiên trước khi chạy tiếp.",
                ),
                JobRecoveryAction(
                    id="view-jobs",
                    label="Theo dõi bảng tác vụ",
                    description="Quan sát job đăng nhập và tác vụ lỗi ở cùng một chỗ để xác nhận phiên đã hồi phục.",
                ),
            ],
        )

    if (
        _has_any(lowered, "project", "mã project")
        and _has_any(
            lowered,
            "not found",
            "không tìm thấy",
            "quyền truy cập",
            "permission denied",
            "forbidden",
            "bắt buộc",
            "mở project",
            "tải lại project",
        )
    ):
        return JobErrorSnapshot(
            category="project",
            label="Lỗi project",
            title="Project Google Flow cần được kiểm tra lại",
            message=humanized,
            is_known=True,
            actions=[
                JobRecoveryAction(
                    id="focus-project",
                    label="Kiểm tra project",
                    description="Quay lại Bước 1 để kiểm tra mã project, URL project và quyền truy cập.",
                ),
                JobRecoveryAction(
                    id="refresh-all",
                    label="Làm mới workspace",
                    description="Tải lại state sau khi chủ nhân sửa project để app đồng bộ ngay.",
                ),
            ],
        )

    if _has_any(lowered, "workflow", "media id", "media_id", "workflow id"):
        return JobErrorSnapshot(
            category="workflow",
            label="Lỗi workflow",
            title="Workflow hoặc media tham chiếu chưa khớp",
            message=humanized,
            is_known=True,
            actions=[
                JobRecoveryAction(
                    id="load-workflows",
                    label="Tải lại workflow",
                    description="Làm mới danh sách workflow rồi điền lại workflow/media đúng cho form chỉnh sửa.",
                ),
                JobRecoveryAction(
                    id="open-edit",
                    label="Mở form chỉnh sửa",
                    description="Kiểm tra lại Media ID, Workflow ID và loại thao tác trước khi chạy lại.",
                ),
            ],
        )

    if (
        _has_any(
            lowered,
            "timed out",
            "hết thời gian chờ",
            "quá chậm",
            "timeout",
            "thời gian chờ",
            "không trả về ảnh",
            "không trả về video",
            "không trả về",
        )
        or _IMAGE_TIMEOUT_RE.search(raw)
        or _VIDEO_TIMEOUT_RE.search(raw)
        or _GENERIC_TIMEOUT_RE.search(raw)
    ):
        timeout_title = "Google Flow phản hồi chậm hơn thời gian chờ đã lưu"
        if normalized_job_type == "image":
            timeout_title = "Tạo ảnh đã chạm giới hạn thời gian chờ"
        elif normalized_job_type in {"video", "extend", "upscale", "camera_motion", "camera_position", "insert", "remove"}:
            timeout_title = "Tạo hoặc xử lý video đã chạm giới hạn thời gian chờ"
        return JobErrorSnapshot(
            category="timeout",
            label="Lỗi timeout",
            title=timeout_title,
            message=humanized,
            is_known=True,
            actions=[
                JobRecoveryAction(
                    id="focus-timeout",
                    label="Tăng thời gian chờ",
                    description="Mở phần cấu hình để tăng timeout lên khoảng 420-600 giây rồi thử lại.",
                ),
                JobRecoveryAction(
                    id="view-jobs",
                    label="Xem lại bảng tác vụ",
                    description="So sánh log hiện tại trước khi chạy lại để biết Flow dừng ở bước nào.",
                ),
            ],
        )

    if _has_any(
        lowered,
        "audio generation failed",
        "return silent videos",
        "phần tạo audio bị lỗi",
        "video im lặng",
        "model không audio",
    ):
        return JobErrorSnapshot(
            category="audio",
            label="Lỗi audio",
            title="Google Flow vấp ở bước tạo âm thanh",
            message=humanized,
            is_known=True,
            actions=[
                JobRecoveryAction(
                    id="retry-prompt",
                    label="Thử prompt khác",
                    description="Rút gọn hoặc đổi prompt rồi chạy lại để giảm khả năng audio bị Flow từ chối.",
                ),
                JobRecoveryAction(
                    id="switch-model",
                    label="Dùng video im lặng",
                    description="Bật trả video im lặng trong Flow hoặc đổi sang model không audio như Veo 2.",
                ),
            ],
        )

    if _has_any(lowered, "khởi động lại", "bị ngắt") or ("máy chủ" in lowered and "đang chạy" in lowered):
        return JobErrorSnapshot(
            category="interrupted",
            label="Tác vụ bị ngắt",
            title="App đã khởi động lại khi tác vụ chưa hoàn tất",
            message=humanized,
            is_known=True,
            actions=[
                JobRecoveryAction(
                    id="focus-replay-pack",
                    label="Mở replay pack",
                    description="Xem cụm interrupted work để mở retry nhanh từ đúng job đang bị ngắt.",
                ),
                JobRecoveryAction(
                    id="view-jobs",
                    label="Xem bảng tác vụ",
                    description="Đối chiếu log cuối và kết quả hiện có trước khi quyết định chạy lại.",
                ),
            ],
        )

    if _has_any(lowered, "browser has been closed", "chromium", "chrome", "browser"):
        return JobErrorSnapshot(
            category="browser",
            label="Lỗi browser",
            title="Phiên browser dùng cho Flow đã bị đóng hoặc mất kết nối",
            message=humanized,
            is_known=True,
            actions=[
                JobRecoveryAction(
                    id="focus-login",
                    label="Mở lại browser Flow",
                    description="Mở lại cửa sổ Flow hoặc phiên đăng nhập trước khi tiếp tục tác vụ kế tiếp.",
                ),
                JobRecoveryAction(
                    id="refresh-all",
                    label="Làm mới trạng thái",
                    description="Tải lại state để kiểm tra app đã nhìn thấy browser mới hay chưa.",
                ),
            ],
        )

    return JobErrorSnapshot(
        category="unknown",
        label="Lỗi chưa phân loại",
        title="Chưa map được lỗi vào nhóm recovery cố định",
        message=humanized,
        actions=[
            JobRecoveryAction(
                id="refresh-all",
                label="Làm mới trạng thái",
                description="Tải lại toàn bộ state trước để kiểm tra xem lỗi có đổi sang trạng thái rõ hơn không.",
            ),
            JobRecoveryAction(
                id="view-jobs",
                label="Xem log tác vụ",
                description="Mở bảng tác vụ và log hiện tại để quyết định lần chạy tiếp theo.",
            ),
        ],
    )
