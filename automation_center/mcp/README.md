# HaviGroup ERP MCP

MCP này chạy cục bộ theo STDIO cho Codex desktop/CLI/IDE. Credential không nằm trong mã nguồn hay `config.toml`; server đọc chúng từ macOS Keychain service `HaviGroup ERP MCP`.

- `bot-token`: raw token của `HVG Agent Bot` (được ưu tiên dùng).
- `api-key` và `api-secret`: credential tương thích Frappe đang dùng tạm thời khi chưa có Bot token.

## Scope và an toàn

- Chỉ GraphQL endpoint chính thức của ERP qua HTTPS.
- Khi có `bot-token`, dùng `Authorization: HVGToken <raw-token>`; token Bot bị giới hạn theo Project membership của bot.
- Chỉ khi chưa cấp `bot-token`, dùng Frappe compatibility auth `Authorization: token <api-key>:<api-secret>` cho cặp credential tạm thời.
- Chỉ cho phép Project `PROJ-0049`; không có generic GraphQL tool.
- Tool ghi (`create_task`, `update_task_status`, `add_task_comment`) cần cả approval của Codex và `confirmed=true`.
- Không có delete, upload tệp, comment attachment, hoặc thao tác token/bot management.

Sau khi Codex khởi động lại, dùng `/mcp` để kiểm tra server **hvg_erp**. Ví dụ: “đọc các task trong PROJ-0049”, “lấy chi tiết TASK-0001”, hoặc “sau khi tôi xác nhận, đổi TASK-0001 sang Working”.
