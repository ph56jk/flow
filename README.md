# Flow v2

Web app local điều khiển [flow-py](https://github.com/eddie-fqh/flow-py) qua giao diện trình duyệt. App bọc các luồng chính của `flow-py`: đăng nhập Google Flow, kiểm tra credits, sinh video/ảnh, image-to-video, extend, upscale, camera motion/position, insert/remove object, xem workflows và tải kết quả.

---

## 1. Yêu cầu hệ thống

| Mục | Yêu cầu |
|---|---|
| OS | Windows 10/11 hoặc macOS / Linux |
| Python | **3.11+**. Trên Windows, script one-click có thể tự kéo Python portable nếu máy chưa có |
| Git | Cần để clone repo |
| Chromium | Sẽ do Playwright tự tải |
| Tài khoản Google | Đã được cấp quyền truy cập Google Flow (labs.google/fx) |
| Gemini API key | Tuỳ chọn — chỉ cần nếu muốn dùng Prompt AI dùng Gemini thật |

## 2. Chạy nhanh kiểu một phát

### Một launcher chung cho mọi hệ điều hành

Nếu máy đã có Python 3.11+, có thể dùng cùng một launcher trên Windows, macOS và Linux:

```bash
python3 scripts/run_flow_web.py
```

Launcher này tự tạo `.venv`, cài dependency, cài Chromium cho Playwright, mở trình duyệt và chạy app ở `http://127.0.0.1:8000`.
Trên Windows nếu chưa có Python 3.11, dùng script PowerShell bên dưới vì nó có thể tự kéo Python portable.

### Windows

```powershell
git clone https://github.com/ph56jk/flow-v2.git
cd flow-v2
powershell -ExecutionPolicy Bypass -File .\scripts\run_flow_web.ps1
```

Script này sẽ tự:
- chọn ổ còn nhiều chỗ trống hơn để đặt runtime nếu `C:` gần đầy
- tự kéo Python portable nếu máy chưa có Python 3.11 chuẩn
- tạo `.venv` nếu chưa có
- cài dependencies nếu thiếu hoặc vừa pull code mới
- cài Chromium cho Playwright nếu chưa có
- mở app ở `http://127.0.0.1:8000`

Nếu đã có Python 3.11 sẵn, có thể chạy chung cùng macOS/Linux:

```powershell
py -3.11 .\scripts\run_flow_web.py
```

### Windows portable: giải nén là chạy

Nếu không muốn mỗi máy lại tải Python, dependency và Chromium từ đầu, có thể build sẵn một bản portable ngay trên Windows:

```powershell
cd flow-v2
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_portable.ps1
```

Script này sẽ tạo thư mục:

```text
dist\flow-windows-portable
```

Trong đó đã có sẵn:
- Python portable
- dependency Python
- Chromium cho Playwright
- launcher `Flow v2.cmd`

Người dùng cuối chỉ cần:
1. copy hoặc giải nén thư mục đó sang máy Windows khác
2. double click `Flow v2.cmd`

Không cần clone repo, không cần cài Python, không cần chờ tải Chromium lại.

### Windows release zip: đóng gói để gửi cho người khác

Nếu muốn đóng thành một file zip để share:

```powershell
cd flow-v2
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_release.ps1
```

Script này sẽ tạo:

```text
dist\flow-windows-release.zip
```

Người nhận chỉ cần:
1. tải file zip
2. giải nén
3. double click `Flow v2.cmd`

### macOS / Linux

```bash
git clone https://github.com/ph56jk/flow-v2.git
cd flow-v2
chmod +x ./scripts/run_flow_web.sh ./scripts/run_flow_web.command
./scripts/run_flow_web.sh
```

Nếu dùng macOS và thích double-click:
- mở [run_flow_web.command](./scripts/run_flow_web.command)

Script `.sh` hiện gọi launcher Python chung nên hành vi trên macOS/Linux bám cùng một đường chạy với Windows có Python 3.11.

### Test nhanh sau khi cài

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_flow_web_tests.ps1
```

macOS / Linux:

```bash
./scripts/run_flow_web_tests.sh
```

### ⚠️ Windows lưu ý đặc biệt

- **Path cài Chromium KHÔNG được có khoảng trắng.** Thư mục `C:\Users\HAVI GROUP\...` sẽ gây lỗi `side-by-side configuration is incorrect` / `spawn UNKNOWN`. Script `run_flow_web.ps1` sẽ tự chọn path kiểu `D:\pw-flow` hoặc `C:\pw-flow` theo ổ còn trống.
- Cần **Microsoft Visual C++ Redistributable (x64)** mới nhất — Chromium yêu cầu.
- Biến môi trường `Path` **không được có entry rỗng** (dấu `;` thừa cuối chuỗi) vì sẽ gây Node.js `spawn UNKNOWN` khi Playwright launch browser.
- `flow-py` đã được đổi sang tải từ file zip GitHub trực tiếp, nên **không còn bắt buộc phải có Git** chỉ để `pip install` chạy được.
- Các script `.sh` trong repo chỉ dùng cho macOS/Linux. Trên Windows dùng PowerShell hoặc các script `scripts/setup_windows.ps1`, `scripts/run_flow_web.ps1`.
- Google Flow dùng browser automation + reCAPTCHA → **chạy ở chế độ hiện cửa sổ (không headless)** ổn định hơn nhiều so với headless.

---

## 3. Cài đặt thủ công

### 3.1. Clone repo

```bash
git clone https://github.com/ph56jk/flow-v2.git
cd flow-v2
```

### 3.2. Cài Python 3.11 (nếu chưa có)

**Windows (winget):**
```powershell
winget install --id Python.Python.3.11 -e
```

**macOS:**
```bash
brew install python@3.11
```

### 3.3. Cài Microsoft Visual C++ Redistributable (chỉ Windows)

```powershell
winget install --id Microsoft.VCRedist.2015+.x64 -e
```

### 3.4. Tạo venv và cài dependencies

**Windows PowerShell:**
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

**Windows bash / macOS / Linux:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate          # mac/linux
# hoặc: .venv/Scripts/activate     # Windows bash
pip install --upgrade pip
pip install -e .
```

### 3.5. Cài Chromium cho Playwright

**Windows (BẮT BUỘC dùng path không có khoảng trắng):**
```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "C:\pw"
python -m playwright install chromium
```

**macOS / Linux:**
```bash
python -m playwright install chromium
```

---

## 4. Cấu hình

### 4.1. File `.env.local` (ở root repo)

Tạo file `.env.local` với nội dung:

```env
# Không cần env cho thao tác thường ngày:
# nhập trực tiếp trong app ở sidebar App integrations / ERP storage.
# Các biến dưới chỉ còn là fallback nâng cao nếu muốn cấu hình ngoài UI.
# PLAYWRIGHT_BROWSERS_PATH=C:\pw-flow
# GEMINI_API_KEY=AIza...
# GEMINI_MODEL=gemini-2.5-flash
# ERP_API_KEY=your_erp_key
# ERP_API_SECRET=your_erp_api_secret
# ERP_BASE_URL=https://erp.havigroup.llc
# ERP_PROJECT_ID=PROJ-0049
# ERP_TASK_ID=TASK-xxxx
# ERP_STATUS_ID=Open
# Bộ xóa watermark Gemini (thư mục removelogo, chạy bằng `npm start`).
# REMOVE_LOGO_URL=http://127.0.0.1:8788
# REMOVE_LOGO_ENABLED=false

# Multi-account Flow Agent fallback. Each path is one separate Chrome profile.
# Use ; to separate profiles on Windows. The token "default" keeps the normal
# flow-py profile as the first account.
# FLOW_CHROME_PROFILE_DIRS=Acc1=default;Acc2=data\flow-profiles\account-2;Acc3=data\flow-profiles\account-3
# Optional: map each profile to its own Flow project. Profiles without a
# mapping use the project saved in the app UI.
# FLOW_CHROME_PROFILE_PROJECTS=Acc2=https://labs.google/fx/vi/tools/flow/project/project-id-2;Acc3=https://labs.google/fx/vi/tools/flow/project/project-id-3
# FLOW_CHROME_PROFILE_QUOTA_BLOCK_S=86400
```

App sẽ tự nạp file này khi khởi động nếu có, nhưng không bắt buộc. Nếu không tạo Prompt AI sẽ dùng kho skill nội bộ.
Ảnh Flow chỉ được ghi về ERP sau khi toàn bộ review được duyệt trên dashboard.
Gemini là tuỳ chọn, chỉ dùng cho phần **AI viết prompt**. Nếu workflow chỉ là Google Sheet/Excel -> Flow -> dashboard/ERP thì chỉ cần tài khoản Flow đã đăng nhập.
Playwright path có thể nhập trong sidebar **App integrations** rồi bấm **Lưu app**. Không cần sửa `.env.local`; secret chỉ được lưu local và API chỉ trả về cờ trạng thái đã cấu hình.
ERP sử dụng HaviGroup ERP qua HTTPS GraphQL: mở dashboard, đi tới **HaviGroup ERP**, nhập API key + API secret, điền mã **Project** (ví dụ `PROJ-0013`) rồi chọn Task nguồn. App chỉ đọc/ghi trong đúng project đang cấu hình — mọi Task ID gõ tay, graph import hay batch item đều bị kiểm tra lại theo giá trị này, nên phạm vi ảnh hưởng luôn gói trong một project. ERP Source đọc ảnh nguồn từ comment trên Task (kể cả file `/private/files/...` do người dùng đính qua web ERP — Flow v2 tải qua endpoint `download_file` có auth). Sau khi duyệt trên dashboard, Flow v2 đẩy ảnh đã xóa watermark lên chính ERP rồi gắn nó vào comment Task như **file đính kèm thật**, hiển thị inline đúng như khi người dùng kéo ảnh vào ô comment. Job thất bại cũng được ghi vào comment với tiền tố `[FLOW_V2_ERROR]`. App không tạo/sửa/xóa Task.

Cơ chế gắn attachment gồm đúng hai bước, và **thứ tự cùng bộ field là bắt buộc** (đây chính là payload mà web ERP gửi):

1. `POST /api/method/upload_file` với `is_private=1`, `folder=Home`, `doctype=Task`, `docname=<task>`, `fieldname=comment`. Giá trị `fieldname=comment` là cờ "file đang chờ gắn vào comment kế tiếp"; thiếu nó thì bước 2 luôn trả `linked: 0`.
2. `addTaskComment(name, content, attachments: ["/private/files/..."])` với đường dẫn **tương đối** vừa nhận. ERP tự chuyển file sang `attached_to_field = comment:<comment_id>` và trả `linked: 1`.

Nếu `linked` vẫn bằng 0, Flow v2 ghi thêm một comment chứa URL tuyệt đối để ảnh không biến mất; hàm đọc lại nhận cả hai dạng (attachment thật và URL trong nội dung), nên số output cũ luôn đếm đúng và ảnh không bị tạo lại.

**Ảnh tạo ra nằm trong thread "Trả lời" của comment ảnh nguồn**, đúng luồng người dùng mong đợi: thả ảnh vào card → mọi ảnh Flow tạo ra (và cả comment lỗi `[FLOW_V2_ERROR]`) nằm gọn trong thread của chính comment đó thay vì thành một dãy comment rời. Mutation GraphQL `addTaskComment` **không có tham số cha** (trường `meta` chỉ được lưu nguyên văn, không tạo thread), nên Flow v2 gọi đúng whitelisted method mà nút "Trả lời" của web ERP dùng:

```
POST /api/method/hvg_workspace.api.add_task_comment
{"name": "<TASK>", "content": "...", "mentions": "[]", "meta": "",
 "parent": "<id comment ảnh nguồn>", "attachments": ["/private/files/..."]}
→ {"message": {"ok": true, "linked": 1}}
```

Comment cha được tìm lại theo `file_url` của ảnh nguồn (`_erp_source_comment_id`) chứ không lưu trong state, nên vẫn đúng sau khi job chờ duyệt lâu hoặc app khởi động lại. Không tìm thấy comment cha thì ảnh rơi về comment thường và log job nói rõ điều đó.

> ⚠️ **Giới hạn ERP còn lại:** không tạo được cột mới. "Cột" trên ERP là các option `status` của DocType Task (`Open`, `Working`, `Pending Review`, `Completed`, `Cancelled`); `DocField`/`DocPerm` đều trả `403` nên không thể thêm cột kiểu "Pic For AI" qua API. Dùng cột **Open** làm cột "cần làm" (mặc định sẵn của app).
>
> Lưu ý: ERP khử trùng lặp file theo nội dung — upload hai ảnh giống hệt nhau sẽ trả về cùng một `file_url`. Đọc trực tiếp DocType `Comment`/`DocPerm` qua REST bị `403`; muốn xóa comment thì gọi `hvg_workspace.api.delete_task_comment(name, comment)`.

### 4.1b. Bước xóa watermark Gemini (`removelogo`)

Mọi ảnh Google Flow trả về đều có watermark Gemini, nên module **Remove Logo** nằm ngay sau **Google Flow** và trước bước duyệt. Module này gọi server Node trong thư mục `removelogo`:

1. Mở thư mục `removelogo`, chạy `npm install` (lần đầu) rồi `npm start`.
2. Server lắng nghe ở `http://127.0.0.1:8788`. Đổi địa chỉ bằng `REMOVE_LOGO_URL` hoặc ô cấu hình trong app.
3. Flow v2 gửi từng ảnh qua `POST {base_url}/process` và ghi file PNG sạch về thư mục downloads; ảnh trên dashboard và file gửi lên ERP đều là bản đã xử lý.

Nếu server chưa chạy hoặc xử lý lỗi, job **không** fail: ảnh gốc được giữ nguyên, artifact ghi trạng thái `failed` và log job nói rõ lý do. Riêng trường hợp ảnh vốn không có watermark Gemini (removelogo trả `422`), artifact ghi `skipped` chứ không phải `failed` — không có gì để xóa thì không phải lỗi.

removelogo gỡ metadata AI (C2PA/XMP/EXIF) **trước** khi tìm watermark hiển thị, và khi bước hiển thị không sửa được gì nó vẫn trả `200` kèm file chỉ-gỡ-metadata. Flow v2 vì thế so pixel file trả về với ảnh gốc: giống hệt nhau thì artifact ghi `metadata_only` (không phải `cleaned`) và log job cảnh báo "chỉ gỡ được metadata, watermark hiển thị vẫn còn". File đó vẫn là file được gửi lên ERP vì nó đã sạch metadata, chỉ là trạng thái không được phép nói quá. Đặt `REMOVE_LOGO_ENABLED=false` để bỏ hẳn bước này. Công cụ chỉ xóa watermark Gemini và metadata AI (C2PA/XMP/EXIF) do chính Google gắn vào ảnh bạn tạo ra — không dùng cho ảnh của người khác.

Tài liệu ERP chính thức ưu tiên `Authorization: HVGToken <raw-token>`. Cặp API key/API secret được cấp cho luồng này đã được xác nhận chỉ-đọc qua cơ chế tương thích Frappe `Authorization: token <key>:<secret>`; chúng không thể tự chuyển thành raw HVG token. Khi công ty cấp raw HVG token, hãy chuyển integration sang header chính thức đó thay vì suy diễn token từ cặp key/secret.

### 4.1c. Chạy ảnh cho từng idea (Phân rã công việc → mỗi thẻ con là 1 idea)

Luồng người dùng ERP mô tả: một thẻ **Idea** cha giữ ảnh sản phẩm gốc (kể cả khi ảnh đó chỉ là **ảnh bìa** của thẻ), phần **PHÂN RÃ CÔNG VIỆC** tách mỗi idea thành một thẻ con riêng ở cột *Cần làm*. Ảnh content chạy cho idea "a" phải nằm trong chính thẻ "a", không dồn hết về thẻ cha.

Trong sidebar **Chạy ảnh cho từng idea**: điền mã thẻ Idea cha (ví dụ `TASK-2026-00202`), số ảnh mỗi idea (mặc định 12) rồi bấm **Chạy ảnh cho các idea**. Tương đương API:

```
POST /api/erp/idea-batch
{"task_id": "TASK-2026-00202", "count": 12, "include_done": false, "child_task_ids": []}
→ {"parent_task_id": ..., "project_id": ..., "queued": [{"job_id", "task_id", "subject"}], "skipped": [...]}
```

Mỗi thẻ con thành một job riêng, chạy tuần tự (một trình duyệt, một phiên Flow):

1. Ảnh nguồn lấy từ thẻ **cha** — comment, attachment, hoặc `cover_image`.
2. Prompt ghép từ tiêu đề + mô tả của thẻ **con** cộng bối cảnh mô tả của thẻ cha.
3. Ảnh chạy xong dừng ở **bước duyệt trên dashboard** — đúng yêu cầu "nhớ có nút duyệt/bỏ để check ảnh". Chưa duyệt thì không có gì được ghi lên ERP.
4. Ảnh được duyệt mới được gửi vào comment của **chính thẻ con** đó; ảnh bị từ chối không bao giờ rời khỏi máy.

Vì đích ghi khác thẻ nguồn, ảnh của idea nằm ở comment cấp một của thẻ con (không chui vào thread trả lời của comment ảnh nguồn trên thẻ cha). Thẻ con đã có ảnh Flow (`[FLOW_V2_ARTIFACT]`) bị bỏ qua, trừ khi bật **Chạy lại cả thẻ con đã có ảnh Flow** (`include_done: true`). Truyền `child_task_ids` để chỉ chạy vài idea cụ thể.

### 4.2. Custom giao diện và luồng automation

Trong sidebar **Tùy biến người dùng**, có thể đổi:
- tên app / scenario
- mô tả trên thanh đầu
- nguồn prompt bằng link Google Sheet/CSV, upload `.xlsx/.csv/.tsv`, hoặc paste bảng copy từ Google Sheets
- màu chủ đạo
- tên và ghi chú từng module trong diagram
- Gemini, Playwright path và ERP Task/status dùng cho bước viết prompt, duyệt trên dashboard và lưu URL artifact
- bấm từng module để đổi loại, đổi ký hiệu, bật/tắt, thêm, xóa, nhân bản hoặc di chuyển module trong diagram

Khi dùng file/bảng prompt, app tìm cột `Prompt_Content` hoặc `Prompt`, ưu tiên các dòng có `Active = TRUE`, rồi đưa prompt đầu tiên vào ô **Tạo ảnh bằng Flow**.

Giao diện người dùng chính hiện chỉ để lộ dashboard kiểu Make. Các form Studio cũ vẫn được giữ trong code để tái sử dụng logic tạo ảnh/video khi cần, nhưng không còn là luồng thao tác chính của người dùng.

Các tuỳ chỉnh này được lưu trong trình duyệt bằng `localStorage`. Muốn mang sang máy Windows hoặc MacBook khác, bấm **Export** để tải `flow-automation-config.json`, rồi sang máy mới bấm **Import** trong cùng khu vực.

### 4.3. File `~/.flow-py/config.json` (tự sinh sau lần đăng nhập đầu)

Đảm bảo `"headless": false` để cửa sổ Chromium hiện ra và giải reCAPTCHA khi cần:

```json
{
  "headless": false,
  ...
}
```

---

## 5. Chạy app thủ công

**Windows PowerShell:**
```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "C:\pw-flow"
.\.venv\Scripts\Activate.ps1
python -m uvicorn flow_web.main:app --host 127.0.0.1 --port 8000 --reload
```

**Windows bash:**
```bash
PLAYWRIGHT_BROWSERS_PATH="C:\\pw-flow" .venv/Scripts/python.exe -m uvicorn flow_web.main:app --host 127.0.0.1 --port 8000
```

**macOS / Linux:**
```bash
source .venv/bin/activate
uvicorn flow_web.main:app --reload
```

Mở trình duyệt: http://127.0.0.1:8000

---

## 6. Cách dùng lần đầu

1. Mở http://127.0.0.1:8000
2. Dán **Project ID** của Google Flow vào ô Config → bấm **Save Config**
3. Bấm **Sign In With Google Flow** → Chromium sẽ mở ra tab đăng nhập Google
4. Đăng nhập tài khoản Google đã có quyền truy cập Google Flow
5. Sau khi đăng nhập xong, tab Chromium **được giữ nguyên** để dùng tiếp
6. Dùng các form Generate / Edit để tạo video/ảnh
7. Job chạy nền — theo dõi ở card **Luồng gần nhất**

### ⚠️ Khi gặp reCAPTCHA

Google Flow có thể bật reCAPTCHA bất chợt. Khi đó:
- **Nhìn cửa sổ Chromium** đã mở
- Tự tay bấm giải captcha (tích "I'm not a robot" hoặc chọn ảnh)
- Job sẽ tự tiếp tục sau khi captcha được giải

---

## 7. Chạy test

```bash
pip install pytest pytest-asyncio
pytest tests/
```

Hiện có 34 smoke tests cho `flow_web`.

---

## 8. Troubleshooting

| Triệu chứng | Nguyên nhân | Cách fix |
|---|---|---|
| `spawn UNKNOWN` khi launch Chromium | PATH có entry rỗng, hoặc path cài Chromium có khoảng trắng | Xoá `;` thừa cuối `Path`, dùng `scripts/run_flow_web.ps1` hoặc đặt `PLAYWRIGHT_BROWSERS_PATH=C:\pw-flow` rồi cài lại Chromium |
| `side-by-side configuration is incorrect` | Thiếu VC++ Redist hoặc path có khoảng trắng | `winget install Microsoft.VCRedist.2015+.x64` + cài Chromium vào `C:\pw-flow` |
| UI hiện "Chưa đăng nhập" dù đã đăng nhập | `flow-py` check cookies ở vị trí cũ | Patch `_storage.py` để check cả `Default/Network/Cookies` (Chromium mới) |
| "Google Flow chưa chuyển sang chế độ tạo ảnh" | UI tiếng Việt, selector không match "Image" | Đã fix trong `service.py` — nhận cả "Hình ảnh" |
| Tạo ảnh bị treo mãi ở "Kết nối Flow" | Browser cũ còn lock profile hoặc reCAPTCHA chưa giải | `taskkill /F /IM chrome.exe /T`, restart app, giải captcha khi hiện |
| Job hiển thị treo mãi ở UI | Đã fix — frontend chỉ hiện job đang chạy, ẩn failed/completed tự động |
| Toàn bộ app treo trên macOS, mọi request đều timeout | App tìm Chromium ở `~/.cache/ms-playwright` (đường dẫn Linux) nên luôn tưởng thiếu, rồi chạy `playwright install` chặn event loop | Đã fix trong `service.py` — macOS dùng `~/Library/Caches/ms-playwright`; phần cài đặt cũng chạy ở thread riêng |
| Dashboard báo "đã đăng nhập" nhưng job nào cũng 401 | `flow._storage.is_authenticated()` chỉ kiểm tra *có file* `Default/Cookies`, nên hồ sơ có phiên đã chết vẫn được tính là đăng nhập | Đã fix trong `service.py` — `get_auth_status` đọc thêm hạn của cookie `__Secure-next-auth.session-token` trong hồ sơ (chỉ đọc tên và hạn, không đọc giá trị); hồ sơ không đọc được thì giữ nguyên kết quả cũ |
| Job báo `HTTP 401 ... API keys are not supported by this API` | Phiên đăng nhập Flow hết hạn nên không lấy được Bearer token; app rơi về API key trần | Bấm **Đăng nhập Flow** trên dashboard (hoặc `POST /api/flow/open-login`) và đăng nhập lại trong cửa sổ Chromium vừa mở |
| `removelogo trả lỗi 503: ... can't open file '.../src/strip-ai-provenance.py': Operation not permitted` | macOS thu hồi quyền truy cập thư mục `Downloads` của tiến trình chạy removelogo (TCC) | Cấp lại quyền cho Terminal trong **System Settings → Privacy & Security → Files and Folders** (hoặc Full Disk Access) rồi `npm start` lại; trong lúc đó job vẫn chạy tiếp và giữ ảnh gốc. Chuyển hẳn thư mục `removelogo` ra ngoài `Downloads` thì hết lỗi này |
| Job đọc ảnh trên card ERP báo `Không tải được ảnh nguồn ERP (HTTP 403)` | Ảnh người dùng thả vào comment ERP nằm ở `/private/files/`, mà bước tải ảnh nguồn lại GET ẩn danh | Đã fix trong `service.py` — `_erp_download_attachment_bytes` đi qua endpoint download có xác thực của Frappe khi URL trỏ đúng host ERP; URL host khác vẫn tải ẩn danh, không kèm credential |
| Job chết ngay với `HTTP 400 INVALID_ARGUMENT on batchGenerateImages` | Google đổi cấu trúc request nên gọi API thẳng bị từ chối (không kèm chi tiết trường nào sai); trước đây chỉ lỗi reCAPTCHA mới có đường lui | Đã fix trong `service.py` — `_is_flow_api_argument_error` cho job chuyển sang tạo qua giao diện Flow như ca reCAPTCHA |
| Ảnh cuối trong lô lên ERP kèm log `ERP không nhận file ảnh N` | Frappe giới hạn số tệp đính kèm mỗi Task (mặc định 20), card dùng lại nhiều lượt sẽ đầy; ảnh đó chỉ còn URL Flow gốc nên **vẫn còn watermark** | Xoá bớt ảnh cũ trên card hoặc nâng giới hạn đính kèm của Task; log tổng kết đã đếm riêng số ảnh rơi vào ca này |

---

## 9. Ghi chú kỹ thuật

- `flow-py` là **browser automation**, không phải official API → Google có thể đổi UI bất cứ lúc nào
- Session và project lưu tại `~/.flow-py/`
- App state lưu tại `data/state.json`
- Trên Windows, tránh tự tay tắt cửa sổ Chromium giữa chừng — để app tự quản lý
- Headless mode không khuyến khích vì reCAPTCHA sẽ luôn fail
- Bản portable/release dành cho Windows dùng `scripts/run_flow_web_portable.ps1`, nên không phụ thuộc `.venv` của máy đích
