# Flow Web UI

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

### Windows

```powershell
git clone https://github.com/ph56jk/flow.git
cd flow
powershell -ExecutionPolicy Bypass -File .\scripts\run_flow_web.ps1
```

Script này sẽ tự:
- chọn ổ còn nhiều chỗ trống hơn để đặt runtime nếu `C:` gần đầy
- tự kéo Python portable nếu máy chưa có Python 3.11 chuẩn
- tạo `.venv` nếu chưa có
- cài dependencies nếu thiếu hoặc vừa pull code mới
- cài Chromium cho Playwright nếu chưa có
- mở app ở `http://127.0.0.1:8000`

### Windows portable: giải nén là chạy

Nếu không muốn mỗi máy lại tải Python, dependency và Chromium từ đầu, có thể build sẵn một bản portable ngay trên Windows:

```powershell
cd flow
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
- launcher `Flow Web UI.cmd`

Người dùng cuối chỉ cần:
1. copy hoặc giải nén thư mục đó sang máy Windows khác
2. double click `Flow Web UI.cmd`

Không cần clone repo, không cần cài Python, không cần chờ tải Chromium lại.

### Windows release zip: đóng gói để gửi cho người khác

Nếu muốn đóng thành một file zip để share:

```powershell
cd flow
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_release.ps1
```

Script này sẽ tạo:

```text
dist\flow-windows-release.zip
```

Người nhận chỉ cần:
1. tải file zip
2. giải nén
3. double click `Flow Web UI.cmd`

### macOS / Linux

```bash
git clone https://github.com/ph56jk/flow.git
cd flow
chmod +x ./scripts/run_flow_web.sh ./scripts/run_flow_web.command
./scripts/run_flow_web.sh
```

Nếu dùng macOS và thích double-click:
- mở [run_flow_web.command](./scripts/run_flow_web.command)

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
git clone https://github.com/ph56jk/flow.git
cd flow
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
# Tuỳ chọn trên Windows — mặc định script đã tự dùng C:\pw-flow
PLAYWRIGHT_BROWSERS_PATH=C:\pw-flow

# Tuỳ chọn — để dùng Gemini thật cho Prompt AI
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash
```

App sẽ tự nạp file này khi khởi động. Nếu không tạo Prompt AI sẽ dùng kho skill nội bộ.

### 4.2. File `~/.flow-py/config.json` (tự sinh sau lần đăng nhập đầu)

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

---

## 9. Ghi chú kỹ thuật

- `flow-py` là **browser automation**, không phải official API → Google có thể đổi UI bất cứ lúc nào
- Session và project lưu tại `~/.flow-py/`
- App state lưu tại `data/state.json`
- Trên Windows, tránh tự tay tắt cửa sổ Chromium giữa chừng — để app tự quản lý
- Headless mode không khuyến khích vì reCAPTCHA sẽ luôn fail
- Bản portable/release dành cho Windows dùng `scripts/run_flow_web_portable.ps1`, nên không phụ thuộc `.venv` của máy đích
