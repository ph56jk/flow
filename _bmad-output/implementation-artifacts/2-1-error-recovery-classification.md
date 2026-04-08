# Story 2.1: Phân loại lỗi và action recovery theo ngữ cảnh

Status: done

## Story

As a người dùng vừa gặp lỗi,
I want mỗi job lỗi hiển thị loại lỗi và hành động recovery liên quan,
so that tôi biết nên làm gì tiếp theo thay vì tự đoán.

## Acceptance Criteria

1. Khi backend nhận lỗi từ Flow hoặc browser automation, lỗi được map vào nhóm rõ ràng như auth, project, timeout, browser lock, workflow và hiển thị bằng tiếng Việt dễ hiểu.
2. Khi job có nhóm lỗi đã biết, job card hiển thị các action recovery phù hợp như đăng nhập lại, kiểm tra project, tăng timeout hoặc mở lại browser.
3. Khi lỗi không map được, app vẫn hiển thị fallback message an toàn và cung cấp ít nhất một hành động tiếp theo hợp lệ.

## Tasks / Subtasks

- [ ] Thiết kế taxonomy lỗi và action recovery (AC: #1, #2, #3)
  - [ ] Xác định bộ nhóm lỗi tối thiểu và mapping từ raw error sang nhóm.
  - [ ] Chốt danh sách action recovery hợp lệ cho từng nhóm.
- [ ] Mở rộng lớp humanize lỗi và recovery metadata ở backend (AC: #1, #3)
  - [ ] Cập nhật `flow_web/messages.py` để map lỗi nhất quán hơn.
  - [ ] Cân nhắc thêm metadata lỗi/recovery trong state hoặc job payload theo hướng additive.
- [ ] Cập nhật UI job card để hiển thị action recovery theo ngữ cảnh (AC: #2, #3)
  - [ ] Render action buttons hoặc CTA recovery phù hợp trong `app.js`.
  - [ ] Dùng copy tiếng Việt rõ, tránh tiếng Anh kỹ thuật thô.
- [ ] Kiểm tra hồi quy tối thiểu (AC: #1, #2, #3)
  - [ ] Xác nhận các lỗi cũ vẫn hiển thị đúng sau humanize.
  - [ ] `python3 -m py_compile flow_web/*.py` và `node --check flow_web/static/app.js`.

## Dev Notes

- Mọi lỗi kỹ thuật liên quan Flow nên đi qua `humanize_flow_error(...)` thay vì lộ raw error ra UI. [Source: _bmad-output/project-context.md#Quy-tắc-tích-hợp-Google-Flow]
- Đây là story về classification và guidance; chưa phải story thực hiện retry. Retry nằm ở Story 2.2, vì vậy đừng nhồi luôn payload-clone ở đây. [Source: _bmad-output/planning-artifacts/epics.md#Epic-2:-Guided-Recovery-and-Safe-Retry]
- UI nên render recovery actions theo nhóm lỗi, không hardcode rời rạc ở nhiều nơi. Ưu tiên một hàm map tập trung trong `app.js`. [Source: _bmad-output/planning-artifacts/architecture.md#4.2-Frontend]

### Project Structure Notes

- Backend trọng tâm: `flow_web/messages.py`, `flow_web/service.py`, có thể thêm metadata vào snapshot/job output.
- Frontend trọng tâm: `flow_web/static/app.js`, có thể cần tinh chỉnh `styles.css`.
- Không cần mở subsystem mới; tận dụng job card và message bar hiện có.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.1:-Phân-loại-lỗi-và-action-recovery-theo-ngữ-cảnh]
- [Source: _bmad-output/planning-artifacts/prd.md#Journey-4:-Xử-lý-lỗi-hoặc-job-bị-ngắt]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Theme-2:-Recovery-&-Retry]
- [Source: _bmad-output/project-context.md#Quy-tắc-tích-hợp-Google-Flow]

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
