-- Gộp hai nửa: bỏ cột `approvals.runner_run_id` của nửa listing.
--
-- Hai nửa đặt tên khác nhau cho cùng một thứ — "lượt chạy runner nào sinh ra
-- phiếu duyệt này": nửa ảnh gọi là `run_id` (0003_listing2_erp_runner.sql),
-- nửa listing gọi là `runner_run_id` (0003_listing2_erp_dashboard.sql). Giữ cả
-- hai thì mỗi lần ghi phiếu phải nhớ ghi vào ô nào, và sớm muộn có phiếu chỉ
-- điền một ô — lúc đó không truy được lượt chạy nữa. Chỉ giữ `run_id`, vì đó
-- là cột đang có chỉ mục `idx_approvals_pending_push` mà hàng đợi đẩy ảnh dùng.
--
-- AN TOÀN: đây là lệnh xoá dữ liệu, nên chỉ chạy được khi cột còn rỗng. Tại
-- thời điểm viết migration này, `SELECT COUNT(*) FROM approvals` trên D1 thật
-- trả về 0 — chưa có phiếu nào, nên không mất gì. Nếu về sau ai đó chạy
-- migration này trên một cơ sở dữ liệu ĐÃ có phiếu ghi `runner_run_id`, phải
-- chép sang `run_id` trước:
--   UPDATE approvals SET run_id = runner_run_id
--    WHERE (run_id IS NULL OR run_id = '') AND runner_run_id IS NOT NULL;
--
-- Chỉ mục phải xoá trước cột: SQLite không cho bỏ một cột đang nằm trong chỉ mục.
DROP INDEX IF EXISTS idx_approvals_runner_run;

ALTER TABLE approvals DROP COLUMN runner_run_id;
