# Story 1.1: Chuẩn hóa project và readiness snapshot

Status: done

## Story

As a người dùng mới hoặc quay lại,
I want app chuẩn hóa project input và tính readiness snapshot thống nhất,
so that tôi biết ngay workspace hiện có thể chạy hay đang thiếu bước nào.

## Acceptance Criteria

1. Backend lưu `project_id` đã normalize và `project_url` nhất quán khi người dùng nhập ID hoặc URL project.
2. `/api/state` vẫn giữ shape hiện tại nhưng cung cấp đủ dữ liệu để frontend suy ra readiness snapshot mà không làm gãy UI cũ.
3. Khi project, auth hoặc workflow thay đổi, readiness snapshot và copy trạng thái được cập nhật đồng bộ bằng tiếng Việt có dấu.

## Tasks / Subtasks

- [ ] Thiết kế readiness data contract tương thích ngược (AC: #1, #2)
  - [ ] Liệt kê các cờ readiness tối thiểu cho project, auth, workflow và input availability.
  - [ ] Chốt cách biểu diễn trong `FlowWebService.get_state()` mà không phá shape hiện có của `/api/state`.
- [ ] Cập nhật backend để chuẩn hóa project và trả readiness snapshot (AC: #1, #2)
  - [ ] Giữ normalize logic ở `flow_web/service.py`, không dồn vào route trong `flow_web/main.py`.
  - [ ] Bổ sung dữ liệu readiness vào state theo hướng additive.
- [ ] Cập nhật frontend hiển thị readiness snapshot (AC: #3)
  - [ ] Đọc readiness snapshot trong `flow_web/static/app.js`.
  - [ ] Hiển thị copy trạng thái rõ ràng, tiếng Việt có dấu trong UI hiện có.
- [ ] Kiểm tra hồi quy tối thiểu (AC: #1, #2, #3)
  - [ ] Chạy `python3 -m py_compile flow_web/*.py`.
  - [ ] Chạy `node --check flow_web/static/app.js`.

## Dev Notes

- Giữ `flow_web/main.py` mỏng; mọi logic readiness nên nằm ở `FlowWebService` hoặc helper của service. [Source: _bmad-output/project-context.md#Critical Implementation Rules]
- Không phá contract của `/api/state`; chỉ thêm dữ liệu mới theo hướng tương thích ngược. [Source: _bmad-output/planning-artifacts/architecture.md#6.-Dữ-Liệu-Và-Hợp-Đồng-API]
- Project input có thể là ID hoặc URL đầy đủ; luôn dùng normalize helper hiện có thay vì ghép thủ công. [Source: _bmad-output/project-context.md#Quy-tắc-tích-hợp-Google-Flow]
- Copy hiển thị phải là tiếng Việt có dấu và dễ hiểu cho người mới. [Source: _bmad-output/project-context.md#Quy-tắc-frontend]

### Project Structure Notes

- Backend trọng tâm: `flow_web/service.py`, `flow_web/main.py`, `flow_web/schemas.py`.
- Frontend trọng tâm: `flow_web/static/app.js`, `flow_web/static/index.html`, `flow_web/static/styles.css`.
- Nếu cần lưu bền vững thêm dữ liệu readiness, đi qua `StateStore`; không sửa trực tiếp `data/state.json`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-1:-Guided-Readiness-and-First-Successful-Run]
- [Source: _bmad-output/planning-artifacts/prd.md#Functional-Requirements]
- [Source: _bmad-output/planning-artifacts/architecture.md#4.1-Backend]
- [Source: _bmad-output/project-context.md#Critical-Implementation-Rules]

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
