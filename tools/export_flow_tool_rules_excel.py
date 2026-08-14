from __future__ import annotations

import json
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from flow_web.service import FlowWebService
from flow_web.shot_rules import PRODUCT_SHOT_RULE_PRIORITY, PRODUCT_SHOT_RULES


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Flow_Tool_Rules_Current_Work_20260603.xlsx"
STATE_FILE = ROOT / "data" / "state.json"
ENV_FILE = ROOT / ".env.local"


def load_state() -> tuple[dict[str, Any], str]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/state", timeout=5) as response:
            return json.loads(response.read().decode("utf-8")), "http://127.0.0.1:8000/api/state"
    except Exception:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8")), str(STATE_FILE)
    return {}, "none"


def parse_env_projects() -> list[dict[str, str]]:
    if not ENV_FILE.exists():
        return []
    raw = ENV_FILE.read_text(encoding="utf-8", errors="replace")
    value = ""
    for line in raw.splitlines():
        if line.strip().startswith("FLOW_CHROME_PROFILE_PROJECTS="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
    rows: list[dict[str, str]] = []
    for item in value.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        label, url = item.split("=", 1)
        project_id = url.rstrip("/").split("/")[-1]
        rows.append({"label": label.strip(), "project_id": project_id, "url": url.strip()})
    return rows


def mojibake_score(value: str) -> int:
    return sum(value.count(marker) for marker in ("Ã", "Â", "Ä", "Æ", "áº", "á»", "ðŸ"))


def repair_mojibake(value: str) -> str:
    if mojibake_score(value) <= 0:
        return value
    best = value
    best_score = mojibake_score(value)
    for encoding in ("latin1", "cp1252"):
        try:
            candidate = value.encode(encoding).decode("utf-8")
        except Exception:
            continue
        score = mojibake_score(candidate)
        if score < best_score:
            best = candidate
            best_score = score
    return best


def cell_text(value: Any, limit: int = 32000) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    out = repair_mojibake(str(value))
    out = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", out)
    if len(out) > limit:
        return out[: limit - 20] + " ... [truncated]"
    return out


def col_letter(index: int) -> str:
    output = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        output = chr(65 + remainder) + output
    return output


def sheet_xml(rows: list[list[Any]], widths: list[int] | None = None) -> str:
    widths = widths or []
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
        'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
    ]
    if widths:
        parts.append("<cols>")
        for index, width in enumerate(widths, start=1):
            parts.append(f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>')
        parts.append("</cols>")
    parts.append("<sheetData>")
    for row_index, row in enumerate(rows, start=1):
        parts.append(f'<row r="{row_index}">')
        style = ' s="1"' if row_index == 1 else ""
        for col_index, value in enumerate(row, start=1):
            value_text = cell_text(value)
            if value_text == "":
                continue
            ref = f"{col_letter(col_index)}{row_index}"
            parts.append(
                f'<c r="{ref}"{style} t="inlineStr"><is><t xml:space="preserve">'
                f"{escape(value_text)}"
                "</t></is></c>"
            )
        parts.append("</row>")
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def safe_sheet_name(name: str) -> str:
    return (re.sub(r"[\\/*?:\[\]]", " ", name).strip() or "Sheet")[:31]


def styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Arial"/></font>'
        '<font><b/><sz val="11"/><name val="Arial"/></font>'
        '</fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def write_xlsx(path: Path, sheets: list[tuple[str, list[list[Any]], list[int]]]) -> None:
    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for index in range(1, len(sheets) + 1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    workbook_sheets = []
    workbook_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for index, (name, _rows, _widths) in enumerate(sheets, start=1):
        workbook_sheets.append(f'<sheet name="{escape(safe_sheet_name(name))}" sheetId="{index}" r:id="rId{index}"/>')
        workbook_rels.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    workbook_rels.append(
        f'<Relationship Id="rId{len(sheets) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    workbook_rels.append("</Relationships>")

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        + "".join(workbook_sheets)
        + "</sheets></workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        "</Relationships>"
    )
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>Flow Tool Rules and Current Work</dc:title><dc:creator>Codex</dc:creator>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now_iso}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now_iso}</dcterms:modified>'
        "</cp:coreProperties>"
    )
    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>Codex</Application></Properties>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", "".join(content_types))
        workbook.writestr("_rels/.rels", rels_xml)
        workbook.writestr("xl/workbook.xml", workbook_xml)
        workbook.writestr("xl/_rels/workbook.xml.rels", "".join(workbook_rels))
        workbook.writestr("xl/styles.xml", styles_xml())
        workbook.writestr("docProps/core.xml", core_xml)
        workbook.writestr("docProps/app.xml", app_xml)
        for index, (_name, rows, widths) in enumerate(sheets, start=1):
            workbook.writestr(f"xl/worksheets/sheet{index}.xml", sheet_xml(rows, widths))


def banner_hook_applies(kind: Any, title: Any, concept: Any) -> bool:
    joined = " ".join([str(kind), str(title), str(concept)]).lower()
    wall_terms = ("hanging", "hung", "wall", "treo", "nursery", "crib", "headboard", "baby room")
    non_wall_terms = (
        "table",
        "tabletop",
        "flat lay",
        "gift",
        "box",
        "folded",
        "collage",
        "close-up",
        "macro",
        "process",
        "embroidering",
        "craft table",
        "round embroidery hoop",
    )
    return any(term in joined for term in wall_terms) and not any(term in joined for term in non_wall_terms)


def build_sheets() -> list[tuple[str, list[list[Any]], list[int]]]:
    state, state_source = load_state()
    config = state.get("config") or {}
    integrations = state.get("integrations") or {}
    runtime = integrations.get("runtime") or {}
    profiles = runtime.get("flow_profiles") or []
    jobs = state.get("jobs") or []
    active_jobs = [job for job in jobs if str(job.get("status") or "").lower() in {"queued", "running", "polling"}]
    recent_jobs = jobs[:20]
    env_projects = parse_env_projects()

    server_health = "unknown"
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=3) as response:
            server_health = json.loads(response.read().decode("utf-8")).get("status", "unknown")
    except Exception as exc:
        server_health = f"unreachable: {exc}"

    summary_rows = [
        ["Mục", "Giá trị", "Ghi chú"],
        ["Generated at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Giờ local trên máy"],
        ["Workspace", str(ROOT), ""],
        ["State source", state_source, "Ưu tiên API; fallback data/state.json"],
        ["Local web", "http://127.0.0.1:8000", f"health={server_health}"],
        ["Project hiện tại", config.get("project_name", ""), config.get("project_id", "")],
        ["Project URL", config.get("project_url", ""), ""],
        ["Headless", config.get("headless", ""), "False nghĩa là browser automation có thể mở UI"],
        ["Generation timeout", config.get("generation_timeout_s", ""), "giây"],
        ["Poll interval", config.get("poll_interval_s", ""), "giây"],
        ["Số output mục tiêu", FlowWebService.FLOW_AGENT_TARGET_OUTPUT_COUNT, "Không tính ảnh nguồn/reference"],
        ["Max images per run", FlowWebService.FLOW_AGENT_MAX_IMAGES_PER_RUN, "Giới hạn Flow Agent"],
        ["ERP source list", FlowWebService.DEFAULT_ERP_SOURCE_LIST_NAME, "Tool quét card ở đây"],
        ["ERP review list", FlowWebService.DEFAULT_ERP_REVIEW_LIST_NAME, "Card chuyển/duyệt khi đủ output"],
        ["Active jobs", len(active_jobs), "queued/running/polling"],
        ["Tổng jobs trong state", len(jobs), ""],
        ["Gemini model", (state.get("integration_config") or {}).get("gemini_model") or "gemini-2.5-flash", ""],
        ["Số account Flow cấu hình", len(env_projects) or len(profiles), ""],
    ]

    workflow_rows = [
        ["#", "Giai đoạn", "Tool đang làm gì", "Rule/điều kiện dừng"],
        [1, "Quét ERP", "Quét card có ảnh trong Ready for AI hoặc list nguồn cấu hình.", "Chỉ lấy đúng list/card nguồn; card đủ 12 output thì bỏ qua trừ khi reset."],
        [2, "Khóa ảnh nguồn", "Chọn attachment ảnh trên chính card, lưu task_id và attachment_id vào prompt.", "Không dùng ảnh từ card khác, gallery Flow, thumbnail cũ, hoặc task trước."],
        [3, "Nhận diện sản phẩm", "Dùng tên card/attachment/user instruction và Gemini visual classification nếu có.", "Nếu không xác định được HAVI product rule/category thì dừng trước khi gửi Flow Agent."],
        [4, "Tạo request", "Ghép prompt vận hành cho Flow Agent: source lock, product lock, shot plan, lighting, embroidery, no-tag rules.", "Prompt ảnh cuối do Flow Agent tự viết nội bộ; app không bắt buộc dùng Sheet."],
        [5, "Mở Flow", "Dùng Google Flow project/profile đã cấu hình.", "Nếu profile quota/project lỗi thì đánh dấu hoặc chuyển account; nếu hết account thì dừng."],
        [6, "Attach ảnh", "Kéo/upload ảnh nguồn vào panel Tác nhân Flow.", "Phải chờ ready attachment mới gửi prompt; không gửi khi ảnh chưa sẵn sàng."],
        [7, "Tạo ảnh", "Yêu cầu đúng số ảnh còn thiếu, thường 12 output riêng biệt 1:1.", "Không tính ảnh gốc; không tạo grid/contact sheet; riêng pennant image 7 được collage detail."],
        [8, "Thu output", "Theo dõi/download ảnh Flow tạo ra và gom artifact.", "Nếu thiếu output thì split/rerun theo shot range, không reset về image 1."],
        [9, "QA/Gemini", "Nếu bật Gemini QA, kiểm ảnh generated có khớp nguồn/card nguồn không.", "Nếu Gemini báo sai source/category thì chặn upload; nếu Gemini quota thì báo lỗi rõ."],
        [10, "Upload/Duyệt", "Upload output về đúng card ERP, có thể gửi Telegram duyệt và chuyển Content Review khi đủ.", "Không upload vào card khác; đủ 12 output mới chuyển, không tính ảnh gốc."],
    ]

    global_rule_rows = [
        ["Nhóm rule", "Rule hiện tại", "Tác dụng"],
        ["Fresh task", "Flow Agent phải coi mỗi prompt là task mới, bỏ qua chat/task/gallery/project memory cũ.", "Tránh lấy nhầm sản phẩm/shot idea từ lần chạy trước."],
        ["Source lock", "Selected ERP attachment là ảnh nguồn duy nhất có thẩm quyền.", "Chống dùng nhầm thumbnail Flow hoặc ảnh card khác."],
        ["No generic filename inference", "Không suy luận product từ tên generic như tao_hinh/image/photo hoặc từ motif như animal/flower/character.", "Ảnh nguồn thắng filename."],
        ["Category lock", "Giữ nguyên category, silhouette, construction, material, base color family, design placement, scale.", "Không biến sản phẩm sang loại khác."],
        ["No derivative merchandise", "Không copy motif/name/design nguồn sang áo, gối, chăn, tote, hoop nếu nguồn không phải sản phẩm đó.", "Giữ đúng sản phẩm bán thật."],
        ["HAVI product rule required", "Auto AI ERP phải có HAVI product shot rule hoặc tín hiệu category rõ; nếu không có thì dừng.", "Tránh fallback generic tạo sai rule."],
        ["Output count", "Mục tiêu mặc định là 12 ảnh generated output + 1 ảnh nguồn; ảnh nguồn không được tính là output.", "Đảm bảo bộ ảnh đủ số lượng."],
        ["Missing outputs", "Nếu card đã có một phần output thì tạo phần còn thiếu tới đủ 12; split-run phải tiếp tục đúng shot range.", "Tránh tạo trùng image 1..8."],
        ["Square format", "Tất cả output là ảnh product photo 1:1 square.", "Chuẩn listing/Etsy."],
        ["No grid/collage", "Không tạo 12-frame grid/contact sheet; ngoại lệ: pennant image 7 được là 1 ảnh collage 4 panel close-up.", "Tránh Flow gom nhiều ảnh vào một canvas."],
        ["Lighting", "Clean clear white neutral daylight, accurate whites; không yellow/orange/golden/tungsten/sepia/beige/warm cast.", "Giữ màu sản phẩm sạch."],
        ["Embroidery", "Embroidery phải như thêu tay thật: raised thread, stitch direction, tactile fibers, crisp edges, natural thread shadows.", "Tránh thành print/sticker/digital flat."],
        ["No tags/labels", "Không thêm sticker, tag, price tag, hang tag, label, barcode, QR, sale badge, logo, watermark, text overlay nếu nguồn không có.", "Tránh AI thêm chữ/nhãn sai."],
        ["Names/text", "Chỉ đổi/tạo tên khi source có embroidered/personalized name và shot plan yêu cầu; nếu source không có tên thì không invent.", "Tránh chữ AI sai."],
        ["Banner special", FlowWebService.BANNER_VISIBLE_WALL_HOOK_RULE, "Áp cho mọi shot banner/cờ treo tường; không áp tabletop/gift/process."],
    ]

    profile_rows = [["Label", "Project ID", "Project URL", "Active", "Quota blocked", "Last error"]]
    profile_by_label = {str(profile.get("label") or ""): profile for profile in profiles if isinstance(profile, dict)}
    for project in env_projects:
        profile = profile_by_label.get(project["label"], {})
        profile_rows.append([
            project["label"],
            project["project_id"],
            project["url"],
            profile.get("active", ""),
            profile.get("quota_blocked", ""),
            profile.get("last_error", ""),
        ])

    product_rows = [["Priority", "Product key", "Display name", "Aliases", "Lock rule", "Shot count"]]
    shot_rows = [["Product key", "Display name", "Image #", "Kind", "Shot title", "Concept / prompt rule"]]
    for priority, key in enumerate(PRODUCT_SHOT_RULE_PRIORITY, start=1):
        rule = PRODUCT_SHOT_RULES.get(key, {})
        aliases = rule.get("aliases") or ()
        shots = rule.get("shots") or ()
        product_rows.append([priority, key, rule.get("display_name", key), ", ".join(map(str, aliases)), rule.get("lock", ""), len(shots)])
        for index, shot in enumerate(shots, start=1):
            kind, title, concept = (list(shot) + ["", "", ""])[:3]
            extra = ""
            if key == "banner" and banner_hook_applies(kind, title, concept):
                extra = "\n\nADDED CURRENT RULE: " + FlowWebService.BANNER_VISIBLE_WALL_HOOK_RULE
            shot_rows.append([key, rule.get("display_name", key), index, kind, title, str(concept) + extra])

    banner_rows = [
        ["Mục", "Chi tiết"],
        ["Rule mới", FlowWebService.BANNER_VISIBLE_WALL_HOOK_RULE],
        ["Áp dụng", "Mọi shot cờ/banner treo tường: hanging/hung/wall/treo/nursery/crib/headboard/baby room."],
        ["Không áp dụng", "Tabletop, flat lay, gift box/folded, collage/macro/close-up, process/woman embroidering/round embroidery hoop."],
        ["Prompt cần có", "clearly visible wall hook/nail/peg above the dowel; rope/cord visibly hanging from that support."],
        ["Lý do", "Ảnh cờ treo tường trước đó có thể bị crop mất móc hoặc nhìn như treo lơ lửng."],
    ]

    job_rows = [["Scope", "Job ID", "Status", "Title", "Error", "Created", "Updated"]]
    for job in active_jobs:
        job_rows.append(["active", job.get("id", ""), job.get("status", ""), job.get("title", ""), job.get("error", ""), job.get("created_at", ""), job.get("updated_at", "")])
    for job in recent_jobs:
        job_rows.append(["recent", job.get("id", ""), job.get("status", ""), job.get("title", ""), job.get("error", ""), job.get("created_at", ""), job.get("updated_at", "")])

    runbook_rows = [
        ["Triệu chứng", "Nguyên nhân thường gặp", "Cách xử lý hiện tại"],
        ["ERR_CONNECTION_REFUSED ở 127.0.0.1:8000", "Uvicorn/local web server tắt.", r"Start lại: .\.venv\Scripts\python.exe -m uvicorn flow_web.main:app --host 127.0.0.1 --port 8000"],
        ["Tool báo chạy nhưng không thấy cửa sổ", "Server chạy nền hidden; browser chỉ mở khi automation cần.", "Kiểm /api/health, /api/state, active jobs và logs/flow-web.*.err.log."],
        ["Tất cả profile quota_blocked", "Flow Agent báo hết quota trên các Chrome profile.", "Chờ quota reset hoặc thêm account/project; chỉ reset quota_blocked khi chắc quota đã reset."],
        ["Flow project màn hình đen 'Đã xảy ra lỗi'", "Project/account Flow lỗi hoặc không còn truy cập được.", "Đổi sang project/account khác còn mở được Flow Agent."],
        ["Ảnh chưa upload xong mà prompt đã gửi", "Race giữa file input và attachment ready.", "Đã sửa: app chờ ready attachment/label thay đổi trước khi gửi prompt."],
        ["Bộ ảnh sai product rule", "Không nhận diện đúng HAVI product hoặc fallback generic.", "Đã sửa: thiếu rule thì dừng; visual classification/inferred rule cho 14 sản phẩm."],
        ["Banner/cờ treo không thấy móc", "Prompt cũ không bắt rõ wall hook.", "Đã thêm BANNER_VISIBLE_WALL_HOOK_RULE cho shot treo tường."],
        ["Gemini quota free tier", "Gemini API hết request miễn phí.", "Chờ reset/thêm key khác; nếu không có product rule rõ, app sẽ dừng để tránh sai rule."],
    ]

    recent_change_rows = [
        ["Ngày", "Thay đổi", "File/chỗ liên quan", "Verification"],
        ["2026-06-03", "Sửa race upload ảnh: chờ Flow Agent ready attachment trước khi gửi prompt.", "flow_web/service.py; tests/test_flow_web_smoke.py", "unittest smoke OK"],
        ["2026-06-03", "Bỏ fallback generic khi không có HAVI product rule; app dừng để tránh tạo sai rule.", "flow_web/service.py", "unittest smoke OK"],
        ["2026-06-03", "Thêm visual inference cho toàn bộ 14 HAVI product rules, không riêng dress.", "flow_web/service.py; flow_web/shot_rules.py", "unittest smoke OK"],
        ["2026-06-03", "Thêm rule banner/cờ treo tường phải thấy rõ móc treo.", "flow_web/service.py; tests/test_flow_web_smoke.py", "229 tests OK"],
        ["2026-06-03", "Reset quota_blocked state cho Acc1-Acc4 theo yêu cầu user.", "data/state.json backup state.before-quota-reset.20260603-124056.json", "profiles quota_blocked=false"],
    ]

    return [
        ("Tổng quan", summary_rows, [26, 80, 80]),
        ("Workflow hiện tại", workflow_rows, [6, 28, 90, 90]),
        ("Rule chung", global_rule_rows, [24, 100, 70]),
        ("Profiles Projects", profile_rows, [16, 42, 90, 12, 16, 60]),
        ("Product rules", product_rows, [10, 24, 24, 80, 120, 12]),
        ("Shot plan all products", shot_rows, [24, 24, 10, 22, 40, 140]),
        ("Banner hook rule", banner_rows, [26, 120]),
        ("Jobs hiện tại", job_rows, [12, 38, 14, 70, 100, 26, 26]),
        ("Runbook lỗi", runbook_rows, [46, 70, 100]),
        ("Recent changes", recent_change_rows, [16, 80, 70, 36]),
    ]


def main() -> None:
    write_xlsx(OUT, build_sheets())
    print(OUT)
    print(OUT.stat().st_size)


if __name__ == "__main__":
    main()
