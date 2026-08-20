-- Listing 2 · ERP / Etsy runner.
--
-- Hai thứ còn thiếu để nối Automation Center với phần ERP đã có sẵn trong Flow:
--
--   1. bot_runs chưa mang được mã Task ERP nguồn, nên runner không biết phải
--      ghi ảnh về Task nào.
--   2. approvals không trỏ ngược về lần chạy sinh ra nó, nên sau khi người dùng
--      bấm Duyệt thì không ai biết ảnh đó thuộc Flow job nào / artefact thứ mấy.
--      Flow đã có sẵn POST /api/jobs/{job_id}/artifacts/{index}/approval để
--      "resume the ERP step", chỉ thiếu đường dẫn quyết định duyệt về tới đó.
--
-- pushed_at đánh dấu quyết định đã được đẩy sang Flow, để runner không đẩy lại
-- sau mỗi vòng poll.

ALTER TABLE bot_runs ADD COLUMN erp_task_id TEXT NOT NULL DEFAULT '';

ALTER TABLE approvals ADD COLUMN run_id TEXT NOT NULL DEFAULT '';
ALTER TABLE approvals ADD COLUMN artifact_index INTEGER NOT NULL DEFAULT 0;
ALTER TABLE approvals ADD COLUMN pushed_at TEXT;
ALTER TABLE approvals ADD COLUMN push_error TEXT NOT NULL DEFAULT '';

-- Hàng đợi mà runner quét: đã có quyết định nhưng chưa đẩy về Flow.
CREATE INDEX IF NOT EXISTS idx_approvals_pending_push
  ON approvals(run_id, status, pushed_at);
