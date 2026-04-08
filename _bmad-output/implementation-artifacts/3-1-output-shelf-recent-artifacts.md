# Story 3.1: Output shelf cho artifact gần đây

Status: done

## Story

As a người sáng tạo quay vòng nhiều lần,
I want một output shelf nhỏ hiển thị artifact gần đây với action rõ ràng,
so that tôi có thể mở, tải, chép mã hoặc tái sử dụng output nhanh hơn.

## Acceptance Criteria

1. Khi có artifact từ các job hoàn tất gần đây, output shelf hiển thị preview phù hợp và không bắt người dùng cuộn toàn bộ lịch sử job để tìm.
2. Khi artifact có URL gốc hoặc file local, người dùng có thể mở đúng liên kết hoặc file local và nhận lỗi rõ ràng nếu tệp không còn.
3. Khi người dùng muốn tái sử dụng artifact, output shelf cung cấp action `Chép media id`, `Chép workflow id`, `Dùng để sửa`, `Lưu về máy` ngay cạnh artifact liên quan.

## Tasks / Subtasks

- [ ] Thiết kế data source cho output shelf (AC: #1)
  - [ ] Chốt rule chọn artifact gần đây từ job history hiện có.
  - [ ] Tránh tạo source of truth mới nếu có thể derive từ `jobs`.
- [ ] Cập nhật UI output shelf và preview rendering (AC: #1, #2)
  - [ ] Thêm vùng output shelf trong `index.html`.
  - [ ] Render ảnh/video đúng loại trong `app.js` và `styles.css`.
- [ ] Gắn actions tái sử dụng trực tiếp trên shelf (AC: #2, #3)
  - [ ] Mở link/file local đúng ngữ cảnh.
  - [ ] Cho phép copy media/workflow id và gọi flow `Dùng để sửa`.
- [ ] Kiểm tra với artifact bị thiếu file local (AC: #2)
  - [ ] Xác nhận lỗi hiển thị rõ và không phá UI shelf.

## Dev Notes

- Story này có thể derive toàn bộ từ `state.jobs`; ưu tiên không thêm endpoint nếu chưa thật cần. [Source: _bmad-output/planning-artifacts/architecture.md#6.-Dữ-Liệu-Và-Hợp-Đồng-API]
- Dùng lại logic preview và actions đã có ở job card khi có thể; đừng viết hai hệ hành vi khác nhau cho artifact. [Source: flow_web/static/app.js]
- Output shelf là lớp truy cập nhanh, không thay thế timeline job hiện có. [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Priority-3:-Artifact-to-Edit-Chain-+-Output-Shelf]

### Project Structure Notes

- Chủ yếu chạm vào `flow_web/static/index.html`, `flow_web/static/app.js`, `flow_web/static/styles.css`.
- Có thể cần helper frontend mới để derive recent artifacts từ jobs.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.1:-Output-shelf-cho-artifact-gần-đây]
- [Source: _bmad-output/planning-artifacts/prd.md#Artifact,-Workflow-Và-Tái-Sử-Dụng-Kết-Quả]
- [Source: _bmad-output/project-context.md#Quy-tắc-frontend]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Theme-3:-Artifact-Reuse-&-Creative-Continuity]

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
