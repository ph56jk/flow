---
project_name: 'flow'
user_name: 'admin'
date: '2026-04-07'
sections_completed: ['technology_stack', 'critical_implementation_rules']
existing_patterns_found: 11
---

# Project Context for AI Agents

_Tệp này ghi lại những quy tắc và pattern quan trọng mà agent cần bám theo khi sửa hoặc mở rộng dự án. Chỉ ưu tiên các chi tiết dễ bị bỏ sót._

---

## Technology Stack & Versions

- Python `>=3.10` là bắt buộc. Python `3.9` không tương thích vì dự án phụ thuộc `flow-py`.
- Backend dùng `FastAPI` `>=0.115,<1.0` và `uvicorn[standard]` `>=0.30,<1.0`.
- Upload form dùng `python-multipart` `>=0.0.9,<1.0`.
- Tích hợp Google Flow không dùng API chính thức; dự án gọi `flow-py` từ GitHub và vận hành bằng browser automation.
- UI là static web thuần: `flow_web/static/index.html`, `flow_web/static/app.js`, `flow_web/static/styles.css`. Không có bundler, không có React/Vue.
- Dữ liệu runtime lưu cục bộ bằng JSON trong `data/state.json`; file người dùng nằm ở `data/uploads` và `data/downloads`.
- App dùng FastAPI static mounts cho `/static`, `/files/uploads`, `/files/downloads` và route tải file `/download/{file_name}`.
- BMAD đã được cài cục bộ trong dự án; đầu ra chuẩn nên đặt ở `_bmad-output/`.

## Critical Implementation Rules

### Kiến trúc backend

- Giữ `flow_web/main.py` mỏng. Chỉ đặt routing, lifecycle và wiring ở đây; logic nghiệp vụ phải nằm trong `flow_web/service.py`.
- Mọi thay đổi liên quan trạng thái lâu dài phải đi qua `StateStore` trong `flow_web/store.py`. Không cập nhật trực tiếp `data/state.json`.
- Dùng `flow_web/paths.py` để resolve mọi đường dẫn nội bộ. Không hardcode đường dẫn tương đối rải rác.
- `lifespan()` là nơi khởi tạo app directories, store và `FlowWebService`; đừng lặp lại các bước này trong từng endpoint.

### Job, trạng thái và độ bền dữ liệu

- Tác vụ Flow chạy nền bằng `asyncio.create_task(...)` trong `FlowWebService`. Nếu thêm loại job mới, phải theo pattern `enqueue -> persist job -> spawn task -> patch status/log/artifacts`.
- `StateStore` tự sửa các job dở dang thành `interrupted` sau khi server restart. Không giả định job `queued/running/polling` có thể sống qua lần khởi động lại.
- UI hydrate chủ yếu từ `/api/state`. Khi thay schema trả về, phải giữ tương thích cho các khóa `config`, `jobs`, `skills`, `projects`, `auth`.
- Trường `skills` vẫn còn trong state/API để tương thích backend hiện tại, dù giao diện học skill đã bị gỡ khỏi màn hình. Không tự ý đưa lại UI học skill nếu chủ nhân chưa yêu cầu.

### Quy tắc tích hợp Google Flow

- Xem `flow-py` như một lớp browser automation dễ gãy khi Google đổi giao diện. Mọi lỗi trả ra người dùng nên được Việt hóa và dễ hiểu.
- Nếu xử lý lỗi Flow, đi qua `flow_web/messages.py` và hàm `humanize_flow_error(...)` thay vì để raw error tiếng Anh lộ ra UI.
- `project_id` có thể được người dùng dán dưới dạng ID hoặc cả URL project. Bất kỳ chỗ nào nhận input project đều phải normalize theo helper của service, không ghép URL thủ công.
- Các tính năng như login, credits, workflows, generate, edit đều phụ thuộc vào phiên đăng nhập trình duyệt. Đừng giả định có API token ổn định ở backend.

### Quy tắc frontend

- Frontend hiện là DOM manipulation thuần trong `flow_web/static/app.js`. Khi sửa HTML, phải rà lại toàn bộ selector/id tương ứng trong JS.
- Không thêm framework frontend hoặc bước build mới nếu chưa có yêu cầu rõ ràng. Hướng hiện tại ưu tiên triển khai nhanh, dễ bảo trì, ít phụ thuộc.
- Copy giao diện và thông báo lỗi phải dùng tiếng Việt có dấu, giọng thân thiện, dễ tiếp cận cho người mới.
- Giao diện hiện được tối giản để người dùng đi theo luồng `kết nối project -> đăng nhập -> tạo tác vụ`. Khi thêm UI mới, ưu tiên giảm nhiễu thay vì tăng số bảng điều khiển.

### Lưu trữ file và an toàn đường dẫn

- Mọi file upload phải đi vào `data/uploads`; file tải kết quả phải đi vào `data/downloads`.
- Route `/download/{file_name}` đã chặn path traversal bằng cách resolve path dưới `DOWNLOADS_DIR`; mọi thay đổi về tải file phải giữ nguyên mức an toàn này.
- Tên file upload cần được làm gọn về basename và tránh đè file cũ bằng suffix tăng dần, theo pattern đang có trong `save_upload(...)`.

### Quy tắc mở rộng dự án

- Nếu thêm endpoint mới, hãy cân nhắc xem có nên phản ánh vào `/api/state` hoặc vòng refresh của frontend hay không; app hiện phụ thuộc nhiều vào polling nhẹ và local state đồng bộ.
- Nếu thêm kiểu job mới, phải cập nhật cả validation request, title mặc định, render UI và download artifact nếu có.
- Nếu cần tài liệu BMAD mới, dùng `_bmad-output/` làm nơi lưu chuẩn. Không dùng thư mục literal `{output_folder}/` đang tồn tại như nguồn sự thật; đó chỉ là placeholder chưa resolve hết.
