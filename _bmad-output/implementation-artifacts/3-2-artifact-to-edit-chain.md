# Story 3.2: Chuỗi hành động artifact-to-edit và prefill sâu cho form sửa

Status: done

## Story

As a người dùng đã có output tốt,
I want đi từ artifact hoặc workflow sang form sửa với prefill sâu,
so that tôi có thể tiếp tục chỉnh sửa trong tối đa hai thao tác.

## Acceptance Criteria

1. Khi người dùng bấm `Dùng để sửa` từ artifact hoặc workflow, app mở đúng form chỉnh sửa và điền sẵn `media id`, `workflow id` cùng các field liên quan.
2. Khi loại chỉnh sửa được suy ra từ action chọn, app chọn đúng `edit type` mặc định và chỉ hiển thị các trường phù hợp.
3. Khi submit chỉnh sửa, các luồng backend hiện có cho extend, upscale, camera, insert và remove tiếp tục hoạt động mà không cần nhập lại dữ liệu đã có trong artifact context.

## Tasks / Subtasks

- [ ] Chuẩn hóa action chain từ artifact sang edit form (AC: #1, #2)
  - [ ] Xác định các action chain cần hỗ trợ như `Sửa tiếp`, `Kéo dài`, `Upscale`, `Dùng làm tham chiếu`.
  - [ ] Chốt cách map action sang `edit type` mặc định.
- [ ] Mở rộng prefill logic trong frontend (AC: #1, #2)
  - [ ] Điền sâu `media id`, `workflow id` và các trường phụ khi có context.
  - [ ] Ẩn/hiện các trường edit đúng theo loại sửa đã chọn.
- [ ] Xác nhận submit flow không gãy backend hiện có (AC: #3)
  - [ ] Kiểm tra các request edit vẫn dùng schema và service path hiện tại.
  - [ ] Tránh nhân đôi logic enqueue job cho edit.
- [ ] Kiểm tra UX hai thao tác tối đa cho luồng phổ biến (AC: #1, #2, #3)
  - [ ] Từ artifact hoàn tất -> mở form sửa -> submit được trong luồng ngắn.

## Dev Notes

- Story này nên tận dụng action buttons hiện đã có trên artifact/job card thay vì thêm một khu điều hướng mới. [Source: flow_web/static/app.js]
- `edit` form hiện đã có logic ẩn/hiện field theo `editType`; story này mở rộng prefill và action mapping, không viết lại toàn bộ form. [Source: flow_web/static/index.html]
- Giữ toàn bộ orchestration edit ở `FlowWebService._run_flow_job`; frontend chỉ lo context và form state. [Source: _bmad-output/planning-artifacts/architecture.md#5.4-Luồng-tạo-hoặc-sửa-nội-dung]

### Project Structure Notes

- Frontend trọng tâm: `flow_web/static/app.js`, `flow_web/static/index.html`, `flow_web/static/styles.css`.
- Backend chủ yếu xác nhận không cần thay đổi lớn; chỉ chỉnh `service.py` nếu metadata artifact cần nhất quán hơn.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.2:-Chuỗi-hành-động-artifact-to-edit-và-prefill-sâu-cho-form-sửa]
- [Source: _bmad-output/planning-artifacts/prd.md#Journey-3:-Đi-từ-kết-quả-cũ-sang-chỉnh-sửa-tiếp]
- [Source: _bmad-output/project-context.md#Quy-tắc-frontend]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Breakthrough-2:-Artifact-to-Edit-Chain]

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
