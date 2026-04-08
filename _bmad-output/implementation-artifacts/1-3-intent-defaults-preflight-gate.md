# Story 1.3: Mặc định theo ý định và preflight gate cho form tạo nội dung

Status: done

## Story

As a người sáng tạo nội dung,
I want form tạo ảnh và video có mặc định phù hợp theo ý định và chặn submit sai điều kiện,
so that tôi tạo tác vụ nhanh hơn và giảm lỗi có thể đoán trước.

## Acceptance Criteria

1. Khi người dùng chọn intent tạo ảnh hoặc video, app điền sẵn các giá trị mặc định hợp lý như aspect, count hoặc timeout nhưng vẫn cho phép chỉnh tay.
2. Khi thiếu điều kiện tối thiểu để chạy job, app không enqueue job và hiển thị rõ điều kiện còn thiếu cùng cách xử lý.
3. Khi input hợp lệ, luồng submit vẫn dùng backend hiện tại và không phá các khả năng create image/video đã có.

## Tasks / Subtasks

- [ ] Xác định logic mặc định theo intent (AC: #1)
  - [ ] Chốt các intent chính và map default fields cho từng intent.
  - [ ] Đảm bảo defaults không override giá trị người dùng đã sửa bằng tay.
- [ ] Thêm preflight gate ở frontend và backend (AC: #2)
  - [ ] Chặn submit sớm ở frontend với lý do rõ ràng.
  - [ ] Giữ validate backend như lớp an toàn cuối cùng trong `service.py`.
- [ ] Tích hợp submit flow với logic mới mà không làm gãy generate hiện có (AC: #3)
  - [ ] Kiểm tra create image, create video, image-to-video vẫn dùng request model hiện tại.
  - [ ] Cập nhật copy thông báo để hướng người dùng sửa input nhanh.
- [ ] Chạy kiểm tra hồi quy tối thiểu (AC: #1, #2, #3)
  - [ ] `python3 -m py_compile flow_web/*.py`
  - [ ] `node --check flow_web/static/app.js`

## Dev Notes

- Story này nên tái sử dụng readiness data từ Story 1.1 và luồng Golden Path từ Story 1.2 thay vì tạo thêm cơ chế thứ ba. [Source: _bmad-output/planning-artifacts/epics.md#Epic-1:-Guided-Readiness-and-First-Successful-Run]
- Validation request chính hiện ở `FlowWebService._validate_job_request`; nếu bổ sung guardrail, giữ nó ở service layer. [Source: flow_web/service.py]
- Không enqueue job khi biết chắc thất bại do thiếu điều kiện; ưu tiên fail-fast trước khi tạo record thừa. [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Action-Planning]

### Project Structure Notes

- Frontend: `flow_web/static/app.js` là nơi áp intent defaults và gate submit.
- Backend: `flow_web/service.py`, `flow_web/schemas.py` nếu cần làm rõ contract request.
- Không cần tạo subsystem mới; mở rộng form hiện có là đủ.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.3:-Mặc-định-theo-ý-định-và-preflight-gate-cho-form-tạo-nội-dung]
- [Source: _bmad-output/planning-artifacts/prd.md#Functional-Requirements]
- [Source: _bmad-output/project-context.md#Job,-trạng-thái-và-độ-bền-dữ-liệu]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Theme-1:-Readiness-&-Onboarding]

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
