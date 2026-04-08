# Story 4.2: Trust signals layer và project health timeline

Status: done

## Story

As a người dùng quay lại app sau một thời gian,
I want thấy trust signals và health timeline của project,
so that tôi quyết định nhanh có nên chạy tiếp hay cần sửa môi trường trước.

## Acceptance Criteria

1. Khi app có dữ liệu về auth, project, workflow và artifact local, dashboard hiển thị trust signals ngắn gọn như `Project hợp lệ`, `Đăng nhập còn hiệu lực`, `Workflow có sẵn`, `Artifact local còn tồn tại`.
2. Khi project có lịch sử hoạt động đủ gần, app tóm tắt được health timeline với các dấu hiệu như login ổn, timeout tăng, workflow rỗng hoặc interrupted jobs mà không trở thành màn hình quá kỹ thuật.
3. Khi người dùng quay lại app sau refresh hoặc lần mở sau, trust signals và health timeline vẫn có dữ liệu nền phù hợp và không buộc thiết lập lại từ đầu.

## Tasks / Subtasks

- [ ] Xác định trust signals và cách derive chúng từ state hiện có (AC: #1, #3)
  - [ ] Chốt danh sách tín hiệu trust tối thiểu.
  - [ ] Xác định tín hiệu nào derive từ state hiện tại, tín hiệu nào cần metadata mới.
- [ ] Thiết kế health timeline cấp project (AC: #2, #3)
  - [ ] Chốt rule tổng hợp interrupted jobs, timeout patterns và workflow availability.
  - [ ] Giữ timeline ở mức product-facing, không quá kỹ thuật.
- [ ] Cập nhật dashboard UI cho trust signals và health timeline (AC: #1, #2)
  - [ ] Thêm badge/card hoặc timeline gọn trong `index.html`/`app.js`.
  - [ ] Giữ visual density thấp, ưu tiên dễ đọc.
- [ ] Xác nhận dữ liệu bền qua refresh và session sau (AC: #3)
  - [ ] Kiểm tra hydrate từ state hiện có.
  - [ ] Kiểm tra fallback khi dữ liệu chưa đủ.

## Dev Notes

- Story này có thể reuse state local, jobs và auth status hiện có; đừng biến nó thành analytics subsystem mới. [Source: _bmad-output/planning-artifacts/architecture.md#6.-Dữ-Liệu-Và-Hợp-Đồng-API]
- Trust signals nên là dấu hiệu ngắn, ổn định, ít gây nhiễu, không phải flood badge trên mọi panel. [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Breakthrough-1:-Trust-Signals-Layer]
- Health timeline cấp project nên phục vụ quyết định “có nên chạy tiếp hay không”, không phải audit log chi tiết. [Source: _bmad-output/planning-artifacts/prd.md#Project-Type-Requirements]

### Project Structure Notes

- Frontend trọng tâm: `flow_web/static/index.html`, `flow_web/static/app.js`, `flow_web/static/styles.css`.
- Backend có thể cần helper derive project health trong `flow_web/service.py` nếu frontend derive quá rối.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.2:-Trust-signals-layer-và-project-health-timeline]
- [Source: _bmad-output/planning-artifacts/prd.md#Success-Criteria]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Theme-4:-Observability-&-Time-Awareness]
- [Source: _bmad-output/project-context.md#Quy-tắc-frontend]

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
