# Story 1.2: Chế độ Golden Path cho lần chạy đầu tiên

Status: done

## Story

As a người mới dùng app,
I want một luồng Golden Path chỉ hiển thị các bước cốt lõi,
so that tôi có thể đi từ project tới login rồi tới tác vụ đầu tiên mà không lạc trong giao diện.

## Acceptance Criteria

1. Khi người dùng chưa hoàn tất project hoặc auth, app hiển thị rõ bước hiện tại trong luồng Golden Path và CTA chính phù hợp.
2. Khi từng bước được hoàn tất, giao diện phản ánh ngay bước kế tiếp mà không bắt người dùng tự suy đoán trạng thái.
3. Người dùng có thể hoàn tất luồng phổ biến mà không cần mở `Cài đặt nâng cao`, và app không yêu cầu tài khoản riêng ngoài phiên Google Flow.

## Tasks / Subtasks

- [ ] Thiết kế lại luồng Golden Path trên UI hiện có (AC: #1, #2)
  - [ ] Xác định các điểm vào chính cho project, auth và create đầu tiên.
  - [ ] Chốt vị trí CTA chính và fallback CTA để không làm rối bố cục hiện tại.
- [ ] Cập nhật frontend cho trạng thái bước và CTA động (AC: #1, #2)
  - [ ] Điều chỉnh logic trong `flow_web/static/app.js` để suy ra bước hiện tại.
  - [ ] Cập nhật `index.html` và `styles.css` để làm rõ đường đi chính.
- [ ] Bảo toàn luồng không cần tài khoản riêng và không cần advanced settings cho case phổ biến (AC: #3)
  - [ ] Đảm bảo copy onboarding không gợi ý tài khoản khác ngoài Google Flow.
  - [ ] Giữ `Cài đặt nâng cao` ngoài Golden Path mặc định.
- [ ] Kiểm tra trải nghiệm trên viewport hẹp và tab order (AC: #1, #2, #3)
  - [ ] Kiểm tra nhanh tính usable ở viewport ~390px.
  - [ ] Xác nhận CTA chính truy cập được bằng bàn phím.

## Dev Notes

- Story này nên build trên readiness snapshot của Story 1.1; không tạo logic readiness mới song song ở frontend. [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1:-Chuẩn-hóa-project-và-readiness-snapshot]
- Giao diện hiện đã tối giản theo luồng `kết nối project -> đăng nhập -> tạo/chỉnh sửa`; story này cần làm rõ hơn đường vàng chứ không thêm dashboard mới. [Source: _bmad-output/project-context.md#Quy-tắc-frontend]
- Không đưa framework mới vào frontend. [Source: _bmad-output/planning-artifacts/architecture.md#Quyết-định-4:-Giữ-frontend-là-static-web-thuần]

### Project Structure Notes

- Chủ yếu chạm vào `flow_web/static/index.html`, `flow_web/static/app.js`, `flow_web/static/styles.css`.
- Có thể cần tinh chỉnh nhẹ copy/state derivation từ backend nhưng không nên mở endpoint mới cho story này.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.2:-Chế-độ-Golden-Path-cho-lần-chạy-đầu-tiên]
- [Source: _bmad-output/planning-artifacts/prd.md#User-Journeys]
- [Source: _bmad-output/planning-artifacts/architecture.md#4.2-Frontend]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md#Prioritization-Results]

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
