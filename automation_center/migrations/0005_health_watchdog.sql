-- Watchdog sức khoẻ host runner.
--
-- Lý do có bảng này: ngày 2026-08-15 cả hai runner ngừng heartbeat lúc 01:00Z
-- và không ai biết cho tới hơn 25 tiếng sau.  Dashboard có tính đúng
-- `runner_online` (cửa sổ 45s trên last_seen_at) nhưng nó chỉ đúng khi có người
-- đang mở dashboard ra nhìn.  Không có cron nào, không có đường báo ra ngoài.
--
-- Một sự cố = một hàng còn mở (resolved_at IS NULL).  Chỉ số duy nhất bên dưới
-- là thứ giữ cho cron chạy mỗi 5 phút không đẻ ra 288 hàng một ngày cho cùng
-- một runner chết: sự cố thứ hai cùng (kind, subject) sẽ bị chặn ở tầng DB chứ
-- không dựa vào việc code nhớ kiểm tra trước khi ghi.
CREATE TABLE IF NOT EXISTS health_incidents (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL
    CHECK (kind IN ('runner_offline', 'run_orphaned', 'access_token_expiring')),
  subject TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  opened_at TEXT NOT NULL,
  resolved_at TEXT,
  -- notified_at NULL nghĩa là chưa đẩy được ra ngoài; vòng cron sau sẽ thử lại.
  -- Giữ nguyên NULL khi lỗi là chốt chống mất cảnh báo, giống pushed_at của
  -- approvals ở migration 0003.
  notified_at TEXT,
  notify_error TEXT NOT NULL DEFAULT ''
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_health_incident_open
  ON health_incidents(kind, subject) WHERE resolved_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_health_incident_recent
  ON health_incidents(opened_at DESC);

-- Hàng đợi gửi lại: sự cố đã mở nhưng chưa báo ra ngoài được.
CREATE INDEX IF NOT EXISTS idx_health_incident_unnotified
  ON health_incidents(notified_at, opened_at) WHERE notified_at IS NULL;
