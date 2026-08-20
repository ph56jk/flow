# Automation HaviGroup

`automation.havigroup.llc` là control plane cho nhiều chương trình tự động hóa. Mỗi chương trình tương ứng với một dashboard: bot, project được gán, quyền thành viên, yêu cầu duyệt và audit log được tách theo dashboard.

Lần triển khai hiện tại chỉ khởi tạo chương trình **Agent tạo ảnh Content**. Có thể thêm chương trình khác sau khi agent này đã được nối runner và nghiệm thu.

Đây là Cloudflare Worker + D1. Giao diện không lưu thông tin đăng nhập, ERP token hay token runner trên trình duyệt. Người dùng phải đi qua Cloudflare Access và Worker chỉ nhận email công ty từ header do Access ký.

## Chạy giao diện mẫu

```bash
cd automation_center
python3 -m http.server 8020 --directory public
```

Mở `http://127.0.0.1:8020/?preview=1`. Preview chỉ dùng dữ liệu minh họa; mọi nút thay đổi dữ liệu đều được chặn, không gọi ERP hoặc bot.

## Triển khai Cloudflare

Điều kiện trước: zone `havigroup.llc` đã nằm trong đúng Cloudflare account và máy triển khai đã đăng nhập Wrangler.

```bash
cd automation_center
pnpm dlx wrangler whoami
pnpm dlx wrangler deploy
pnpm dlx wrangler d1 migrations apply hvg-automation-center --remote
pnpm dlx wrangler secret put INITIAL_OWNER_EMAIL
pnpm dlx wrangler deploy
```

Khi Wrangler hỏi `INITIAL_OWNER_EMAIL`, nhập email công ty của Owner đầu tiên. Giá trị này chỉ ở Cloudflare secret, không ghi vào Git. Lần đăng nhập đầu tiên của Owner sẽ tự tạo bốn dashboard khởi đầu.

`wrangler.jsonc` đã khai báo route `automation.havigroup.llc/*`. Nếu Wrangler báo không tự tạo được D1, tạo database thủ công rồi thay `d1_databases[0]` bằng `database_id` được Wrangler trả về trước khi deploy:

```bash
pnpm dlx wrangler d1 create hvg-automation-center
```

Tiếp tục xem [hướng dẫn Access và triển khai](docs/cloudflare-access-setup.md) trước khi mở link cho nhân viên.

## Quyền

| Vai trò | Trong dashboard được gán |
| --- | --- |
| Owner | Tạo dashboard, cấu hình, cấp quyền, chạy bot, duyệt, xem toàn bộ. |
| Admin | Cấu hình bot, cấp quyền trong dashboard đó, chạy bot, duyệt, xem. |
| Operator | Xem và gửi lệnh chạy/tạm dừng bot. |
| Reviewer | Xem và duyệt/từ chối yêu cầu. |
| Viewer | Chỉ xem. |

Quyền chỉ có hiệu lực tại dashboard được gán. Khi mở thêm chương trình trong tương lai, quyền của Agent tạo ảnh Content không tự mở sang chương trình đó.

## Agent điều phối: cho nhân viên nhắn để sửa code

Màn hình **Agent điều phối** cho phép nhân viên mô tả thay đổi bằng tiếng Việt; ChatGPT chạy trên máy trung tâm đọc repo, sửa code, chạy test rồi trả diff về để duyệt. Mục tiêu là nhân viên không phải đi qua Owner cho từng sửa đổi nhỏ, nhưng cũng không ai sửa được cả codebase.

Ba lớp giới hạn, độc lập nhau:

1. **Vai trò** — Operator trở lên mới gửi được yêu cầu (`code_request`); chỉ Admin/Owner duyệt được (`code_approve`). Reviewer và Viewer không gửi được.
2. **Phạm vi đường dẫn** — mỗi vai trò hoặc từng người được cấp một danh sách glob cùng trần số file và số dòng. Không có bản ghi phạm vi thì không gửi được yêu cầu (Owner mặc định `**`, 40 file / 4000 dòng). Phạm vi được **đóng băng** vào yêu cầu lúc xếp hàng, nên sửa quyền sau đó không nới rộng được yêu cầu đang chờ.
3. **Danh sách bảo vệ toàn cục** — `.env*`, `*.pem`, `*.key`, `*secret*`, `*credentials*`, `.gitignore`, `.github/**`, `wrangler.*`, `automation_center/migrations/**`, `automation_center/runner/**`, `automation_center/scripts/**` và chính `automation_center/src/worker.js`. Phạm vi rộng đến `**` cũng không vượt được: chạm vào là buộc Owner duyệt tay và không bao giờ tự áp dụng. Agent do đó không sửa được chính phần phân quyền đang ràng buộc nó.

### Agent điều khiển các agent khác

Cùng ô chat đó còn dùng để chạy, tạm dừng hay tiếp tục các bot trong chương trình: "dừng bot tạo ảnh lại giúp tôi". Agent nhận ra đây không phải yêu cầu sửa code, nên nó không tạo nhánh và không sinh diff — chỉ chuyển lệnh, và thẻ yêu cầu hiện lại từng lệnh đã chạy cùng kết quả.

Ranh giới đúng bằng cái nút người đó tự bấm được trên web: Worker kiểm quyền `run` của **người gửi** (vai trò đã đóng băng lúc xếp việc) rồi chạy đúng lõi mà nút bấm dùng. Reviewer và Viewer không điều khiển được bot qua agent, vì họ cũng không bấm được nút. Runner còn không hiển thị danh sách bot cho người không có quyền, nên ChatGPT không có `bot_id` nào để gọi.

Owner có thể bật `auto_apply` cho một phạm vi: thay đổi nằm trong phạm vi, không chạm file bảo vệ và test xanh thì vào thẳng nhánh base, không cần người duyệt. Mặc định tắt.

Người gửi không tự duyệt yêu cầu của mình (trừ Owner). Mỗi yêu cầu chạy trên nhánh riêng `agent/<id>` tách từ `main`, chỉ merge sau khi có quyết định.

Ranh giới này được khoá bằng hai bộ test:

```bash
node --test tests/permissions.test.mjs          # ranh giới quyền phía Worker
python3 tests/test_scope_parity.py              # Worker và runner phải cho cùng kết quả
python3 tests/test_orchestrator_bot.py          # điều khiển bot không rò tên bot, không chạm git
```

Bộ thứ hai tồn tại vì hai lớp kiểm phạm vi được cài đặt hai lần bằng hai ngôn ngữ. Trùng lặp là cố ý, nhưng trùng lặp sẽ trôi — và một chỗ trôi ở đây nghĩa là một file lẽ ra được bảo vệ lại đi lọt. Khi thêm mẫu vào danh sách bảo vệ, phải sửa **cả hai** nơi: `src/worker.js` và `runner/orchestrator_runner.py`.

### Đưa Agent điều phối vào chạy

1. Áp dụng migration `0004_orchestrator_agent.sql` rồi deploy:

   ```bash
   cd automation_center
   pnpm dlx wrangler d1 migrations apply hvg-automation-center --remote
   pnpm dlx wrangler deploy
   ```

2. Trên **máy trung tâm** (PC `100.75.125.80`), clone một bản repo riêng cho agent — không dùng bản đang chạy service, vì agent checkout qua lại giữa các nhánh.

3. Tạo `runner/orchestrator.env` từ [`runner/orchestrator-runner.env.example`](runner/orchestrator-runner.env.example). File này phải riêng, không dùng chung với hai runner kia. `OPENAI_API_KEY` chỉ nằm ở đây: không đưa vào D1, `public/`, form của Automation Center hay Git.

4. Chạy `runner/run-orchestrator-runner.ps1` (Scheduled Task, giống hai runner còn lại). Khi runner chưa heartbeat, Worker trả 409 và không xếp yêu cầu nào — không có lệnh giả.

5. Owner vào **Agent điều phối → Cấp hoặc sửa phạm vi** cấp glob cho từng vai trò hoặc từng người. Trước bước này chỉ Owner dùng được agent.

Chi tiết endpoint và luồng xử lý: [kiến trúc](docs/architecture.md).

## Agent tạo ảnh Content: đưa vào chạy thật

Agent đã có hàng đợi thật, không còn đổi sang “đang chạy” khi runner chưa kết nối. Luồng hoạt động là: người dùng nhập idea → Worker xếp lệnh → runner Mac/VM nhận lệnh → Flow tạo ảnh → kết quả quay về phần **Yêu cầu duyệt**. Khi lệnh đang chờ hoặc đang chạy, nút **Dừng** luôn hiện; lệnh chờ sẽ bị huỷ ngay, còn lệnh đã vào Flow sẽ nhận lệnh dừng.

Runner dùng polling outbound, vì thế Flow v2 vẫn chỉ mở ở `127.0.0.1` trên máy công ty và không cần expose cổng Flow ra Internet.

1. Áp dụng migration và deploy Worker:

   ```bash
   cd automation_center
   pnpm dlx wrangler d1 migrations apply hvg-automation-center --remote
   pnpm dlx wrangler secret put RUNNER_SHARED_SECRET
   pnpm dlx wrangler deploy
   ```

   Sinh một chuỗi ngẫu nhiên dài cho `RUNNER_SHARED_SECRET`; không đưa giá trị này vào Git, D1 hay giao diện.

2. Trong Cloudflare Zero Trust, tạo **Access Service Token** riêng (ví dụ `content-image-runner`) và thêm policy **Service Auth** cho ứng dụng `Automation HaviGroup`, chỉ Include service token đó. Giữ nguyên policy đăng nhập SSO cho nhân viên.

3. Trên Mac/VM công ty, chạy Flow v2, mở Google Flow để đăng nhập và lưu Project ID. Sau đó tạo một file riêng từ [`runner/content-image-runner.env.example`](runner/content-image-runner.env.example), điền runner secret cùng Access client ID/secret, rồi nạp biến môi trường và chạy:

   ```bash
   python3 runner/content_image_runner.py
   ```

   Runner sẽ hiện **Runner trực tuyến** trong dashboard. Khi chưa thấy trạng thái này, dashboard chỉ mở hướng dẫn thiết lập và không tạo lệnh giả.

Xem [kiến trúc](docs/architecture.md) để biết ranh giới quyền và bí mật.
