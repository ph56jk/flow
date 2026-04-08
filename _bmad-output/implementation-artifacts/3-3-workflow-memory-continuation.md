# Story 3.3: Workflow memory cho continuation work

Status: done

## Story

As a người dùng hay lặp lại kiểu continuation giống nhau,
I want app nhớ workflow và context edit gần đây,
so that các lần chỉnh tiếp theo bắt đầu nhanh hơn từ các gợi ý có căn cứ.

## Acceptance Criteria

1. Khi có các job chỉnh sửa hoặc generate thành công gần đây, app đề xuất workflow hoặc context gần nhất có liên quan khi người dùng vào form sửa.
2. Khi người dùng chọn một gợi ý workflow memory, các field liên quan được điền sẵn nhưng người dùng vẫn có thể thay đổi hoặc bỏ qua.
3. Khi workflow memory không còn hợp lệ, app không submit mù và hiển thị hướng dẫn chọn lại workflow khả dụng.

## Tasks / Subtasks

- [ ] Thiết kế mô hình workflow memory nhẹ và local-first (AC: #1, #2, #3)
  - [ ] Chốt rule chọn “memory” từ các job thành công gần đây.
  - [ ] Quyết định lưu memory dưới dạng derive từ jobs hay persist riêng trong state.
- [ ] Cập nhật backend/store nếu cần cho workflow memory (AC: #1)
  - [ ] Giữ storage tối giản và không biến thành hệ preset/skill mới.
  - [ ] Giữ compatibility với state hiện tại.
- [ ] Cập nhật form sửa để hiển thị và áp dụng gợi ý memory (AC: #1, #2)
  - [ ] Render danh sách gợi ý ngắn gọn, không chiếm quá nhiều không gian.
  - [ ] Điền các field liên quan khi người dùng chọn memory.
- [ ] Xử lý workflow memory không hợp lệ (AC: #3)
  - [ ] Chặn submit khi workflow đã stale hoặc không còn trả về từ Flow.
  - [ ] Hiển thị hướng dẫn chọn lại workflow khả dụng.

## Dev Notes

- Đây không phải thư viện preset/skill; mọi UI/copy phải giữ nó như “gợi ý từ lịch sử gần đây”, không như hệ thống mẫu độc lập. [Source: _bmad-output/project-context.md#Quy-tắc-mở-rộng-dự-án]
- Nếu có thể derive từ `jobs` hoặc `workflows`, ưu tiên derive thay vì lưu state mới. [Source: _bmad-output/planning-artifacts/architecture.md#Quyết-định-2:-Dùng-local-JSON-thay-vì-database]
- Memory chỉ nên phục vụ continuation work; không làm loãng màn hình chính với quá nhiều lựa chọn. [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Theme-5:-Lightweight-Guidance-without-Skill-UI]

### Project Structure Notes

- Có thể chạm vào `flow_web/store.py`, `flow_web/service.py`, `flow_web/schemas.py` nếu cần dữ liệu bền hơn.
- Frontend trọng tâm: `flow_web/static/app.js`, `flow_web/static/index.html`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.3:-Workflow-memory-cho-continuation-work]
- [Source: _bmad-output/planning-artifacts/prd.md#Functional-Requirements]
- [Source: _bmad-output/project-context.md#Trường-`skills`-vẫn-còn-trong-state/API-để-tương-thích-backend-hiện-tại]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Workflow-Memory]

## Dev Agent Record

### Agent Model Used

- _TBD_

### Debug Log References

- _TBD_

### Completion Notes List

- _TBD_

### File List

- _TBD_

### Change Log

- 2026-04-07: Story file created from `epics.md`.
- 2026-04-07: Story completed via Ralph/Codex implementation pass.
