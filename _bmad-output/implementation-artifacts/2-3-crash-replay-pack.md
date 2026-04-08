# Story 2.3: Crash replay pack và tóm tắt interrupted work

Status: done

## Story

As a người dùng quay lại sau khi app restart,
I want interrupted work được gom thành một replay pack rõ ràng,
so that tôi có thể khôi phục đà làm việc thay vì đọc log rời rạc.

## Acceptance Criteria

1. Khi server restart trong lúc còn job `queued`, `running` hoặc `polling`, các job đó được chuyển sang `interrupted` và giữ lại log cuối cùng cùng input cần cho recovery.
2. Khi có interrupted jobs, app hiển thị danh sách interrupted work theo cụm rõ ràng và cho phép mở nhanh retry từ từng item.
3. Khi người dùng không cần giữ interrupted jobs nữa, metadata recovery có thể được làm sạch an toàn mà không xóa nhầm artifact local.

## Tasks / Subtasks

- [ ] Hoàn thiện mô hình replay pack cho interrupted work (AC: #1, #2, #3)
  - [ ] Xác định dữ liệu tối thiểu cần giữ lại cho mỗi interrupted job.
  - [ ] Quyết định cách biểu diễn interrupted cluster/replay pack trong state.
- [ ] Cập nhật persistence khi khởi động lại app (AC: #1)
  - [ ] Mở rộng logic repair hiện có trong `StateStore` để giữ đủ ngữ cảnh recovery.
  - [ ] Đảm bảo log cuối và input recovery không bị mất sau save/load.
- [ ] Cập nhật UI interrupted summary và retry entrypoints (AC: #2)
  - [ ] Hiển thị interrupted work theo cụm hoặc khu vực rõ ràng.
  - [ ] Gắn CTA mở retry flow cho từng item interrupted.
- [ ] Thêm cleanup path cho recovery metadata (AC: #3)
  - [ ] Cho phép làm sạch metadata mà không xóa file local liên quan.
  - [ ] Xác nhận hành vi an toàn sau refresh hoặc restart tiếp theo.

## Dev Notes

- `StateStore._repair_incomplete_jobs()` đã chuyển trạng thái sang `interrupted`; story này mở rộng ngữ cảnh và UX xung quanh hành vi đó, không được phá nó. [Source: flow_web/store.py]
- Phần replay pack nên dựa trên dữ liệu đang có trong `JobRecord` và `logs` trước, tránh tạo schema quá nặng. [Source: flow_web/schemas.py]
- Không được xóa artifact local chỉ vì cleanup interrupted metadata; đó là ranh giới rõ trong PRD. [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional-Requirements]

### Project Structure Notes

- Backend: `flow_web/store.py`, `flow_web/service.py`, có thể cần chỉnh `schemas.py`.
- Frontend: `flow_web/static/app.js`, có thể thêm khu interrupted summary trong `index.html`.
- Tập trung vào tính bền dữ liệu local và khả năng recovery sau restart.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.3:-Crash-replay-pack-và-tóm-tắt-interrupted-work]
- [Source: _bmad-output/planning-artifacts/architecture.md#Quyết-định-3:-Chạy-job-nền-bằng-asyncio.create_task]
- [Source: _bmad-output/project-context.md#Job,-trạng-thái-và-độ-bền-dữ-liệu]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Priority-2:-Safe-Retry-Studio-+-Guided-Recovery-Paths]

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
