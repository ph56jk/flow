# Story 2.2: Retry từ job lỗi hoặc bị ngắt với payload clone

Status: done

## Story

As a người dùng muốn chạy lại nhanh,
I want clone payload từ job lỗi hoặc bị ngắt sang một retry flow,
so that tôi có thể chạy lại tác vụ mà không phải nhập lại từ đầu.

## Acceptance Criteria

1. Khi người dùng bấm `Chạy lại` trên job `failed` hoặc `interrupted`, app tạo một retry flow mới dựa trên input cũ mà không sửa đổi job gốc.
2. Khi retry flow được mở, người dùng có thể điều chỉnh các trường được phép như prompt, timeout hoặc workflow và các thay đổi chỉ áp dụng cho lần retry mới.
3. Khi enqueue retry, job mới vẫn được phân biệt với job gốc trong history và không làm mất trace của lần chạy trước.

## Tasks / Subtasks

- [ ] Thiết kế contract cho retry payload clone (AC: #1, #2, #3)
  - [ ] Chốt tập field nào được clone nguyên và field nào cho phép chỉnh.
  - [ ] Quyết định cách liên kết job retry với job gốc trong metadata/state.
- [ ] Cập nhật backend hỗ trợ tạo retry flow (AC: #1, #3)
  - [ ] Thêm helper để dựng `CreateJobRequest` từ input cũ an toàn.
  - [ ] Đảm bảo job gốc không bị mutate khi tạo retry.
- [ ] Cập nhật UI để mở retry flow và cho chỉnh nhanh (AC: #1, #2)
  - [ ] Thêm action `Chạy lại` vào job card phù hợp.
  - [ ] Prefill form theo job type với input clone và cho chỉnh các field cho phép.
- [ ] Kiểm tra hiển thị history giữa job gốc và retry (AC: #3)
  - [ ] Xác nhận người dùng vẫn phân biệt được bản gốc và retry.
  - [ ] Xác nhận refresh trang không làm mất retry context.

## Dev Notes

- Reuse model/request hiện có thay vì tạo một pipeline retry tách rời khỏi `enqueue_job`. [Source: _bmad-output/planning-artifacts/architecture.md#5.4-Luồng-tạo-hoặc-sửa-nội-dung]
- Nếu thêm metadata như `retry_of_job_id`, làm theo hướng additive trong `JobRecord.input` hoặc `result`, tránh migration lớn. [Source: flow_web/schemas.py]
- Story này nối với Story 2.1: UI retry action nên tận dụng taxonomy lỗi/recovery đã có thay vì render một nút mồ côi. [Source: _bmad-output/planning-artifacts/epics.md#Story-2.1:-Phân-loại-lỗi-và-action-recovery-theo-ngữ-cảnh]

### Project Structure Notes

- Backend: `flow_web/service.py`, `flow_web/schemas.py`, có thể `flow_web/main.py` nếu cần endpoint riêng.
- Frontend: `flow_web/static/app.js` và các form hiện có trong `index.html`.
- Giữ local history là nguồn thật; không dùng storage phụ ngoài `StateStore`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.2:-Retry-từ-job-lỗi-hoặc-bị-ngắt-với-payload-clone]
- [Source: _bmad-output/planning-artifacts/prd.md#Functional-Requirements]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Priority-2:-Safe-Retry-Studio-+-Guided-Recovery-Paths]
- [Source: _bmad-output/project-context.md#Job,-trạng-thái-và-độ-bền-dữ-liệu]

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
