# Thiết lập Cloudflare cho `automation.havigroup.llc`

## 1. Đăng nhập và triển khai Worker

Tại thư mục `automation_center`, xác nhận đúng Cloudflare account:

```bash
pnpm dlx wrangler whoami
```

Nếu chưa đăng nhập, chạy `pnpm dlx wrangler login`, hoàn tất OAuth trong trình duyệt bằng Cloudflare account đang quản lý zone `havigroup.llc`, rồi chạy lại `whoami`.

Sau đó chạy:

```bash
pnpm dlx wrangler deploy
pnpm dlx wrangler d1 migrations apply hvg-automation-center --remote
pnpm dlx wrangler secret put INITIAL_OWNER_EMAIL
pnpm dlx wrangler deploy
```

Lệnh deploy tạo Worker, assets và route `automation.havigroup.llc/*`. Nếu D1 tự cấp phát không thành công, tạo D1 thủ công, thêm `database_id` được trả về vào `wrangler.jsonc`, rồi deploy và migration lại.

## 2. Chặn truy cập trực tiếp bằng Cloudflare Access

Trong Cloudflare Zero Trust:

1. Vào **Access → Applications → Add an application → Self-hosted**.
2. Tên: `Automation HaviGroup`.
3. Domain: `automation.havigroup.llc`; path: `/*`.
4. Thêm policy **Allow — Company staff**: Include → Emails ending in → `@havigroup.llc`.
5. Chọn identity provider của công ty (ưu tiên Google Workspace SSO). Nếu chưa có, cấu hình IdP trước; không dùng email OTP như một thay thế lâu dài cho SSO công ty.
6. Không tạo policy Bypass cho domain này. Kiểm tra policy theo thứ tự để không có rule Allow rộng hơn.
7. Bật session duration hợp lý theo chính sách công ty và yêu cầu xác thực lại cho vai trò nhạy cảm nếu có.

Sau khi Access bảo vệ hostname, request hợp lệ sẽ có header `Cf-Access-Authenticated-User-Email`. Worker dùng header này và chỉ chấp nhận email `@havigroup.llc`; không có header thì API trả 401.

## 3. Khởi tạo Owner đầu tiên

Khi lệnh `wrangler secret put INITIAL_OWNER_EMAIL` hỏi giá trị, nhập email công ty của người sẽ quản trị đầu tiên. Sau đó người đó đăng nhập Access và mở trang; Worker tự provision tài khoản Owner + các dashboard khởi đầu.

Để đổi Owner về sau, dùng D1 hoặc bổ sung endpoint quản trị có quy trình phê duyệt. Không sửa `INITIAL_OWNER_EMAIL` để thu hồi quyền cũ vì secret này chỉ bootstrap Owner đầu tiên, không phải hệ thống quản trị nhân sự.

## 4. Kiểm tra trước khi bàn giao

- Mở `https://automation.havigroup.llc` ở cửa sổ private: phải bị Cloudflare Access chặn trước khi tới giao diện.
- Đăng nhập bằng email công ty được cấp: chỉ thấy dashboard có membership.
- Với user Viewer: không thấy nút tạo/chạy/duyệt/cấp quyền.
- Với user Operator: gửi lệnh bot chỉ trong dashboard đã gán.
- Với user Reviewer: duyệt/từ chối chỉ trong dashboard đã gán.
- Với Owner/Admin: thêm thành viên vào một dashboard rồi kiểm tra người đó vẫn không thấy dashboard khác.

## 5. Content Image Runner

Không expose Google Flow/ERP runner trực tiếp ra public Internet. Content Image Runner polling Worker qua Access, do đó Flow chỉ cần chạy ở `http://127.0.0.1:8000` trên Mac/VM.

1. Vào **Access → Service Auth → Service Tokens**, tạo token `content-image-runner`. Lưu ngay Client ID và Client Secret vào secret manager của máy runner; Cloudflare chỉ hiện secret một lần.
2. Trong policy của ứng dụng **Automation HaviGroup**, thêm policy **Service Auth**: Include → Service Token → `content-image-runner`. Không thay policy SSO đang dành cho nhân viên.
3. Đặt cùng một giá trị ngẫu nhiên vào Worker secret `RUNNER_SHARED_SECRET` và biến môi trường `AUTOMATION_RUNNER_SECRET` trên runner.
4. Trên runner, copy `runner/content-image-runner.env.example` thành file local không theo dõi Git, điền các Access credentials, nạp file đó rồi chạy `python3 runner/content_image_runner.py`.

Runner chỉ được quyền claim và cập nhật lệnh của `content-image-runner`; mọi lệnh UI vẫn cần Cloudflare Access + role theo dashboard. Không đưa Service Token, `RUNNER_SHARED_SECRET`, ERP credential hay Google cookie vào D1/UI/Git.
