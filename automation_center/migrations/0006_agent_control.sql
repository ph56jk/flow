-- Agent trung tâm: một agent điều khiển các agent còn lại (chạy / dừng / xem
-- trạng thái / khôi phục run mồ côi).
--
-- Ranh giới nằm ở agent_control_scopes, không nằm ở lời nhắc gửi cho mô hình.
-- Một mô hình ngôn ngữ có thể bị thuyết phục đòi dừng nhầm bot; một bảng
-- allowlist thì không.  Worker kiểm TỪNG lệnh trước khi chạy, độc lập với đề
-- xuất của mô hình, và ghi lại cả lệnh bị từ chối.
--
-- Ba lớp (PRD mục 6), độc lập nhau:
--   lớp 1  capability agent_control / agent_recover của vai trò;
--   lớp 2  dòng agent_control_scopes, ĐÓNG BĂNG vào requests.scope_json lúc
--          xếp yêu cầu — sửa quyền sau đó không nới một yêu cầu đang chờ;
--   lớp 3  PROTECTED_RUNNER_KEYS trong worker.js — hằng số, không nằm trong
--          bảng nào, nên không ai cấp quyền vượt qua được nó.
--
-- Không đổi bảng nào đang có: runners, bots, bot_runs, approvals giữ nguyên.
-- Lệnh start/stop chỉ GHI VÀO chúng qua đúng các câu SQL mà nút bấm đang dùng.

PRAGMA foreign_keys = ON;

-- Ai được điều khiển runner nào, bằng action gì, tối đa bao nhiêu lệnh/ngày.
-- subject_type='role' áp cho cả vai trò trong dashboard; 'user' là ngoại lệ
-- cho một email cụ thể và luôn thắng dòng theo vai trò.
CREATE TABLE IF NOT EXISTS agent_control_scopes (
  id TEXT PRIMARY KEY,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('role', 'user')),
  subject TEXT NOT NULL,
  -- Mỗi dòng một runner_key, SO KHỚP BẰNG NHAU — không glob.  Runner key là
  -- định danh máy móc do Owner đặt, không phải cây thư mục; glob ở đây chỉ mở
  -- đường cho "*-runner" khớp cả key tương lai chưa ai duyệt.
  allow_runner_keys TEXT NOT NULL DEFAULT '',
  -- csv trong: start,stop,status,recover
  allow_actions TEXT NOT NULL DEFAULT 'status',
  max_commands_per_day INTEGER NOT NULL DEFAULT 20 CHECK (max_commands_per_day > 0),
  -- 'HH-HH' giờ Asia/Ho_Chi_Minh, rỗng = mọi giờ.  Chuỗi gõ sai bị Worker coi
  -- là ĐÓNG, không phải mở (parseAllowedHours).  stop được miễn khung giờ.
  allowed_hours TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  updated_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (dashboard_id, subject_type, subject)
);

-- Một yêu cầu điều khiển (một tin nhắn, hoặc một cú bấm nút).
--   queued → planning → executing → completed | answered
-- Nhánh rẽ: failed, rejected, cancelled.  Đường B (bấm nút) đi thẳng
-- queued → executing → completed trong cùng một request Worker, không qua
-- runner trung tâm và không qua mô hình ngôn ngữ nào.
CREATE TABLE IF NOT EXISTS agent_control_requests (
  id TEXT PRIMARY KEY,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  thread_id TEXT NOT NULL DEFAULT '',
  runner_key TEXT NOT NULL DEFAULT 'agent-control-runner',
  requested_by TEXT NOT NULL,
  requested_role TEXT NOT NULL DEFAULT '',
  instruction TEXT NOT NULL,
  -- Phạm vi đóng băng lúc xếp hàng.  Đọc lại từ đây, không tra lại bảng.
  scope_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN (
    'queued', 'planning', 'executing', 'completed', 'answered',
    'failed', 'rejected', 'cancelled'
  )),
  plan_summary TEXT NOT NULL DEFAULT '',
  error TEXT NOT NULL DEFAULT '',
  decided_by TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TEXT,
  finished_at TEXT
);

-- Từng lệnh cụ thể sau khi Worker đã kiểm.  Cả lệnh bị từ chối cũng nằm đây:
-- audit phải thấy được "ai (hoặc mô hình nào) đã đòi gì và bị chặn ở lớp nào".
--
-- created_at luôn được Worker ghi tường minh bằng ISO-8601 UTC ('...T...Z').
-- Câu đếm trần lệnh/ngày so sánh chuỗi với mốc 00:00 giờ VN cũng ở dạng ISO,
-- nên đừng để cột này rơi về DEFAULT CURRENT_TIMESTAMP ('YYYY-MM-DD HH:MM:SS'):
-- hai định dạng đó không so sánh chuỗi với nhau được.
CREATE TABLE IF NOT EXISTS agent_control_commands (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL REFERENCES agent_control_requests(id) ON DELETE CASCADE,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL DEFAULT 0,
  action TEXT NOT NULL CHECK (action IN ('start', 'stop', 'status', 'recover')),
  target_bot_id TEXT NOT NULL DEFAULT '',
  target_runner_key TEXT NOT NULL DEFAULT '',
  -- Run bị stop/recover, hoặc run sinh ra bởi start.
  target_run_id TEXT NOT NULL DEFAULT '',
  params_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'executed' CHECK (status IN (
    'executed', 'rejected', 'failed', 'cancelled'
  )),
  reject_reason TEXT NOT NULL DEFAULT '',
  result_json TEXT NOT NULL DEFAULT '{}',
  requested_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_control_requests_queue
  ON agent_control_requests(runner_key, status, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_control_requests_dashboard
  ON agent_control_requests(dashboard_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_control_commands_request
  ON agent_control_commands(request_id, seq ASC);
-- Đếm trần lệnh/ngày của một người.
CREATE INDEX IF NOT EXISTS idx_control_commands_sender
  ON agent_control_commands(requested_by, created_at DESC);
