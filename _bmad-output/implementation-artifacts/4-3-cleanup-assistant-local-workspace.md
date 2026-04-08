# Story 4.3: Cleanup assistant cho uploads, downloads và history

Status: done

## Story

As a người vận hành app local lâu dài,
I want một cleanup assistant an toàn cho file và history,
so that workspace luôn gọn mà không làm mất output quan trọng.

## Acceptance Criteria

1. Khi uploads, downloads và job history tăng dần, cleanup assistant phân loại được file tạm, file đã tải, metadata cũ và mục có thể dọn, đồng thời hiển thị rõ mục nào an toàn để xóa.
2. Khi người dùng xác nhận dọn một nhóm dữ liệu, app chỉ xóa những mục thuộc phạm vi cho phép và không vi phạm các rào chắn path an toàn hiện có.
3. Khi artifact local vẫn đang được tham chiếu là quan trọng hoặc gần đây, cleanup assistant giữ lại mặc định hoặc yêu cầu xác nhận rõ ràng hơn trước khi xóa.

## Tasks / Subtasks

- [ ] Thiết kế cleanup scope và safety rules (AC: #1, #2, #3)
  - [ ] Chốt các nhóm dữ liệu có thể dọn: metadata cũ, upload tạm, download không còn tham chiếu, v.v.
  - [ ] Chốt quy tắc giữ lại artifact gần đây hoặc quan trọng.
- [ ] Cập nhật backend cleanup service và path safety (AC: #1, #2)
  - [ ] Dùng `paths.py` và các guard hiện có để tránh path traversal hoặc xóa ngoài phạm vi app quản lý.
  - [ ] Tạo API hoặc action backend để preview và thực thi cleanup an toàn.
- [ ] Cập nhật UI cleanup assistant (AC: #1, #3)
  - [ ] Hiển thị phân loại dữ liệu và xác nhận trước khi xóa.
  - [ ] Làm rõ khác biệt giữa dọn history và xóa file local.
- [ ] Kiểm tra hồi quy với file local còn được tham chiếu (AC: #2, #3)
  - [ ] Đảm bảo không xóa nhầm output quan trọng.
  - [ ] Đảm bảo route download vẫn chỉ phục vụ tệp hợp lệ sau cleanup.

## Dev Notes

- Route `/download/{file_name}` đã có chặn path traversal; cleanup assistant phải giữ nguyên mức an toàn đó. [Source: _bmad-output/project-context.md#Lưu-trữ-file-và-an-toàn-đường-dẫn]
- Tách bạch “dọn metadata/history” và “xóa file local” trong UX và implementation. [Source: _bmad-output/planning-artifacts/prd.md#Journey-5:-Quản-lý-và-tải-kết-quả-local]
- Đây là story về local hygiene, không phải object storage manager; ưu tiên quy tắc đơn giản và an toàn. [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Local-Cleanup-Assistant]

### Project Structure Notes

- Backend trọng tâm: `flow_web/service.py`, `flow_web/paths.py`, có thể `flow_web/main.py` nếu thêm endpoint cleanup.
- Frontend trọng tâm: `flow_web/static/index.html`, `flow_web/static/app.js`, `flow_web/static/styles.css`.
- Persistence vẫn dựa trên `StateStore` và filesystem local hiện có.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.3:-Cleanup-assistant-cho-uploads,-downloads-và-history]
- [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional-Requirements]
- [Source: _bmad-output/project-context.md#Lưu-trữ-file-và-an-toàn-đường-dẫn]
- [Source: _bmad-output/planning-artifacts/architecture.md#Quyết-định-2:-Dùng-local-JSON-thay-vì-database]

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
