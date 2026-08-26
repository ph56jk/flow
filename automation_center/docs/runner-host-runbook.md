# Runbook host runner — Content, Listing 2 ERP, Agent điều phối

**Host chính: PC `100.75.125.80`.** MacBook giữ vai trò dự phòng.

Ba runner chạy song song trên PC, mỗi cái một `runner_key` riêng:

| Runner | `runner_key` | File `.env` | Bot |
| --- | --- | --- | --- |
| Content Image | `content-image-runner` | `runner\.env` | `content-image-agent-runner` |
| Listing 2 ERP | `listing2-erp-runner` | `runner\listing2-erp.env` | `listing2-erp-agent-runner` |
| Agent điều phối | `orchestrator-runner` | `runner\orchestrator.env` | — (không gắn bot, xử lý yêu cầu sửa code) |

Chỉ chạy **một** tiến trình cho **mỗi** `runner_key` tại một thời điểm — hai
tiến trình cùng key sẽ tranh nhau claim job. Runner khác key thì chạy chung
máy vô hại. launchd runner trên Mac **cố ý chưa bootstrap**.

Các runner **không dùng chung file `.env`**: nếu dùng chung, runner nào khởi
động sau cũng đọc `AUTOMATION_RUNNER_KEY` của runner kia và cướp job của nó.
`run-listing2-erp-runner.ps1` và `run-orchestrator-runner.ps1` từ chối khởi
động nếu key không đúng.

Không có secret nào nằm trong repo, plist, Scheduled Task hay log. Secret chỉ ở
các file `.env` với quyền giới hạn trên từng máy.

---

## 1. Trạng thái hiện tại

| Hạng mục | Trạng thái |
| --- | --- |
| Worker | ✅ đã deploy `49de0199` (2026-08-16) — kèm Agent điều phối + watchdog |
| Migration D1 | ✅ `0001`–`0005` đã áp dụng lên remote (`0004`+`0005` áp 2026-08-16) |
| `RUNNER_SHARED_SECRET` | ✅ đã sinh 48 ký tự, đặt trên Worker, đồng bộ sang `.env` của cả Mac và PC |
| Flow v2 trên PC | ✅ chạy `127.0.0.1:8000` qua Scheduled Task S4U, **headless = true** |
| Đăng nhập Google Flow trên PC | ✅ `auth: true`, project `42f50a6f-5ab5-407b-ade1-eb6c23158377` |
| Runner Content Image | ✅ chạy, heartbeat, bot ở trạng thái `paused` |
| Runner Listing 2 ERP | ✅ chạy, heartbeat, bot tự chuyển `needs_runner` → `paused` |
| Flow v2 trên Mac | ✅ chạy `127.0.0.1:8000` qua launchd |
| Cloudflare Access Service Token | ✅ `content-image-runner`, **hết hạn 2027-08-13** (dùng chung cho cả hai runner) |
| Policy Service Auth | ✅ `Content Image Runner Service Auth` (`6a0e2e2c-fd45-4d0e-8b20-0980faa894e8`) gắn vào app Automation HaviGroup |
| Nghiệm thu tạo ảnh + nút Dừng | ❌ chưa (cần người bấm nút vì `botAction` đòi SSO) |
| Nghiệm thu ghi ảnh về ERP | ❌ chưa chạy thật (project đích giờ là `PROJ-0013`, không còn `PROJ-0049`) |
| Agent điều phối — code | ✅ Worker, migration `0004`, runner, UI, test quyền (12/12) đã xong ở máy dev |
| Agent điều phối — migration + deploy | ✅ đã áp `0004` + deploy 2026-08-16 |
| Runner Agent điều phối trên PC | ❌ chưa cài (xem mục 5.H) |
| Watchdog sức khoẻ | ✅ đã deploy, cron `*/5 * * * *` (xem mục 4) — **chưa đặt `ALERT_WEBHOOK_URL`** |
| PC chạy cố định 24/7 | ⚠️ `set-always-on.ps1` đã chạy 2026-08-20 (sleep/hibernate/disk/monitor = 0, `hibernate off`, Fast Startup off, NIC không bị Windows tắt, Tailscale Automatic). **Còn lại đúng một mục: BIOS `AC BACK = Always On` — phải có người tại chỗ.** |

---

## 2. PC `100.75.125.80` — host chính

### Truy cập

SSH thông qua Tailscale bằng key `~/.ssh/PC_Admin_ed25519`. Alias đã có trong
`~/.ssh/config`:

```sh
ssh hvg-pc
```

Shell mặc định trên PC là `cmd.exe`. **Đừng viết lệnh PowerShell nhiều tầng nháy
qua SSH** — quoting sẽ hỏng âm thầm. Hãy `scp` một file `.ps1` rồi chạy:

```sh
scp foo.ps1 hvg-pc:C:/HaviGroup/foo.ps1
ssh hvg-pc "powershell -NoProfile -ExecutionPolicy Bypass -File C:\HaviGroup\foo.ps1"
```

### Bố trí

| Thành phần | Vị trí |
| --- | --- |
| Source | `C:\HaviGroup\flow-v2` (không kèm `data/`, không kèm secret) |
| Workspace của agent | `C:\HaviGroup\agent-workspace\flow-v2` — bản sao repo **riêng**, tách khỏi bản đang chạy service |
| venv | `C:\HaviGroup\flow-v2\.venv` (Python 3.11.9) |
| Scheduled Task | `HaviGroup Flow v2`, `HaviGroup Content Image Runner`, `HaviGroup Listing2 ERP Runner`, `HaviGroup Orchestrator Runner` |
| Cấu hình runner | `...\automation_center\runner\.env`, `...\listing2-erp.env`, `...\orchestrator.env` (ACL: `PC\Admin` R/W + SYSTEM, bỏ kế thừa) |
| Log | `C:\HaviGroup\logs\` |
| Trình duyệt Playwright | `C:\Users\Admin\AppData\Local\ms-playwright\` (Chromium 191,8 MiB) |

### Vì sao dùng S4U

Ban đầu hai task đăng ký với `LogonType Interactive` + trigger `AtLogOn`, và
**chưa từng chạy** (`LastTaskResult = 0x41303`) vì trên PC không có phiên đăng
nhập nào (`query user` → *No User exists*).

Đã chuyển sang `-LogonType S4U -RunLevel Highest` với hai trigger `AtStartup` và
`AtLogOn`. S4U chạy được khi không ai đăng nhập và **không phải lưu mật khẩu ở
bất cứ đâu**.

> **Đính chính.** Bản runbook đầu ghi "Flow chạy Chrome headless nên không cần
> desktop session" — lúc đó sai, vì đó là giá trị mặc định
> `headless: bool = False` trong `flow_web/schemas.py`, không phải cấu hình đang
> chạy. S4U đặt tiến trình vào **Session 0**, nên khi `headless = false`
> Playwright cố mở Chrome có giao diện trong một session không có desktop và
> hỏng. **Từ 2026-08-13 đã bật `headless = true`** nên câu đó giờ đúng — nhưng
> nó đúng vì cấu hình, không phải mặc định. Xem mục 5.E và mục 7.

### Lệnh vận hành

```powershell
Get-ScheduledTask -TaskName 'HaviGroup*' | Format-Table TaskName, State
Start-ScheduledTask  -TaskName 'HaviGroup Content Image Runner'
Stop-ScheduledTask   -TaskName 'HaviGroup Content Image Runner'
Get-Content 'C:\HaviGroup\logs\content-image-runner.log' -Tail 20

Start-ScheduledTask  -TaskName 'HaviGroup Listing2 ERP Runner'
Get-Content 'C:\HaviGroup\logs\listing2-erp-runner.log' -Tail 20

Start-ScheduledTask  -TaskName 'HaviGroup Orchestrator Runner'
Get-Content 'C:\HaviGroup\logs\orchestrator-runner.log' -Tail 20
```

`LastTaskResult` `0x41301` nghĩa là **đang chạy**, `0x41303` là **chưa từng chạy**.

Khi restart runner, hãy `Stop-ScheduledTask` **rồi** giết tiến trình
`python.exe` còn sót (lọc theo `CommandLine` chứa `content_image_runner.py`) —
nếu không, file log vẫn bị giữ và bạn sẽ đọc nhầm log cũ tưởng là log mới.

### Cập nhật code lên PC

```sh
cd automation_center
scp runner/content_image_runner.py runner/listing2_erp_runner.py \
    runner/orchestrator_runner.py runner/*.ps1 \
    hvg-pc:C:/HaviGroup/flow-v2/automation_center/runner/
```

Copy xong phải restart task tương ứng thì code mới có tác dụng.

---

## 3. MacBook — dự phòng

| Thành phần | Vị trí |
| --- | --- |
| Flow v2 | `/Users/admin/Documents/ChatGPT/erptrello/flow-v2` (`.venv` Python 3.13) |
| Dịch vụ Flow | launchd `com.havigroup.flow-v2` → `127.0.0.1:8000` |
| Dịch vụ runner | launchd `com.havigroup.content-image-runner` (**chưa bootstrap, cố ý**) |
| Cấu hình runner | `automation_center/runner/.env`, chmod 600 |
| Log | `~/Library/Logs/havigroup/` |

Agent cũ `com.flowv2.local` (trỏ vào clone `~/VibeCoding/flow` từ 2026-05) đã bị
vô hiệu hoá thành `com.flowv2.local.plist.disabled-2026-08-13` để không tranh port 8000.

Kiểm tra sức khoẻ (chỉ in có/không, không in giá trị secret):

```sh
automation_center/scripts/check-runner-host.sh
```

Nếu cần chuyển host chính về Mac, **tắt runner trên PC trước**, rồi:

```sh
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.havigroup.content-image-runner.plist
```

---

## 4. Chạy cố định 24/7

Ngày 2026-08-15 cả hai runner ngừng heartbeat lúc `01:00:4xZ` và Tailscale báo PC
*offline, last seen 1d ago*. Không có log lỗi nào: **máy tắt hoặc ngủ, runner
không chết**. Và không ai biết cho tới khi mở dashboard ra xem.

Đó là hai lỗ khác nhau, phải vá bằng hai thứ khác nhau:

| Lỗ | Vá bằng |
| --- | --- |
| Máy tự ngủ / mất điện xong nằm im | `scripts/set-always-on.ps1` + một mục BIOS |
| Chết mà không ai biết | Watchdog cron trên Worker |

Lớp Scheduled Task lo phần "phần mềm chết thì sống lại", nhưng **không phải nhờ
`RestartCount`**. Đo tay 2026-08-20: giết uvicorn của Flow v2 thì Task Scheduler
ghi Event `102` *"successfully finished"* với return code `4294967295`, task về
`Ready`, `NextRunTime` trống — và nằm im vô hạn. Windows chỉ coi task là thất bại
khi nó *không khởi động được*, chứ không phải khi tiến trình con thoát với mã lỗi.

Thứ thật sự dựng lại là **trigger lặp 5 phút** (`MSFT_TaskTimeTrigger`,
`Repetition.Interval = PT5M`, duration rỗng = vô hạn), an toàn nhờ
`MultipleInstances IgnoreNew`: tick rơi vào lúc đang chạy thì bị bỏ qua.
`install-windows-services.ps1` đã đăng ký sẵn trigger này cho mọi task.

Nghiệm thu 2026-08-20 trên PC: giết tiến trình lúc `09:13:56` → Event `107`
*"due to a time trigger condition"* lúc `09:15:01` → `/api/health` xanh lại lúc
`09:15:07`. **Chết 71 giây, xấu nhất là 5 phút.**

### 4.1 `set-always-on.ps1` — phần cứng và hệ điều hành

Chạy trên PC bằng PowerShell **Run as Administrator**:

```sh
scp automation_center/scripts/set-always-on.ps1 hvg-pc:C:/HaviGroup/set-always-on.ps1
ssh hvg-pc "powershell -NoProfile -ExecutionPolicy Bypass -File C:\HaviGroup\set-always-on.ps1 -DryRun"
ssh hvg-pc "powershell -NoProfile -ExecutionPolicy Bypass -File C:\HaviGroup\set-always-on.ps1"
```

`-DryRun` chỉ in ra, không đổi gì, và không đòi quyền Administrator. Script thoát
với mã `1` khi còn mục phải xử lý tay, nên gọi được từ script khác.

Nó làm: `standby` / `hibernate` / `disk` / `monitor` timeout trên nguồn AC về `0`,
tắt ngủ đông + Fast Startup (`HiberbootEnabled = 0`), cấm Windows tắt card mạng
để tiết kiệm điện, đặt dịch vụ Tailscale về `Automatic` + đang chạy, rà lại bốn
Scheduled Task `HaviGroup*` (có trigger `AtStartup`? có đúng `LogonType = S4U`?
có bị `Disabled`? đã từng chạy chưa?), và cảnh báo khi ổ C: xuống dưới 15 GB.

Hai chỗ nó **cố ý không làm**:

- **Máy có pin thì bỏ qua `powercfg /hibernate off`.** Tắt ngủ đông trên máy
  chạy pin là mất dữ liệu khi cạn pin. Nhận biết bằng `Win32_Battery`. Trên PC
  để bàn, lệnh này còn giải phóng luôn `hiberfil.sys` — đáng kể với ổ C: ~23 GB.
- **`Restore on AC Power Loss = Power On` phải vào BIOS đặt tay.** Windows không
  đặt được. **Thiếu đúng mục này thì mọi thứ ở trên thành vô nghĩa**: mất điện
  xong máy nằm im chờ người tới bấm nút nguồn.

Đặt xong nên reboot một lần rồi chạy `zsh scripts/check-runner-host.sh` từ Mac.
Chạy được hết khi **không có ai đăng nhập vào PC** thì mới gọi là chạy cố định.

### 4.2 Watchdog — biết được lúc nào hỏng

Cron `*/5 * * * *` trong `wrangler.jsonc` gọi `scheduled()` của Worker, chạy
`runHealthChecks()` (`src/worker.js`). Ba thứ nó canh:

| Loại | Ngưỡng | Việc nó làm |
| --- | --- | --- |
| `runner_offline` | không heartbeat > **5 phút** | đặt `runners.status = 'offline'`, mở sự cố |
| `run_orphaned` | `bot_runs` kẹt `running`/`cancel_requested` > **1 giờ** | chuyển run sang `failed`, bot sang `error`, ghi audit `bot_run.orphaned` |
| `access_token_expiring` | còn < **45 ngày** tới `ACCESS_TOKEN_EXPIRES_AT` | mở sự cố nhắc rotate |

Runner heartbeat mỗi 2.5s, nên ngưỡng 5 phút cộng chu kỳ cron 5 phút cho ra phát
hiện trong vòng ~10 phút kể từ lúc chết.

Hai bộ dò **cố ý lệch nhau ở ca timestamp hỏng**: runner có `last_seen_at` không
đọc được thì **coi là offline** (thà báo thừa còn hơn im lặng khi máy đã chết);
run có timestamp không đọc được thì **để yên** (đây là nhánh *ghi*, tự ý cho một
run đang chạy thành `failed` là tệ hơn nhiều so với để nó nằm đó).

Trước đây `runners.status` **không có gì đặt lại về `offline`** — `runnerClaim`
đọc cờ đó, nên một runner đã chết vẫn hiện `online` mãi mãi. Watchdog cũng vá chỗ này.

**Không sinh sự cố trùng.** Chống trùng nằm ở chỉ mục partial của D1 trong
`migrations/0005_health_watchdog.sql`:

```sql
CREATE UNIQUE INDEX idx_health_incident_open
  ON health_incidents(kind, subject) WHERE resolved_at IS NULL;
```

cộng với `INSERT OR IGNORE`. Đây là ràng buộc trong database chứ không phải một
lần `SELECT` rồi mới `INSERT` — nên hai lần cron chạy chồng nhau cũng không tạo
được hai dòng. Sự cố đóng lại (`resolved_at`) rồi thì lần hỏng sau mở được dòng mới.

**Báo động.** Đặt `ALERT_WEBHOOK_URL` (Slack/Google Chat/bất cứ endpoint `https`
nào nhận `POST {text, incidents}`) làm secret:

```sh
cd automation_center
CLOUDFLARE_ACCOUNT_ID=f2cb3db89a7cc7e2578db1dfdb639a39 npx wrangler secret put ALERT_WEBHOOK_URL
```

Chỉ nhận `https:` — URL `http:` bị từ chối, vì nội dung sự cố có tên runner và
tên bot. Gửi hỏng thì **giữ `notified_at` NULL** và ghi lý do vào `notify_error`,
vòng cron sau thử lại; không cấu hình webhook thì đánh dấu đã báo kèm lý do, để
sự cố không nằm lại xếp hàng vô hạn. Sự cố vẫn xem được không cần webhook:

```sh
curl -s https://automation.havigroup.llc/api/health   # cần Access
```

`GET /api/health` trả `healthy`, danh sách runner kèm cờ `online`, sự cố đang mở
và 20 sự cố gần nhất.

Test (dùng `node:sqlite`, chạy trên **chính file migration thật** nên chỉ mục
partial ở trên nằm trong phạm vi test):

```sh
cd automation_center
node --test --experimental-sqlite tests/health.test.mjs   # 25 test
```

> **Bẫy đã dính một lần.** Đừng `export` hằng số (số, chuỗi, …) từ `src/worker.js`.
> workerd bắt mọi named export của module chính phải là function hoặc
> ExportedHandler, và sẽ chết ngay lúc khởi động với
> `Incorrect type for map entry 'ACCESS_TOKEN_WARN_DAYS'`. Ngưỡng được lộ ra cho
> test qua **hàm** `healthThresholds()` chính vì lý do này.

### 4.3 Deploy — ĐÃ XONG 2026-08-16

```sh
cd automation_center
CLOUDFLARE_ACCOUNT_ID=f2cb3db89a7cc7e2578db1dfdb639a39 npx wrangler d1 migrations apply hvg-automation-center --remote
CLOUDFLARE_ACCOUNT_ID=f2cb3db89a7cc7e2578db1dfdb639a39 npx wrangler deploy
```

**Migration phải chạy trước deploy**, không đảo được: cây code này chứa luôn
phần Agent điều phối, deploy trước khi áp `0004` thì các endpoint orchestrator
gọi vào bảng chưa tồn tại. Chiều ngược lại thì vô hại — D1 có schema mới mà
Worker còn code cũ chỉ nghĩa là bảng mới nằm im.

Đã áp `0004` + `0005`, deploy version `49de0199-d3e8-44e4-9b96-09d5db068a27`
lúc `2026-08-16T04:22:14Z`. Mốc time-travel ngay trước khi áp migration:
`0000001c-00000000-000050c9-58f78ec2220d8409b8a7879dbd7885ea`.

Nghiệm thu ngay sau deploy: cron nổ lúc `04:25:22Z`, mở đúng 2 sự cố
`runner_offline` ("mất tín hiệu 27 giờ") và đặt cả hai runner về `offline` —
trước đó không có gì đặt lại cờ này nên runner chết vẫn hiện `online` mãi. Qua
thêm hai nhịp cron nữa, bảng vẫn đúng 2 dòng: chống trùng chạy đúng trên
production, không chỉ trong test.

Kèm theo đó là **Agent điều phối cũng bật ở phía Worker**. Runner orchestrator
vẫn chưa cài nên UI báo *runner chưa kết nối* và Worker trả 409, không xếp yêu
cầu nào (mục 5.H).

---

## 5. Việc còn lại

### C. Cloudflare Access Service Token — ĐÃ XONG

Token OAuth của wrangler **không có scope `access`** (chỉ `workers`, `d1`,
`zone:read`…), nên bước này phải làm trên Zero Trust dashboard, không thể dùng
CLI. Trong dashboard mới, Service Token nằm ở **Access controls → Service
credentials**, còn policy dùng lại được nằm ở **Access controls → Policies**.

Cấu hình hiện tại:

| Mục | Giá trị |
| --- | --- |
| Service Token | `content-image-runner`, thời hạn 1 năm, **hết hạn 2027-08-13** |
| Policy | `Content Image Runner Service Auth` — Action `Service Auth`, Include `Service Token` = `content-image-runner` |
| Gắn vào | chỉ app **Automation HaviGroup** (`automation.havigroup.llc`) |

Include dùng **`Service Token`** cụ thể, **không** dùng `Any Access Service
Token` — nếu dùng cái sau thì token `hvg-smoke-prod` cũng vào được Automation
Center.

Policy nằm ở thứ tự 2 sau `HaviGroup staff — Automation`, không ảnh hưởng gì:
Access luôn đánh giá Bypass và Service Auth trước rồi mới tới các policy còn lại.

**Khi rotate token (trước 2027-08-13):** tạo token mới, thêm nó vào cùng policy,
rồi nạp cặp mới vào PC bằng một lệnh — script nhận 2 dòng qua stdin nên giá trị
không lên command line, không vào lịch sử shell, không in ra màn hình; nó tự
siết lại ACL, restart sạch runner và in 20 giây log đầu:

```sh
read -r CLIENT_ID; read -rs CLIENT_SECRET
printf '%s\n%s\n' "$CLIENT_ID" "$CLIENT_SECRET" \
  | ssh hvg-pc "powershell -NoProfile -ExecutionPolicy Bypass -File C:\HaviGroup\flow-v2\automation_center\scripts\set-access-token-stdin.ps1"
```

Script kiểm tra dòng 1 phải kết thúc bằng `.access` nên đảo thứ tự hai dòng sẽ
báo lỗi ngay thay vì hỏng âm thầm.

Restart runner không kèm đổi credential:

```sh
ssh hvg-pc "powershell -NoProfile -ExecutionPolicy Bypass -File C:\HaviGroup\flow-v2\automation_center\scripts\restart-runner.ps1"
```

Kiểm tra runner có thật sự online (không cần mở dashboard):

```sh
npx wrangler d1 execute hvg-automation-center --remote \
  --command "SELECT runner_key, version, last_seen_at, datetime('now') AS now_utc FROM runners"
```

Xác nhận thành công: log runner **không còn** dòng
`Cloudflare Access chặn runner: ...`, và dashboard hiện **Runner trực tuyến**.

### E. Đăng nhập Google Flow + bật headless trên PC — ĐÃ XONG

Phiên Google trên MacBook **không dùng lại được** cho PC: cookie Chrome mã hoá
theo OS (Keychain trên macOS, DPAPI trên Windows), copy profile qua là hỏng.

Không thể chỉ mở `http://127.0.0.1:8000` từ xa rồi đăng nhập. Flow chạy dưới
Scheduled Task S4U tức **Session 0**, và `_assert_windows_interactive_browser_session`
(`flow_web/service.py:1274`, `1284`, `6707`) trả **HTTP 400** khi phát hiện
Session 0. Việc nằm ở **tiến trình server**, không phải ở trình duyệt bạn dùng
để mở UI.

**DeskIn không vào được.** Thay bằng **RDP qua Tailscale** — PC là Windows 10
Pro nên đã có sẵn, chỉ cần `fDenyTSConnections=0` và mở port 3389. Thành viên
`Administrators` có quyền RDP mà không cần nằm trong `Remote Desktop Users`.
User đăng nhập là `PC\Admin`.

#### Cầu nối từ SSH vào phiên RDP

SSH cũng nằm ở Session 0, nên không thể `Start-Process` một app có GUI từ SSH.
Cách vượt: đăng ký **Scheduled Task với `LogonType=Interactive`** — Task
Scheduler khởi chạy tiến trình trong **phiên interactive đang hoạt động**. Task
action chỉ gọi `Start-Process` rồi thoát, nên tiến trình con tách ra và sống
tiếp kể cả sau khi xoá task:

```powershell
$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -WindowStyle Hidden -Command "Start-Process ..."'
$p = New-ScheduledTaskPrincipal -UserId 'PC\Admin' -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName 'tmp-bridge' -Action $a -Principal $p -Force
Start-ScheduledTask -TaskName 'tmp-bridge'
Start-Sleep 5; Unregister-ScheduledTask -TaskName 'tmp-bridge' -Confirm:$false
```

#### Lỗi thật khi bấm Đăng nhập: thiếu trình duyệt Playwright

`POST /api/flow/open-login` trả **500 Internal Server Error**. Đây **không** phải
lỗi Session 0. Nguyên nhân thật: trên PC **chưa từng chạy `playwright install`**:

> `Executable doesn't exist at C:\Users\Admin\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe`

```powershell
C:\HaviGroup\flow-v2\.venv\Scripts\python.exe -m playwright install chromium
```

Traceback chỉ thấy được sau khi khởi chạy Flow qua
`cmd.exe /c "... > C:\HaviGroup\logs\flow-rdp.log 2>&1"`. Tiến trình detach ghi
log ra console của chính nó, nên `flow-v2.log` vẫn là log **cũ** — rất dễ đọc
nhầm rồi chẩn đoán sai.

#### Thứ tự đã làm

1. Vào RDP qua Tailscale.
2. `Stop-ScheduledTask -TaskName 'HaviGroup Flow v2'`.
3. Chạy Flow bằng tay **trong phiên RDP** (hoặc qua cầu nối Interactive Task ở trên).
4. Mở `http://127.0.0.1:8000` → mở khối **Thiết lập** (`#setupToggle`) mới thấy
   nút Đăng nhập — nó nằm trong `<section class="setup-panel" hidden>`
   (`flow_web/static/index.html:422`, nút ở dòng `459`).
5. Đăng nhập Google, chọn Project ID.
6. Bật headless bằng `set-flow-headless.ps1`.
7. `Start-ScheduledTask -TaskName 'HaviGroup Flow v2'` → Flow về Session 0, chạy headless.

**Không PUT `/api/config` bằng tay.** `update_config` (`service.py:585`) dựng lại
`AppConfig` từ đầu, field nào không gửi sẽ bị reset — gửi `{"headless":true}`
không thôi sẽ **xoá mất `project_id`** vừa chọn. Script `set-flow-headless.ps1`
đọc config hiện tại rồi ghi lại nguyên vẹn, chỉ đổi một field, và từ chối chạy
nếu `project_id` đang trống.

Trước khi force-kill Chromium để restart, **backup profile trước**
(`C:\HaviGroup\backup\flow-profile-before-headless`): `taskkill` không có `/F`
sẽ báo *"can only be terminated forcefully"* với tiến trình con của Chromium.

Profile Chrome được lưu lại nên các lần sau không cần GUI nữa.

### F. Runner Listing 2 ERP — ĐÃ TRIỂN KHAI

Toàn bộ phần ERP **đã có sẵn trong Flow** (`flow_web/service.py`): đọc Task
nguồn trong project ERP đang cấu hình, upscale, đính ảnh, ghi title/description. Runner
**không** nói GraphQL với ERP và **không** cầm token ERP — đó là lý do
`listing2-erp.env` không có credential ERP nào.

Điểm chốt thiết kế nằm ở docstring của `apply_dashboard_approval`
(`service.py:14384`): *"Record a local review decision and resume the ERP step
when ready."* Nghĩa là Flow **chờ** quyết định duyệt rồi mới ghi về ERP. Nên
runner chạy hai vòng:

1. `claim` lệnh từ Center → tạo job Flow với `erp_enabled=True`,
   `flow_agent_auto_approve=False`.
2. `GET /api/runner/approvals` → chuyển quyết định vào
   `POST /api/jobs/{job_id}/artifacts/{index}/approval` của Flow.

`forward_approvals()` chạy **trước** `claim` trong mỗi vòng: ảnh đã duyệt không
nên phải chờ một lệnh tạo ảnh dài kết thúc mới được ghi về ERP.

`flow_agent_auto_approve` **bắt buộc `False`** — bật lên là đẩy ảnh chưa ai xem
thẳng vào ERP.

Migration `0003` thêm `bot_runs.erp_task_id` và bốn cột cho `approvals`
(`run_id`, `artifact_index`, `pushed_at`, `push_error`). Trước đó `approvals`
**không có đường quay lại run**, nên không thể biết quyết định duyệt thuộc job
Flow nào. `pushed_at` là chốt chống đẩy trùng; đẩy lỗi thì giữ `pushed_at` NULL
và ghi `push_error` để vòng sau thử lại.

Ô nhập **Mã Task ERP nguồn** trên dashboard là tuỳ chọn (chỉ hiện với bot có
`runner_key = listing2-erp-runner`). Để trống thì Flow tự chọn Task trong danh
sách nguồn `Open` của project đang cấu hình. Worker chỉ nhận đúng dạng `TASK-xxxx`.

Triển khai lại từ đầu:

```sh
cd automation_center
CLOUDFLARE_ACCOUNT_ID=f2cb3db89a7cc7e2578db1dfdb639a39 npx wrangler d1 migrations apply hvg-automation-center --remote
CLOUDFLARE_ACCOUNT_ID=f2cb3db89a7cc7e2578db1dfdb639a39 npx wrangler deploy
scp runner/listing2_erp_runner.py runner/run-listing2-erp-runner.ps1 hvg-pc:C:/HaviGroup/flow-v2/automation_center/runner/
```

`listing2-erp.env` được **sinh trên PC** từ `.env` sẵn có (chỉ đổi
`AUTOMATION_RUNNER_KEY` và `AUTOMATION_RUNNER_LABEL`), nên secret không bao giờ
rời máy. Scheduled Task cũng được **nhân bản** từ task content-image bằng
`Export-ScheduledTask` + thay chuỗi, để giữ nguyên S4U / boot + logon trigger /
restart 999 lần.

### G. Nghiệm thu

1. Dashboard hiện **Runner trực tuyến** cho cả hai bot. ✅
2. Tạo 1 ảnh thử → ảnh xuất hiện ở mục duyệt.
3. Tạo ảnh thứ hai rồi bấm **Dừng** khi đang chạy → run chuyển `cancelled`,
   Flow nhận lệnh stop.
4. (ERP) Duyệt một ảnh của bot Listing 2 → Flow chạy tiếp bước ghi về Task ERP.
   **Chưa chạy thật lần nào.** Ghi chú cũ *"`PROJ-0049` có 0 task"* đã lỗi thời:
   project đích bây giờ là `PROJ-0013` (`service.py:201`), và thẻ Idea mẫu là
   `TASK-2026-00202`. `PROJ-0049` chỉ còn sót trong `.env.local.example` và
   `execution-notes.md`.

Bước 2–4 cần người bấm nút trên dashboard: `botAction` đi qua Cloudflare Access
+ Keycloak SSO nên không gọi bằng script được.

### H. Agent điều phối — ĐÃ CÀI, CHỜ `orchestrator.env`

Runner thứ ba, chạy trên chính máy trung tâm này. Nó không gắn bot: nó nhận yêu
cầu sửa code từ nhân viên, gọi ChatGPT, ghi file và chạy test. Đây là phần
"máy trung tâm xử lý code thay vì máy cá nhân".

Điều kiện trước: đã áp `0004_orchestrator_agent.sql` lên remote và deploy Worker.

Ngày 2026-08-26 đã làm qua ssh: cài git, dựng `AGENT_REPO_DIR`, chép mã runner
sang máy, đăng ký Scheduled Task. Còn lại đúng hai việc, ghi ở cuối mục.

Ba điều bản runbook cũ nói sai, vì máy đã đổi từ lúc viết:

- **`C:\HaviGroup\flow-v2` không phải git clone.** Nó là bản giải nén (còn
  nguyên các file `._*` của macOS). `git clone C:\HaviGroup\flow-v2 …` không
  chạy được.
- **Máy chưa có git.** `winget install --id Git.Git -e --silent
  --accept-package-agreements --accept-source-agreements` → 2.55.0.3 tại
  `C:\Program Files\Git\cmd\git.exe`. Không có git thì runner chết ngay ở
  `git checkout -B`, mà chết sau khi đã nhận việc.
- **`AGENT_TEST_COMMAND` không được dùng đường dẫn tương đối.** `run_tests()`
  chạy với `cwd = AGENT_REPO_DIR`, nên `.venv\Scripts\python.exe` trỏ vào bản
  sao của agent — chỗ không có venv. Mọi thay đổi sẽ vĩnh viễn "chưa có test
  xanh". Dùng đường dẫn tuyệt đối tới trình thông dịch của repo service.

1. **Dựng bản repo riêng cho agent.** Không trỏ vào `C:\HaviGroup\flow-v2`:
   agent checkout qua lại giữa các nhánh, trỏ vào bản đang chạy service sẽ làm
   Flow đọc code nửa chừng. `run-orchestrator-runner.ps1` từ chối khởi động nếu
   `AGENT_REPO_DIR` trùng repo service.

   Máy trung tâm không đăng nhập được GitHub, nên đường đi là một git bundle
   gửi từ máy có repo — một file, không cần credential, không cần mạng ra ngoài:

   ```sh
   git bundle create /tmp/flow-v2.bundle --all          # ~2 MB
   scp /tmp/flow-v2.bundle hvg-pc:C:/HaviGroup/flow-v2.bundle
   ```

   ```powershell
   $g = 'C:\Program Files\Git\cmd\git.exe'
   & $g clone -b codex/publish-flow-automation `
       'C:\HaviGroup\flow-v2.bundle' 'C:\HaviGroup\agent-workspace\flow-v2'
   cd 'C:\HaviGroup\agent-workspace\flow-v2'
   & $g checkout -B main                                 # khớp AGENT_BASE_BRANCH
   & $g remote set-url origin 'https://github.com/ph56jk/flow-v2.git'
   & $g config user.name  'HaviGroup Agent dieu phoi'    # thiếu danh tính thì
   & $g config user.email 'agent@havigroup.llc'          # `git commit` thất bại
   & $g config core.autocrlf false
   Remove-Item 'C:\HaviGroup\flow-v2.bundle' -Force
   ```

   Kiểm dung lượng trước: ổ C: chỉ còn ~23 GB.

2. **Tạo `runner\orchestrator.env`.** Đừng chép tay: `AUTOMATION_RUNNER_SECRET`
   và cặp Access Service Token đã nằm trong `runner\.env` của chính máy này,
   chép tay nghĩa là cho chúng đi qua màn hình và clipboard.
   `scripts\make-orchestrator-env.ps1` đọc thẳng file cũ và sao ACL nguyên sang.

   Script **không hỏi gì cả**: agent gọi model qua Codex CLI đã đăng nhập sẵn
   trên máy, nên không có khoá API nào phải cất ở đâu. Nó tự tìm `codex.exe`
   và ghi đường dẫn tuyệt đối vào `CODEX_BIN` — Scheduled Task chạy kiểu S4U
   có PATH hẹp hơn phiên đăng nhập.

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass `
       -File C:\HaviGroup\flow-v2\automation_center\scripts\make-orchestrator-env.ps1
   ```

   Vẫn muốn đi đường HTTP của OpenAI thì thêm `-KhoaOpenAI`. Khi ấy
   `OPENAI_API_KEY` **chỉ** nằm trong file này — không vào D1, `public/`, form
   của Automation Center, plist, Scheduled Task hay log.

   Codex CLI ở đây chỉ là **đường truyền chữ**, không phải thứ ghi file. Nó
   chạy với `--sandbox read-only`, và thư mục làm việc là một thư mục tạm
   **rỗng** chứ không phải `AGENT_REPO_DIR`: model chỉ thấy những gì runner đã
   lọc qua `is_protected()` rồi đưa vào lời nhắc. Ba lớp an toàn không đổi —
   phạm vi glob, danh sách bảo vệ, nhánh `agent/<id>` — vì thứ duy nhất ghi
   file vẫn là runner.

   Đo trên chính máy này ngày 2026-08-26:

   - Lệnh shell do model sinh ra **chết ngay lúc khởi tạo tiến trình** (mã
     `-1073741502` = `STATUS_DLL_INIT_FAILED`, dấu hiệu AppContainer chặn) và
     không file nào được ghi. Sandbox có thật trên Windows, không phải lời hứa.
   - Để model tự loay hoay với công cụ đã chết thì một lượt chạy **quá 5 phút**
     không ra kết quả. Câu "bạn không có công cụ nào dùng được ở đây" trong
     lời nhắc đưa nó về **8 giây**. Đừng bỏ câu đó đi.

3. **Đăng ký Scheduled Task** `HaviGroup Orchestrator Runner`, cùng kiểu S4U /
   `RunLevel Highest` / trigger `AtStartup` + `AtLogOn` như hai task kia. Runner
   này không mở trình duyệt nên không vướng vấn đề Session 0.

   Máy đang chạy bốn task rồi, nên **phải** dùng `-Only`: mỗi lần đăng ký là một
   lần Unregister rồi Register, tức là dừng thật một dịch vụ đang phục vụ.

   Và **phải** gửi lệnh bằng `-EncodedCommand`: qua ssh, chuỗi
   `-Only 'HaviGroup Orchestrator Runner'` bị lớp vỏ bên kia tách thành ba tham
   số, script lặng lẽ bỏ qua đúng cái task cần đăng ký rồi thoát với mã 0.

   ```sh
   CMD=$(python3 -c "
   import base64
   ps = (\"& 'C:\\\\HaviGroup\\\\flow-v2\\\\automation_center\\\\scripts\\\\install-windows-services.ps1' \"
         \"-Only 'HaviGroup Orchestrator Runner'\")
   print(base64.b64encode(ps.encode('utf-16-le')).decode())
   ")
   ssh hvg-pc "powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $CMD"
   ```

4. **Kiểm tra**: dashboard → **Agent điều phối** phải hiện runner trực tuyến.
   Khi runner offline, Worker trả 409 và không xếp yêu cầu nào — không có lệnh giả.

5. **Cấp phạm vi**: Owner mở **Cấp hoặc sửa phạm vi**, cấp glob cho từng vai trò
   hoặc từng người. Trước bước này chỉ Owner dùng được agent. Bật `auto_apply`
   nghĩa là thay đổi trong phạm vi + test xanh vào thẳng nhánh base không cần
   người duyệt — chỉ bật khi đã tin phạm vi đó.

Nghiệm thu tối thiểu, làm theo thứ tự này:

1. Gửi một yêu cầu **trong phạm vi** → có diff, test xanh, trạng thái
   `awaiting_approval`.
2. Gửi một yêu cầu **ngoài phạm vi** → `failed` kèm lý do nêu tên file, không
   có file nào bị ghi.
3. Gửi một yêu cầu chạm file bảo vệ (ví dụ `.env` hay `src/worker.js`) →
   `touches_protected`, chỉ Owner duyệt được, không bao giờ tự áp dụng.
4. Người gửi tự bấm duyệt yêu cầu của mình → bị từ chối (trừ Owner).

**Còn lại tính tới 2026-08-26:** bước 2 (`orchestrator.env`). Worker đã deploy
(bản `8d00be8c`). Task đã đăng ký và đang lặp 5 phút, nên nó tự sống dậy ngay
lần tick đầu sau khi file env có mặt — không phải đăng ký lại. Trước lúc đó log
chỉ có đúng một dòng `Thiếu file cấu hình runner: …\orchestrator.env`, và đó là
dấu hiệu đúng.

---

## 6. Các lỗi đã sửa

### Nút Dừng bị mất tác dụng (`src/worker.js`)

`runnerUpdateRun` cho phép cập nhật `running` của runner ghi đè trạng thái
`cancel_requested`.

Kịch bản hỏng: runner claim job → gọi Flow tạo job (mất vài giây vì phải điều
khiển trình duyệt) → trong lúc đó người dùng bấm **Dừng**, Worker đặt
`cancel_requested` → runner gọi `update_run(..., "running", runner_job_id=...)`
→ Worker ghi đè về `running`. Vòng lặp runner sau đó poll `is_cancel_requested()`
và luôn thấy `running`, nên lệnh dừng biến mất vĩnh viễn và ảnh vẫn được tạo.

Bản sửa: khi run đang ở `cancel_requested` mà runner báo `running`, Worker chỉ
ghi nhận `runner_job_id` và giữ nguyên `cancel_requested`.

### Runner crash ngay khi khởi động trên Windows

Console Windows dùng cp1252, runner in thông báo tiếng Việt → `UnicodeEncodeError`
và thoát ngay. Đã đặt `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` trong cả hai
wrapper `.ps1`.

### Cloudflare WAF chặn runner (lỗi 1010)

User-Agent mặc định `Python-urllib/3.11` bị chặn với
`error_name: browser_signature_banned`. Runner giờ gửi
`HaviGroupAutomationRunner/1.0 (+content-image-runner)`.

### Thông báo lỗi Access khó hiểu

Cloudflare Access trả 302 về trang đăng nhập; urllib đi theo redirect nên runner
nhận HTML 200 và `json.loads` báo `Expecting value: line 1 column 1`. Runner giờ
kiểm tra `content-type` và báo đúng nguyên nhân.

---

## 7. Điểm cần theo dõi

- **Ảnh duyệt trỏ về CDN Google.** `JobArtifact.url` cho ảnh là `fife_url`
  (`googleusercontent.com`). Worker chỉ chấp nhận URL `https:` nên link qua được,
  và trình duyệt người duyệt tải ảnh thẳng từ Google — không qua host, không qua
  Worker. Loại URL này có thể hết hạn; nếu cần lưu trữ lâu dài phải upload ảnh
  lên nơi do công ty kiểm soát rồi mới tạo approval.
- **Run mồ côi — đã có watchdog, nhưng chưa deploy.** `runHealthChecks()` chuyển
  run kẹt `running` / `cancel_requested` quá 1 giờ sang `failed`. Chừng nào chưa
  deploy (mục 4.3) thì vẫn phải dọn tay.
- **`config.headless` giờ điều khiển đúng trình duyệt dùng chung.** Trước đây
  `_ensure_shared_browser` ghi cứng `BrowserManager(headless=False, …)`, nên bật
  `headless` là rơi sang nhánh `FlowClient.create(headless=…)` — client ngắn hạn
  từng job, bỏ trắng danh sách profile, không xoay vòng khi hết lượt. Nay
  `_should_keep_flow_browser_open` chỉ còn nhìn `cdp_url`, và trình duyệt dùng
  chung mở ẩn hay hiện là theo `headless`. Ở Session 0 vẫn phải để
  `headless = true`; **tắt headless là Flow chết ở Session 0** như cũ. Lối đăng
  nhập gọi `_ensure_shared_browser(visible=True)` nên luôn cần phiên interactive.
- **Chạy ẩn phải là Chromium đầy đủ, không phải `chrome-headless-shell`.**
  Playwright lặng lẽ đổi sang bản rút gọn khi `headless=True`. Bản ấy mở đúng hồ
  sơ, giải mã được cookie Google, nhưng labs.google không cấp phiên next-auth cho
  nó: `/fx/api/auth/session` trả `{}`, không có Bearer token, mọi lệnh gọi Flow
  rơi xuống 401 *"API keys are not supported by this API"* — đọc lên y hệt phiên
  đăng nhập đã hết hạn. `_patch_playwright_headless_channel` (gọi từ
  `_patch_flow_runtime_compat`) chèn `channel="chromium"` cho mọi lần mở ẩn; máy
  nào chưa tải bản đầy đủ thì ghi cảnh báo rồi quay về bản rút gọn. Cài
  `playwright install chromium` là có cả hai.
- **Hồ sơ thật không giữ cookie next-auth trên đĩa.** Phiên Flow dựng lại từ
  cookie tài khoản Google mỗi lần mở trang, nên `_flow_session_cookie_expired`
  nay tính cả `SID` / `__Secure-1PSID` của `.google.com`; trước đó nó chỉ tìm
  next-auth, không thấy nên báo "hết hạn đăng nhập" và chặn cả `POST /api/jobs`
  trong lúc Flow vẫn chạy được (đường ERP idea không đi qua cổng này nên vẫn
  chạy — đó là lý do lỗi ẩn mình lâu như vậy).
- **Ổ C: của PC chỉ còn ~23 GB** (đã trừ ~306 MB trình duyệt Playwright vừa tải).
  Chrome profile và ảnh tải về sẽ ăn dần.
- **Agent điều phối ăn thêm ổ C: và token ChatGPT.** Bản sao repo riêng của agent
  là một clone đầy đủ, và mỗi yêu cầu chạy tối đa 4 vòng gọi ChatGPT với ngữ cảnh
  file. Chưa có trần chi phí nào trong code — hiện phải theo dõi bằng hoá đơn
  OpenAI.
- **Nhánh `agent/<id>` không được dọn tự động.** Yêu cầu bị từ chối để lại nhánh
  trong workspace của agent. Nhánh của yêu cầu `failed` thì runner đã tự xoá.
- **Nội dung repo là dữ liệu, không phải lệnh.** Agent đọc file trong repo rồi
  đưa vào prompt ChatGPT, nên một comment cài cắm trong code có thể cố lái nó.
  Lớp chặn thật là phạm vi glob + danh sách bảo vệ ở cả runner lẫn Worker, không
  phải lời nhắc hệ thống — đừng nới hai thứ đó ra để "cho tiện".
- **Service Token hết hạn 2027-08-13.** Khi hết hạn, runner sẽ im lặng quay lại
  lỗi `Cloudflare Access chặn runner: ...` và dashboard báo *Runner chưa kết nối*.
  Chọn thời hạn 1 năm để buộc rotate thay vì non-expiring. Watchdog nhắc trước
  **45 ngày** dựa trên `ACCESS_TOKEN_EXPIRES_AT` trong `wrangler.jsonc` — nhớ sửa
  ngày đó mỗi lần rotate, nếu không lời nhắc sẽ nhắc về một cái token đã chết.
  Xem lại mục 5.C trước ngày đó.
