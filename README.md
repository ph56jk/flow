# Flow Web UI

Web app local de dieu khien [flow-py](https://github.com/eddie-fqh/flow-py) bang giao dien trinh duyet. App nay boc cac luong chinh cua `flow-py`: dang nhap Google Flow, kiem tra credits, sinh video/anh, image-to-video, extend, upscale, camera motion/position, insert/remove object, xem workflows va tai ket qua.

## Tinh nang

- Cau hinh `project_id`, che do browser, `cdp_url`, timeout va thu muc output
- Khoi dong luong dang nhap Google Flow tu web UI
- Text-to-video, text-to-image va image-to-video bang file upload
- Cac thao tac edit video: extend, upscale, camera motion, camera position, insert, remove
- Luu lich su job cuc bo de refresh trang van con thay
- Xem saved projects, workflows, credits va ket qua preview
- Tai ket qua ve may thong qua backend

## Yeu cau

- Python 3.10 tro len
- Playwright Chromium
- Tai khoan Google da duoc cap quyen truy cap Google Flow

## Chay tren Windows duoc khong?

Co. Phan web app chinh (`FastAPI` + `Pathlib` + `Playwright`) chay duoc tren Windows 10/11 neu co:

- Python 3.11+
- Git
- Chromium cho Playwright

Luu y:

- Cac script `.sh` trong repo la cho macOS/Linux.
- Tren Windows, nen dung PowerShell va cac script `scripts/setup_windows.ps1`, `scripts/run_flow_web.ps1`.
- Vi Google Flow dung browser automation + reCAPTCHA, nen che do mo browser that (khong headless) on dinh hon tren Windows.

## Tai repo tu GitHub

```powershell
git clone https://github.com/ph56jk/flow.git
cd flow
```

## Cai dat

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

Neu may chu nhan chua co `python3.11`, can cai Python 3.11 truoc. `flow-py` khong chay duoc tren Python 3.9.

### Cai dat tren Windows (PowerShell)

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\setup_windows.ps1
```

Neu khong muon dung script, co the chay tay:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m playwright install chromium
```

## Chay app

```bash
source .venv/bin/activate
uvicorn flow_web.main:app --reload
```

Mo `http://127.0.0.1:8000`.

### Chay app tren Windows

```powershell
.\scripts\run_flow_web.ps1
```

Hoac chay tay:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn flow_web.main:app --host 127.0.0.1 --port 8000 --reload
```

## Bat Gemini cho Prompt AI

Prompt AI mac dinh van chay bang kho skill noi bo. Neu muon no dung Gemini that de viet prompt, dat them bien moi truong truoc khi chay app:

```bash
export GEMINI_API_KEY="AIza..."
export GEMINI_MODEL="gemini-2.5-flash"  # tuy chon, mac dinh da la gemini-2.5-flash
uvicorn flow_web.main:app --reload
```

App cung chap nhan `GOOGLE_API_KEY` hoac `GOOGLE_GENAI_API_KEY` neu chu nhan da dung ten bien do tu truoc.
Hoac luu vao file `.env.local` o root du an, app se tu nap file nay luc khoi dong.

## Cach dung

1. Mo web UI va dien `Project ID`.
2. Bam `Save Config`.
3. Bam `Sign In With Google Flow` de backend mo Chromium dang nhap.
4. Sau khi dang nhap xong, dung cac form generate va edit.
5. Job se chay nen; khu vuc `Job Console` tu refresh de hien trang thai va preview.

## Luu y

- `flow-py` la browser automation, khong phai official API.
- Google co the doi giao dien bat cu luc nao.
- Headless co the fail vi reCAPTCHA; `Open Browser` la tuy chon an toan hon.
- Session va project luu trong `~/.flow-py`, con app state luu trong `data/state.json`.
