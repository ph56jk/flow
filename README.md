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
- Google Flow dùng browser automation + reCAPTCHA. Mặc định **hiện cửa sổ**, và lần đăng nhập đầu bắt buộc phải hiện. Sau khi đã đăng nhập, bật *Chạy ẩn, không hiện cửa sổ Chromium* trong phần **Thêm một chút** để cửa sổ không còn chen ngang lúc bạn làm việc khác — job vẫn dùng chung đúng một trình duyệt và vẫn xoay vòng profile như cũ. Nếu Google bắt đầu đòi reCAPTCHA liên tục thì tắt công tắc đó đi. Chạy ẩn luôn mở **bản Chromium đầy đủ** ở chế độ `--headless=new`, không phải `chrome-headless-shell` — bản rút gọn ấy mở được hồ sơ nhưng labs.google không cấp phiên đăng nhập cho nó, và app sẽ báo nhầm là hết hạn đăng nhập.

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
ERP sử dụng HaviGroup ERP qua HTTPS GraphQL: mở dashboard, đi tới **HaviGroup ERP**, nhập API key + API secret, điền mã **Project** (ví dụ `PROJ-0013`) rồi chọn Task nguồn. App chỉ đọc/ghi trong đúng project đang cấu hình — mọi Task ID gõ tay, graph import hay batch item đều bị kiểm tra lại theo giá trị này, nên phạm vi ảnh hưởng luôn gói trong một project. ERP Source đọc ảnh nguồn từ comment trên Task (kể cả file `/private/files/...` do người dùng đính qua web ERP — Flow v2 tải qua endpoint `download_file` có auth). Sau khi duyệt trên dashboard, Flow v2 đẩy ảnh đã xóa watermark lên chính ERP rồi gắn nó vào comment Task như **file đính kèm thật**, hiển thị inline đúng như khi người dùng kéo ảnh vào ô comment. **Thẻ chỉ nhận ảnh, không nhận chữ**: comment ảnh có thân rỗng (một ký tự vô hình, để ERP khỏi tự chèn "(đã đính kèm tệp)") còn dấu máy đọc (`[FLOW_V2_ARTIFACT]`, `[FLOW_V2_REVIEW job#idx]`) nằm trong trường `meta` của chính comment đó. Job thất bại **không** còn được ghi lên thẻ nữa — lý do nằm trong nhật ký lượt chạy và trên dashboard. App không tạo Task mới và không xóa Task; hai thao tác ghi duy nhất ngoài comment là đổi `status` của đúng thẻ đích (`Pending Review` khi đăng ảnh chờ duyệt, `Completed` khi ảnh đã duyệt vào thẻ) và gỡ đúng comment ảnh bị người duyệt bấm 👎 — xem [4.1d](#41d-duyệt-ảnh-ngay-trên-thẻ-erp--và-tự-động-chạy-idea).

Cơ chế gắn attachment gồm đúng hai bước, và **thứ tự cùng bộ field là bắt buộc** (đây chính là payload mà web ERP gửi):

1. `POST /api/method/upload_file` với `is_private=1`, `folder=Home`, `doctype=Task`, `docname=<task>`, `fieldname=comment`. Giá trị `fieldname=comment` là cờ "file đang chờ gắn vào comment kế tiếp"; thiếu nó thì bước 2 luôn trả `linked: 0`.
2. `addTaskComment(name, content, attachments: ["/private/files/..."])` với đường dẫn **tương đối** vừa nhận. ERP tự chuyển file sang `attached_to_field = comment:<comment_id>` và trả `linked: 1`.

Nếu `linked` vẫn bằng 0, Flow v2 ghi thêm một comment chứa URL tuyệt đối để ảnh không biến mất; hàm đọc lại nhận cả hai dạng (attachment thật và URL trong nội dung), nên số output cũ luôn đếm đúng và ảnh không bị tạo lại.

**Ảnh tạo ra nằm trong thread "Trả lời" của comment ảnh nguồn**, đúng luồng người dùng mong đợi: thả ảnh vào card → mọi ảnh Flow tạo ra nằm gọn trong thread của chính comment đó thay vì thành một dãy comment rời. Mutation GraphQL `addTaskComment` **không có tham số cha** (trường `meta` chỉ được lưu nguyên văn, không tạo thread — chính vì lưu nguyên văn nên nó là chỗ cất dấu máy đọc), nên Flow v2 gọi đúng whitelisted method mà nút "Trả lời" của web ERP dùng:

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

**Ảnh đi lên ERP được xoá watermark hai lần, không phải một.** Bước nâng 2K gửi ảnh quay lại Google, và Google đóng watermark lên bản trả về — nên một tấm ảnh đã sạch trên đĩa vẫn có thể tới thẻ ERP kèm dấu. Vì vậy **mọi** file 2K sắp upload đều đi qua removelogo lần nữa, không hỏi trước, rồi mới đo; còn dấu thì bộ vá cục bộ (`watermark_repair`) mới vào cuộc. Ảnh vốn sạch thì removelogo trả `422` và file quay về nguyên vẹn, nên không mất gì.

Trước đây bước này *đo trước rồi mới quyết định có gọi removelogo hay không*, và đó chính là lỗi để lọt dấu: trên nền gỗ hoặc vải lanh, bộ đo cục bộ chỉ đọc được 0.10–0.24 — dưới ngưỡng `MIN_STRENGTH = 0.25` — trong khi ngôi sao Gemini nằm rõ mồn một ở góc ảnh, nên cả thẻ ảnh vẫn lên ERP kèm dấu dù bộ xóa mạnh chưa từng được nhìn tới file đó. Đừng đưa phép đo cục bộ trở lại làm cổng chặn.

removelogo gỡ metadata AI (C2PA/XMP/EXIF) **trước** khi tìm watermark hiển thị, và khi bước hiển thị không sửa được gì nó vẫn trả `200` kèm file chỉ-gỡ-metadata. Flow v2 vì thế so pixel file trả về với ảnh gốc: giống hệt nhau thì artifact ghi `metadata_only` (không phải `cleaned`) và log job cảnh báo "chỉ gỡ được metadata, watermark hiển thị vẫn còn". File đó vẫn là file được gửi lên ERP vì nó đã sạch metadata, chỉ là trạng thái không được phép nói quá. Đặt `REMOVE_LOGO_ENABLED=false` để bỏ hẳn bước này. Công cụ chỉ xóa watermark Gemini và metadata AI (C2PA/XMP/EXIF) do chính Google gắn vào ảnh bạn tạo ra — không dùng cho ảnh của người khác.

Tài liệu ERP chính thức ưu tiên `Authorization: HVGToken <raw-token>`. Cặp API key/API secret được cấp cho luồng này đã được xác nhận chỉ-đọc qua cơ chế tương thích Frappe `Authorization: token <key>:<secret>`; chúng không thể tự chuyển thành raw HVG token. Khi công ty cấp raw HVG token, hãy chuyển integration sang header chính thức đó thay vì suy diễn token từ cặp key/secret.

### 4.1c. Chạy ảnh cho từng idea (Phân rã công việc → mỗi thẻ con là 1 idea)

Luồng người dùng ERP mô tả: một thẻ **Idea** cha giữ ảnh sản phẩm gốc (kể cả khi ảnh đó chỉ là **ảnh bìa** của thẻ), phần **PHÂN RÃ CÔNG VIỆC** tách mỗi idea thành một thẻ con riêng ở cột *Cần làm*. Ảnh content chạy cho idea "a" phải nằm trong chính thẻ "a", không dồn hết về thẻ cha.

**Thả ảnh là xong — thẻ con tự sinh.** Không phải tự tay bấm "Phân rã công việc" nữa: mỗi ảnh người dùng thả lên thẻ Idea cha (kéo vào thẻ, đính vào comment, hay dán vào khung đính kèm) sẽ tự thành **một thẻ con `Idea N`** ở trạng thái *Open*, mang đúng tấm ảnh đó và lấy nó làm **ảnh bìa** của thẻ con. Ngay sau đó lượt chạy hiện tại xếp job cho các thẻ vừa sinh luôn, nên thả ảnh xong là ảnh content bắt đầu chạy.

- **Ảnh sản phẩm không bị đem đi chạy.** Ảnh bìa của thẻ cha là ảnh sản phẩm gốc — thứ mà mọi idea đều là ảnh *của nó* — nên nó đứng ngoài; thẻ cha không có ảnh bìa thì ảnh cũ nhất đóng vai đó. Thẻ chỉ có mỗi ảnh sản phẩm thì không sinh thẻ con nào.
- **Không sinh trùng, và không viết chữ nào lên thẻ.** Thẻ con chỉ nhận đúng tấm ảnh; chỗ giữ chỗ chính là tấm ảnh ấy — ảnh bìa và tệp đính kèm của thẻ con vẫn trỏ về đúng đường dẫn của ảnh gốc trên thẻ cha, vì ERP dùng lại tệp cũ khi bản sao trùng từng byte. Sổ nhận ảnh vì thế nằm ngay trên thẻ con chứ không nằm trong state của app: xoá tay một thẻ con thì ảnh đó thật sự quay lại hàng đợi và được sinh lại, còn quét bao nhiêu lần cũng không đẻ thêm thẻ. Dấu `[FLOW_V2_IDEA src=...]` đời cũ vẫn được đọc tiếp cho những thẻ sinh ra trước đây, nhưng không còn được ghi mới.
- Dấu này **cố tình khác** `[FLOW_V2_ARTIFACT]`: ảnh chỉ được *chở sang* thẻ con chứ không phải ảnh Flow tạo ra, gắn nhầm dấu artefact thì thẻ con sẽ bị coi là "đã có ảnh Flow" và không bao giờ chạy.
- Ảnh thả thẳng vào khung đính kèm của thẻ nằm ở chỗ `taskDetail` **không** trả về, nên app đọc thêm `taskAttachments` cho thẻ cha. Ảnh bìa thẻ con phải upload lại kèm `purpose: "cover"` rồi mới `setTaskCover` được — ERP từ chối đặt bìa bằng file chỉ treo ở comment.
- Tắt bằng env `ERP_IDEA_INTAKE=0` (mặc định bật). Tắt rồi thì thẻ con vẫn phải tạo tay như trước.

Trong sidebar **Chạy ảnh cho từng idea**: điền mã thẻ Idea cha (ví dụ `TASK-2026-00202`), số ảnh mỗi idea (mặc định 12) rồi bấm **Chạy ảnh cho các idea**. Tương đương API:

```
POST /api/erp/idea-batch
{"task_id": "TASK-2026-00202", "count": 12, "include_done": false, "child_task_ids": []}
→ {"parent_task_id": ..., "project_id": ..., "created": [{"task_id", "subject", "image", "source"}], "queued": [{"job_id", "task_id", "subject"}], "skipped": [...]}
```

Mỗi thẻ con thành một job riêng, chạy **nhiều thẻ cùng lúc — số thẻ app tự tính theo CPU của máy**: mỗi thẻ tính 2 nhân, chừa 2 nhân cho Chrome và app, trần tự động là `3`. Máy 10 nhân ra `3`, máy 6 nhân ra `2`, máy 4 nhân trở xuống ra `1`. Muốn ép thì đặt `ERP_IDEA_CONCURRENCY` (tối đa `4`, `1` để chạy tuần tự, để trống hoặc `auto` để máy tự tính). Mỗi lượt chạy đều ghi vào log số thẻ song song và số nhân CPU đọc được.

Cần nói rõ con số này **không** làm tăng số ảnh đang được *tạo* cùng lúc. Chỉ có một trình duyệt và một phiên Flow, các thẻ vẫn xếp hàng trước panel Agent (xem đoạn dưới). Muốn tạo ảnh song song thật thì phải có thêm **profile Flow** (`FLOW_CHROME_PROFILE_DIRS`), không phải thêm nhân CPU. Cái con số này chia là phần còn lại của mỗi thẻ — xóa watermark, mã hóa lại ảnh, upload lên ERP — và đó mới là phần chiếm phần lớn thời gian.

Trần tự động để `3` chứ không phải `4` là có lý do: ERP đã trả `502` của Cloudflare khi bị dồn, nên để 4 thẻ upload cùng lúc là cách dở để biết giới hạn của nó. Ai cần cái thứ tư thì đặt tay.

1. Ảnh nguồn lấy từ **chính thẻ con** — comment, attachment, hoặc `cover_image` của nó. Trên board thật, idea *là một tấm ảnh*: thẻ con chỉ tên `c` nhưng ảnh bìa mới là mẫu thêu cần chạy content. Thẻ con nào chưa có ảnh riêng mới mượn ảnh của thẻ **cha**.
2. Prompt ghép từ tiêu đề + mô tả của thẻ **con** cộng bối cảnh mô tả của thẻ cha.
3. Ảnh chạy xong dừng ở **bước duyệt trên dashboard** — đúng yêu cầu "nhớ có nút duyệt/bỏ để check ảnh". Chưa duyệt thì không có gì được ghi lên ERP.
4. Ảnh được duyệt mới được gửi vào comment của **chính thẻ con** đó; ảnh bị từ chối không bao giờ rời khỏi máy.

Vẫn chỉ có **một trình duyệt và một phiên Flow**: `_with_client` giữ khoá phiên suốt mọi lần gọi *có điều khiển trang*, nên các thẻ vẫn xếp hàng trước panel Agent và không thể lấy nhầm ảnh của nhau.

Phần chạy song song là phần không cần tới trang: nâng 2K, xóa watermark và upload lên ERP. Riêng bước nâng 2K trước đây mới là chỗ nghẽn — nó chiếm ~5 phút rưỡi mỗi thẻ mà vẫn giữ khoá, khiến thẻ thứ hai gần như phải chờ hết thẻ thứ nhất. Nay `_upsample_artifacts_bytes` gọi `_with_client(..., hold_session_lock=False)`: mở và kiểm tra trang xong là **trả khoá ngay**, phần còn lại chỉ là `POST flow/upsampleImage` qua `client._api` (HTTPS bằng request context của trình duyệt, không đụng DOM). Nhờ vậy thẻ sau bắt đầu tạo ảnh ngay trong lúc thẻ trước còn đang nâng 2K và đăng comment.

Ngoại lệ duy nhất là `_upsample_image_via_flow_ui_download` — đường dự phòng cuối, có bấm trên trang thật — nên nó **lấy lại khoá phiên** rồi mới lấy `_flow_upsample_ui_lock`, đúng thứ tự đó và không bao giờ ngược lại (đảo thứ tự sẽ kẹt khoá chéo với đường nâng 2K một ảnh).

Một ngoại lệ nữa nằm ngay trong lời gọi nâng 2K: **token reCAPTCHA**. `_client_context` đúc token bằng `page.evaluate` và có thể *tải lại trang* khi lần đọc đầu rỗng — mà lúc đó khoá phiên đã trả rồi, nên nó đang chạy trên đúng trang thẻ sau đang tạo ảnh. Google trả lại `HTTP 403 ... reCAPTCHA evaluation failed`, và đó là nguyên nhân của **mọi** ảnh không lên được 2K trên board thật (không phải bị bóp băng thông, cũng không phải media cũ). Nay `_flow_upsample_client_context` chỉ ôm `_browser_session_lock` cho **riêng bước đúc token** — và chỉ khi người gọi đã trả khoá — còn lời gọi nâng 2K vẫn nằm ngoài khoá. Kèm theo đó, token bị từ chối không còn là dấu chấm hết: `_upsample_image_via_flow` chạy theo **lượt** (`FLOW_UPSAMPLE_RECAPTCHA_ROUNDS`, mặc định `3`), mỗi lượt đúc token mới, và chỉ thử lại khi lỗi đúng là token — lỗi khác thì token mới cũng hỏng y hệt nên dừng luôn.

Ảnh đã lỡ ở 1024 thì **không sửa lại được**: gọi nâng 2K trên media cũ chỉ nhận về đúng ảnh gốc. Đường duy nhất là xoá comment duyệt đó rồi tạo ảnh mới. Đừng dùng `erp-review/publish` để vá — nó đăng bù **mọi** chỉ số artifact chưa có comment trên thẻ, kể cả những chỗ đã xoá từ lâu; một lần gọi định thay một ảnh đã đăng thành sáu và đẩy thẻ từ 12 lên 17 tệp (trần của một Task là ~19–20 tệp).

Vì đích ghi khác thẻ nguồn, ảnh của idea nằm ở comment cấp một của thẻ con (không chui vào thread trả lời của comment ảnh nguồn trên thẻ cha). Truyền `child_task_ids` để chỉ chạy vài idea cụ thể.

**Thẻ nào bị bỏ qua.** Trước khi xếp job, app đọc chi tiết từng thẻ con và bỏ qua thẻ đã chạy rồi, kèm lý do trong `skipped[].reason`:

| Lý do | Ý nghĩa |
| --- | --- |
| `đã có ảnh Flow` | Thẻ con đã có comment mang dấu `[FLOW_V2_ARTIFACT]` — ảnh duyệt xong đã nằm trên thẻ. |
| `đang có ảnh chờ duyệt trên thẻ` | Thẻ con đang có comment mang dấu `[FLOW_V2_REVIEW ...]` chưa ai 👍/👎. |
| `đã có lượt chạy trong app` | Đã có job trong app trỏ `erp_output_task_id` về thẻ này và job đó chưa `failed`/`cancelled`. |
| `chưa có ảnh nguồn (thẻ con không có ảnh riêng, thẻ cha cũng không có ảnh)` | Thẻ con không có ảnh nào để chạy và thẻ cha cũng không có ảnh để cho mượn. Chỉ thẻ đó bị bỏ, các thẻ con khác vẫn chạy bình thường. |
| `thẻ con chưa có nội dung idea (tiêu đề/mô tả trống)` | Thẻ con **không có ảnh riêng** và tiêu đề + mô tả cộng lại chưa tới 8 ký tự (ví dụ thẻ chỉ tên là `c`). Nó sẽ mượn ảnh thẻ cha với prompt giống hệt mọi thẻ trống khác, nên cả board ra cùng một bộ ảnh. Thẻ chỉ có ảnh bìa, không có chữ, vẫn chạy bình thường. |

Ba lớp này chặn đúng trường hợp hay tạo trùng nhất: thẻ vừa được đăng 12 ảnh chờ duyệt mà chưa ai bấm nút thì lần chạy sau không đăng thêm 12 ảnh nữa. Job đã `failed` thì thẻ được chạy lại bình thường. Bật **Chạy lại cả thẻ con đã có ảnh Flow** (`include_done: true`) để bỏ qua cả ba lớp kiểm tra.

**Thẻ kẹt được tự vá.** Ba lớp trên chặn theo *lượt chạy*, nên một lượt hỏng dở lại khoá thẻ vĩnh viễn: job ghi `completed` mà ảnh không lên được thẻ (mạng rớt giữa chừng là đủ) thì từ đó không ai nhìn tới thẻ đó nữa. Mỗi vòng của watcher — và mỗi lượt agent bot — chạy một bước vá trước khi tìm thẻ mới, đúng hai chỗ hỏng:

| Chỗ hỏng | Cách vá | Tốn quota Flow? |
| --- | --- | --- |
| Ảnh **đã tạo** mà chưa lên thẻ | Đăng bù đúng bộ ảnh cũ (`publish_erp_review`) | Không |
| Ảnh **chưa từng được tạo** (job hứa 12, trả về 1) | Xếp một lượt mới cho đúng phần thiếu (11), không chạy lại cả 12 | Có |

Bước vá cố ý nhát tay, vì chồng thêm một bộ ảnh lên thẻ người ta đang duyệt là hỏng hơn cả để nguyên:

- Thẻ đã `Completed` đứng ngoài — người ta chốt xong rồi.
- Chỉ đăng bù cho **đúng lượt đang chiếm mặt thẻ**, hoặc cho lượt mới nhất khi thẻ trắng trơn *và* chưa ai quyết tấm nào của nó. Thẻ trắng vì người duyệt vừa 👎 hết thì lượt ấy có quyết định rồi, nên nó không bị đăng lại; một lượt cũ hơn cũng không được lôi lên thay chỗ.
- Phần thiếu đo ở **chỗ ảnh sinh ra**, không đo trên mặt thẻ: một tấm bị 👎 vẫn là một tấm đã tạo, nên nó không phải chỗ thiếu và không sinh ra lượt chạy bù nào.
- Quá `ERP_IDEA_TOPUP_MAX_JOBS` (3) lượt cho cùng một thẻ thì thôi bù: chạy mãi vẫn thiếu nghĩa là chỗ hỏng không nằm ở đây. Tắt hẳn phần chạy bù bằng `ERP_IDEA_TOPUP=0`.

Chạy tay một lượt vá: `POST /api/erp/idea-batch/repair`.

**Lịch sử lượt chạy không được nuốt ảnh chưa lên thẻ.** App chỉ giữ 50 lượt chạy gần nhất, nhưng một lượt còn ảnh chưa giao cho thẻ ERP thì **ở lại quá hạn mức** (trần tuyệt đối 500): hồ sơ lượt chạy là thứ duy nhất biết mười hai tấm ảnh ấy nằm ở đâu, cắt nó đi là cắt luôn đường đăng bù và thẻ trắng vĩnh viễn trong khi ảnh vẫn nằm trên đĩa.

### 4.1d. Duyệt ảnh ngay trên thẻ ERP (👍/👎) và tự động chạy idea

Ảnh chạy xong **tự** được đăng lên chính thẻ đích (không cần bấm gì), **mỗi ảnh một comment**. Comment đó **không mang chữ nào** — thân của nó là một ký tự vô hình còn dấu `[FLOW_V2_REVIEW job#idx]` nằm trong trường `meta`, nên thẻ nhìn vào chỉ thấy một dãy ảnh. Đây là mắt xích khiến luồng tự động thật sự khép kín: bước duyệt vẫn bắt buộc, nhưng nó diễn ra trên thẻ chứ không nằm chờ trong app. Tắt bằng `ERP_REVIEW_AUTOPUBLISH=0` (khi đó phải bấm **Đăng ảnh lên ERP để duyệt** thủ công). Đăng lại nhiều lần không tạo bản sao — ảnh đã có comment hoặc đã có quyết định đều bị bỏ qua. Người duyệt trả lời ngay dưới ảnh đó:

- 👍 (hoặc `DUYỆT`, `OK`, `YES`) → ảnh được duyệt, đi tiếp vào bước ghi `[FLOW_V2_ARTIFACT]`.
- 👎 (hoặc `BỎ`, `NO`) → ảnh bị loại **và comment ảnh đó bị gỡ khỏi thẻ** qua `hvg_workspace.api.delete_task_comment`. Thao tác này không hoàn tác được. App **không** viết gì lên thẻ để xác nhận: ảnh được duyệt thì nó ở lại, ảnh bị bỏ thì comment của nó biến mất — thẻ tự nó đã là câu trả lời. Dấu vết ai quyết gì nằm trong nhật ký lượt chạy và trên dashboard.

Không trả lời cũng được: **hai nút 👍/👎 ngay trên comment ảnh** (ERP mới thêm) được đọc như một câu trả lời — nhiều 👎 hơn 👍 là loại, ngược lại là duyệt. Trả lời bằng chữ vẫn được ưu tiên hơn nút, vì nó cho biết ai quyết và vì sao. **Hoà phiếu (kể cả 2-2) cố ý là chưa ngã ngũ**, để một thao tác không hoàn tác được không rơi vào thế 50-50. Cách này áp dụng cho cả ảnh đã đăng từ trước, không cần đăng lại.

Hai nút trên dashboard (**👍 Thích** / **👎 Không thích**) chạy đúng logic đó. Quyết định là bất biến — một ảnh chỉ nhận một quyết định — và ảnh bị máy loại ở bước kiểm watermark (`source="watermark_gate"`) **không** bị xóa khỏi thẻ, để còn mở lại được.

Người duyệt chỉ cần trả lời trên thẻ, không phải mở app: một watcher nền đọc lại các thẻ theo chu kỳ `ERP_REVIEW_POLL_SECONDS` và áp dụng quyết định. Nó chỉ theo dõi job nào còn giữ sổ `result["erp_review"]` (mỗi ảnh một comment id) — job mất sổ này là job người duyệt trả lời vào chỗ không ai đọc. Vì bước đăng ảnh ghi thẳng sổ đó vào job trong lúc các module còn đang chạy, kết quả cuối lượt phải gộp lại bằng `_result_with_module_side_writes` chứ không ghi đè bằng bản chụp cũ.

Trạng thái thẻ đích tự đi theo luồng duyệt (best-effort, thất bại chỉ ghi log job chứ không làm hỏng job):

1. Đăng ảnh chờ duyệt → thẻ chuyển sang **Đang review** (`Pending Review`).
2. Ảnh đã duyệt được ghi vào thẻ → thẻ chuyển sang **Hoàn thành** (`Completed`).

Thẻ đang ở `Cancelled` (hoặc đã `Completed`) không bị đụng vào; thẻ bị 👎 hết ảnh cũng không được đẩy lên `Completed`.

**Tự động chạy idea.** Một watcher nền quét thẻ Idea **cha đang cấu hình trong panel ERP** theo chu kỳ và tự xếp job cho các thẻ con chưa chạy, dùng đúng bộ lọc ở bảng trên. Watcher đứng im khi chưa cấu hình thẻ cha, chưa có key/secret, hoặc khi đang có một lượt chạy khác (một trình duyệt, một phiên Flow). Chạy tay một lượt quét:

```
POST /api/erp/idea-batch/auto
→ {"parent_task_id": ..., "queued": [...], "skipped": [...], "reason": ""}
```

Điều chỉnh bằng env: `ERP_IDEA_AUTORUN_SECONDS` (mặc định `180`, đặt `0` để tắt hẳn) và `ERP_IDEA_AUTORUN_COUNT` (số ảnh mỗi idea; bỏ trống hoặc `0` thì dùng mặc định của app).

### 4.1e. Agent bot: thả bot vào thẻ ERP là nó tự chạy

Mục **Agent Bot** trên ERP (Vault) phát cho mỗi bot một token riêng. **Thêm bot vào một dự án là toàn bộ phần cấu hình** — không phải gắn vào từng thẻ: bot tự tìm mọi **thẻ Idea** của dự án đó (thẻ còn mở và có thẻ con, hoặc là thẻ nhóm), tự xếp job tạo ảnh, và tự dọn ảnh theo phiếu 👍/👎.

Muốn chỉ chạy đúng một thẻ thì **gắn bot vào thẻ đó**: hễ trong dự án có thẻ gắn đích danh bot, dự án ấy thu về đúng những thẻ đó. Nói rõ thắng suy đoán. Đặt `ERP_AGENT_SCOPE=card` nếu muốn bot **chỉ** làm việc khi được gắn vào thẻ.

**Gắn vào thẻ cha là gắn cho cả cụm.** Chọn agent ở ô *Người phụ trách* của thẻ cha thì mọi thẻ con của nó cũng được gắn theo — thẻ con đã có sẵn được bot khâu lại ở lượt quét kế, còn thẻ con do phần nhận ảnh vừa sinh ra thì mang agent ngay từ lúc tạo. Chỉ lan **xuống**, không bao giờ lan lên: gắn vào một thẻ con là cố ý chỉ đúng thẻ ấy, tự tiện gắn ngược lên thẻ cha sẽ kéo theo cả những thẻ con khác không ai chọn. Thẻ con đã mang agent thì lượt quét vẫn chỉ chạy thẻ cha — cây của thẻ cha đã chứa sẵn bình luận của con, để con chen vào thì trần `ERP_AGENT_MAX_CARDS_PER_SCAN` bị chính đám con ăn hết.

- **👎 là xoá, 👍 là giữ.** Bot đọc `like_count`/`dislike_count` của từng ảnh nó đã đăng: nhiều 👎 hơn 👍 thì gỡ ảnh khỏi thẻ, ngược lại thì giữ. **Hoà phiếu — kể cả 3-3 — cố ý là chưa ngã ngũ**, vì xoá không hoàn tác được. Quyết định **không** để lại ghi chú trên thẻ: người duyệt vừa tự bấm nút nên đã biết mình quyết gì, còn một dòng "đã gỡ" cho mỗi ảnh thì chính nó thành thứ phải cuộn qua. Vết tích nằm ở log của app và log của job trên dashboard.
- **Chỉ ảnh của chính bot.** ERP chỉ cho xoá comment của chính mình, nên bot chỉ nhận việc với comment có `mine = 1`. Ảnh do luồng cũ đăng dưới danh tính người thật thì bot đọc được phiếu nhưng không dọn được — muốn "👎 là xoá" chạy thật thì chính bot phải là người đăng ảnh.
- **Tự chạy tạo ảnh.** Thẻ Idea được đẩy sang `enqueue_erp_idea_jobs` (đúng bộ lọc ở mục 4.1c, thẻ con đã có ảnh vẫn bị bỏ qua). Thẻ đã **Hoàn thành/Huỷ** thì bỏ qua. Thẻ chưa có thẻ con nào cũng bỏ qua — **trừ khi** trên mặt thẻ đã có từ 2 ảnh trở lên, tức là người dùng vừa thả ảnh idea vào: thẻ đó được chạy để phần nhận ảnh sinh thẻ con cho từng tấm (mục 4.1c). Ảnh **kéo thẳng vào thẻ** không hiện trong `taskFull`, chỉ dòng thẻ trên bảng mới có `attachment_count`; bot giữ lại dòng bảng đó khi đọc cây thẻ, nếu không thì thẻ vừa được thả đầy ảnh lại đếm ra 0 và không ai nhận. Mỗi lượt quét chỉ khởi động tối đa `ERP_AGENT_MAX_CARDS_PER_SCAN` thẻ (mặc định 3) — cả app chỉ có một phiên Flow — phần còn lại để lượt sau và được ghi log. Mỗi thẻ chỉ chạy lại sau `ERP_AGENT_AUTORUN_COOLDOWN_SECONDS`.
- **Phạm vi do ERP quyết.** Board nào đã thêm bot thì mọi thẻ Idea trong đó chạy được — kể cả board vừa thêm hôm nay, không phải khai lại ở đâu cả. Gỡ bot khỏi một dự án là nó hết thấy dự án đó ngay lượt sau. `ERP_AGENT_PROJECTS` chỉ để **thu hẹp** lại, để trống là rộng nhất; `ERP_PROJECT_ID` luôn được tính kèm.
- **Hàng rào của app đọc chung sổ ấy.** Trước đây Flow v2 có hàng rào dự án riêng, nên một board bot thấy mà chưa khai trong `.env.local` thì bot dọn phiếu được nhưng app từ chối tạo ảnh. Nay hàng rào lấy luôn phạm vi lượt quét gần nhất của bot (ghi trong `agent_bot_state.json`, nên còn nguyên sau khi khởi động lại) — hai bên không thể lệch nhau nữa. Bot chưa quét lượt nào trên máy mới tinh thì phạm vi rơi về đúng `ERP_PROJECT_ID` như cũ.

Cấu hình trong `.env.local` (xem chú thích đầy đủ trong `.env.local.example`):

```
ERP_AGENT_TOKEN=...                 # bắt buộc; bỏ trống là tắt hẳn agent bot
ERP_AGENT_BOT_USER=agent-<tên>@bots.hvg.internal
# ERP_AGENT_PROJECTS=PROJ-0013      # bỏ trống = mọi dự án bot nhìn thấy
ERP_AGENT_SCOPE=                    # bỏ trống = board; "card" = chỉ thẻ được gắn
ERP_AGENT_MAX_CARDS_PER_SCAN=3
ERP_AGENT_POLL_SECONDS=120
ERP_AGENT_AUTORUN=1
ERP_AGENT_DRY_RUN=0
```

Token này **không phải** cặp `ERP_API_KEY`/`ERP_API_SECRET`: nó dùng lược đồ `Authorization: HVGToken` và chỉ mở đúng endpoint GraphQL, trần 60 request/phút. Bỏ trống `ERP_AGENT_BOT_USER` thì bot tự nhận ra chính mình, nhưng lượt dò cuối cùng phải ghi rồi xoá một bình luận kỹ thuật trên thẻ — điền vào là khỏi.

Bot chạy sẵn trong app. Chạy tay một lượt:

```
POST /api/agent-bot/run
→ {"enabled": true, "bot_user": ..., "projects": [...], "tasks": [...], "kept": 0, "deleted": 0}
```

Hoặc chạy đứng riêng, không cần mở giao diện — nên bắt đầu bằng lượt chạy khô khi mới cắm bot vào một dự án lạ:

```
python scripts/run_agent_bot.py --once --dry-run
python scripts/run_agent_bot.py --flow-web-url http://127.0.0.1:3170
```

Không có `--flow-web-url` thì script chỉ dọn phiếu: cả app chỉ có một phiên trình duyệt nên việc xếp hàng tạo ảnh phải nằm ở đúng một chỗ.

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

File này là của thư viện `flow-py`, không phải công tắc của app. Chế độ ẩn/hiện
mà app dùng nằm ở `headless` trong `data/state.json`, bật tắt bằng công tắc
*Chạy ẩn, không hiện cửa sổ Chromium* ở phần **Thêm một chút**. Cửa sổ đăng nhập
Google thì luôn hiện, dù công tắc ấy đang bật.

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
