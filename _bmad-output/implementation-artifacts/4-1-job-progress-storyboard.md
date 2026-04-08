# Story 4.1: Storyboard tiến trình cho job dài

Status: done

## Story

As a người dùng đang chờ Flow phản hồi,
I want xem storyboard tiến trình của job,
so that tôi biết app còn đang làm việc hay đã mắc ở bước nào.

## Acceptance Criteria

1. Khi job đang chạy hoặc polling, app hiển thị các mốc tiến trình có ý nghĩa như gửi yêu cầu, chờ phản hồi, polling, lưu artifact và hoàn tất thay vì chỉ một trạng thái chung.
2. Khi backend có log hoặc progress hint mới, storyboard phản ánh mốc mới nhất và giúp người dùng phân biệt tiến triển với đứng yên.
3. Khi người dùng dùng bộ lọc trạng thái, danh sách tác vụ vẫn phản ánh đúng bộ lọc và progress storyboard hiển thị đúng cho các job còn lại.

## Tasks / Subtasks

- [ ] Xác định bộ mốc storyboard và nguồn dữ liệu (AC: #1, #2)
  - [ ] Chốt các giai đoạn tiến trình có thể suy ra từ logs/status hiện tại.
  - [ ] Xác định nơi cần thêm progress hint trong backend nếu logs hiện có chưa đủ.
- [ ] Cập nhật backend/logging nhẹ nếu cần (AC: #1, #2)
  - [ ] Bổ sung log/progress message có cấu trúc hơn trong `service.py`.
  - [ ] Giữ log vẫn dễ đọc với người dùng.
- [ ] Render storyboard trong job card và giữ tương thích bộ lọc (AC: #1, #2, #3)
  - [ ] Thêm thành phần storyboard trong `app.js`/`styles.css`.
  - [ ] Xác nhận render vẫn đúng khi lọc `all/active/completed/failed`.
- [ ] Kiểm tra job thành công và job lỗi (AC: #1, #2)
  - [ ] Đảm bảo storyboard dừng đúng ở trạng thái cuối cùng.

## Dev Notes

- Service hiện đã append logs theo tiến trình ở nhiều chỗ; ưu tiên tận dụng chúng trước khi thêm status machine mới. [Source: flow_web/service.py]
- Storyboard phải là lớp diễn giải trạng thái cho người dùng, không phải debugger kỹ thuật. [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Latency-Storyboard]
- Không làm vỡ bộ lọc job hiện có hoặc làm job card quá nặng ở mobile-width. [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional-Requirements]

### Project Structure Notes

- Backend: `flow_web/service.py`.
- Frontend: `flow_web/static/app.js`, `flow_web/static/styles.css`, có thể chạm nhẹ `index.html` nếu cần markup support.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.1:-Storyboard-tiến-trình-cho-job-dài]
- [Source: _bmad-output/planning-artifacts/prd.md#Success-Criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md#5.4-Luồng-tạo-hoặc-sửa-nội-dung]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Priority-5:-Latency-Storyboard]

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
