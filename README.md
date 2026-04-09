# Flow Web UI

Web app local điều khiển [flow-py](https://github.com/eddie-fqh/flow-py) qua giao diện trình duyệt. App bọc các luồng chính của `flow-py`: đăng nhập Google Flow, kiểm tra credits, sinh video/ảnh, image-to-video, extend, upscale, camera motion/position, insert/remove object, xem workflows và tải kết quả.

---

## 1. Yêu cầu hệ thống

| Mục | Yêu cầu |
|---|---|
| OS | Windows 10/11 hoặc macOS / Linux |
| Python | **3.11+** (bắt buộc, không chạy được trên 3.9/3.10) |
| Git | Cần để clone repo |
| Chromium | Sẽ do Playwright tự tải |
| Tài khoản Google | Đã được cấp quyền truy cập Google Flow (labs.google/fx) |
| Gemini API key | Tuỳ chọn — chỉ cần nếu muốn dùng Prompt AI dùng Gemini thật |

### ⚠️ Windows lưu ý đặc biệt

- **Path cài Chromium KHÔNG được có khoảng trắng.** Thư mục `C:\Users\HAVI GROUP\...` sẽ gây lỗi `side-by-side configuration is incorrect` / `spawn UNKNOWN`. Giải pháp: set biến môi trường `PLAYWRIGHT_BROWSERS_PATH=C:\pw` trước khi chạy `playwright install`.
- Cần **Microsoft Visual C++ Redistributable (x64)** mới nhất — Chromium yêu cầu.
- Biến môi trường `Path` **không được có entry rỗng** (dấu `;` thừa cuối chuỗi) vì sẽ gây Node.js `spawn UNKNOWN` khi Playwright launch browser.
- Các script `.sh` trong repo chỉ dùng cho macOS/Linux. Trên Windows dùng PowerShell hoặc các script `scripts/setup_windows.ps1`, `scripts/run_flow_web.ps1`.
- Google Flow dùng browser automation + reCAPTCHA → **chạy ở chế độ hiện cửa sổ (không headless)** ổn định hơn nhiều so với headless.

---

## 2. Cài đặt

### 2.1. Clone repo

```bash
git clone https://github.com/ph56jk/flow.git
cd flow
```

### 2.2. Cài Python 3.11 (nếu chưa có)

**Windows (winget):**
```powershell
winget install --id Python.Python.3.11 -e
```

**macOS:**
```bash
brew install python@3.11
```

### 2.3. Cài Microsoft Visual C++ Redistributable (chỉ Windows)

```powershell
winget install --id Microsoft.VCRedist.2015+.x64 -e
```

### 2.4. Tạo venv và cài dependencies

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

### 2.5. Cài Chromium cho Playwright

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

## 3. Cấu hình

### 3.1. File `.env.local` (ở root repo)

Tạo file `.env.local` với nội dung:

```env
# Bắt buộc trên Windows nếu đường dẫn user có khoảng trắng
PLAYWRIGHT_BROWSERS_PATH=C:\pw

# Tuỳ chọn — để dùng Gemini thật cho Prompt AI
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash
```

App sẽ tự nạp file này khi khởi động. Nếu không tạo Prompt AI sẽ dùng kho skill nội bộ.

### 3.2. File `~/.flow-py/config.json` (tự sinh sau lần đăng nhập đầu)

Đảm bảo `"headless": false` để cửa sổ Chromium hiện ra và giải reCAPTCHA khi cần:

```json
{
  "headless": false,
  ...
}
```

---

## 4. Chạy app

**Windows PowerShell:**
```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "C:\pw"
.\.venv\Scripts\Activate.ps1
python -m uvicorn flow_web.main:app --host 127.0.0.1 --port 8000 --reload
```

**Windows bash:**
```bash
PLAYWRIGHT_BROWSERS_PATH="C:\\pw" .venv/Scripts/python.exe -m uvicorn flow_web.main:app --host 127.0.0.1 --port 8000
```

**macOS / Linux:**
```bash
source .venv/bin/activate
uvicorn flow_web.main:app --reload
```

Mở trình duyệt: http://127.0.0.1:8000

---

## 5. Cách dùng lần đầu

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

## 6. Chạy test

```bash
pip install pytest pytest-asyncio
pytest tests/
```

Hiện có 34 smoke tests cho `flow_web`.

---

## 7. Troubleshooting

| Triệu chứng | Nguyên nhân | Cách fix |
|---|---|---|
| `spawn UNKNOWN` khi launch Chromium | PATH có entry rỗng, hoặc path cài Chromium có khoảng trắng | Xoá `;` thừa cuối `Path`, đặt `PLAYWRIGHT_BROWSERS_PATH=C:\pw` và cài lại Chromium |
| `side-by-side configuration is incorrect` | Thiếu VC++ Redist hoặc path có khoảng trắng | `winget install Microsoft.VCRedist.2015+.x64` + cài Chromium vào `C:\pw` |
| UI hiện "Chưa đăng nhập" dù đã đăng nhập | `flow-py` check cookies ở vị trí cũ | Patch `_storage.py` để check cả `Default/Network/Cookies` (Chromium mới) |
| "Google Flow chưa chuyển sang chế độ tạo ảnh" | UI tiếng Việt, selector không match "Image" | Đã fix trong `service.py` — nhận cả "Hình ảnh" |
| Tạo ảnh bị treo mãi ở "Kết nối Flow" | Browser cũ còn lock profile hoặc reCAPTCHA chưa giải | `taskkill /F /IM chrome.exe /T`, restart app, giải captcha khi hiện |
| Job hiển thị treo mãi ở UI | Đã fix — frontend chỉ hiện job đang chạy, ẩn failed/completed tự động |

---

## 8. Ghi chú kỹ thuật

- `flow-py` là **browser automation**, không phải official API → Google có thể đổi UI bất cứ lúc nào
- Session và project lưu tại `~/.flow-py/`
- App state lưu tại `data/state.json`
- Trên Windows, tránh tự tay tắt cửa sổ Chromium giữa chừng — để app tự quản lý
- Headless mode không khuyến khích vì reCAPTCHA sẽ luôn fail
