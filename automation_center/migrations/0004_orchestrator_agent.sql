-- Agent điều phối: nhắn với agent để nó sửa code, có giới hạn theo quyền.
--
-- Ý tưởng: mọi người trong công ty nhắn yêu cầu sửa vào một luồng chat trên
-- automation.havigroup.llc.  Một runner trên MÁY TRUNG TÂM nhận yêu cầu, gọi
-- ChatGPT để soạn thay đổi, rồi tự chạy test — máy cá nhân không tham gia.
--
-- Ranh giới nằm ở code_scopes, không nằm ở lời nhắc gửi cho ChatGPT.  Một mô
-- hình ngôn ngữ có thể được thuyết phục sửa file ngoài phạm vi; một bảng
-- allowlist thì không.  Phạm vi được kiểm hai lần: Worker chặn trước khi xếp
-- việc, runner chặn lại sau khi đã có patch thật trong tay.  Không có dòng
-- code_scopes nào cho người đó thì họ không xếp được yêu cầu sửa code — đóng
-- mặc định, mở theo từng vai trò.

PRAGMA foreign_keys = ON;

-- Ai được sửa những file nào, tối đa bao nhiêu, và có được áp thẳng không.
-- subject_type='role' áp cho cả vai trò trong dashboard; 'user' là ngoại lệ
-- cho một email cụ thể và luôn thắng dòng theo vai trò.
CREATE TABLE IF NOT EXISTS code_scopes (
  id TEXT PRIMARY KEY,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('role', 'user')),
  subject TEXT NOT NULL,
  -- Mỗi dòng là một glob, ví dụ "flow_web/static/**".  Rỗng = không cho gì.
  allow_globs TEXT NOT NULL DEFAULT '',
  max_files INTEGER NOT NULL DEFAULT 3 CHECK (max_files > 0),
  max_lines INTEGER NOT NULL DEFAULT 200 CHECK (max_lines > 0),
  -- 1 = thay đổi hợp lệ, test xanh thì áp luôn, không cần ai duyệt.
  auto_apply INTEGER NOT NULL DEFAULT 0 CHECK (auto_apply IN (0, 1)),
  note TEXT NOT NULL DEFAULT '',
  updated_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (dashboard_id, subject_type, subject)
);

-- Một luồng trao đổi giữa người dùng và agent điều phối.
CREATE TABLE IF NOT EXISTS agent_threads (
  id TEXT PRIMARY KEY,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  title TEXT NOT NULL DEFAULT '',
  created_by TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_messages (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES agent_threads(id) ON DELETE CASCADE,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('user', 'agent', 'system')),
  author_email TEXT NOT NULL DEFAULT '',
  content TEXT NOT NULL DEFAULT '',
  -- Tin nhắn sinh ra (hoặc báo cáo về) một yêu cầu sửa code cụ thể.
  request_id TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Một yêu cầu gửi cho agent.  Vòng đời khi nó thật sự sửa code:
--   queued → planning → awaiting_approval → approved → applying → applied
-- Nhánh rẽ: answered (chỉ là câu hỏi, agent trả lời chứ không đổi file),
-- rejected (người từ chối), failed (ChatGPT/patch/test hỏng), cancelled
-- (người gửi rút lại).  Phạm vi được đóng băng vào scope_json ngay lúc xếp
-- việc, nên đổi quyền về sau không âm thầm nới rộng một yêu cầu cũ.
CREATE TABLE IF NOT EXISTS code_change_requests (
  id TEXT PRIMARY KEY,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  thread_id TEXT NOT NULL REFERENCES agent_threads(id) ON DELETE CASCADE,
  runner_key TEXT NOT NULL DEFAULT '',
  repo TEXT NOT NULL DEFAULT 'flow-v2',
  requested_by TEXT NOT NULL,
  requested_role TEXT NOT NULL DEFAULT '',
  instruction TEXT NOT NULL,
  scope_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN (
    'queued', 'planning', 'awaiting_approval', 'approved', 'applying',
    'applied', 'answered', 'rejected', 'failed', 'cancelled',
    -- Yêu cầu điều khiển bot khác (chạy / dừng / tiếp tục).  Không sinh diff,
    -- không có nhánh; kết thúc ngay khi Worker chạy xong lệnh.
    'bot_done'
  )),
  -- Agent tóm tắt nó định làm gì, bằng tiếng Việt, cho người không đọc diff.
  plan_summary TEXT NOT NULL DEFAULT '',
  files_json TEXT NOT NULL DEFAULT '[]',
  diff_text TEXT NOT NULL DEFAULT '',
  -- Diff lưu ở đây bị cắt bớt khi quá dài.  Người duyệt phải biết mình đang
  -- nhìn bản đầy đủ hay bản cắt, nếu không họ duyệt phần chưa đọc.
  diff_truncated INTEGER NOT NULL DEFAULT 0 CHECK (diff_truncated IN (0, 1)),
  -- Danh sách lệnh bot đã chạy, để hiện lại trên thẻ yêu cầu và audit.
  bot_commands_json TEXT NOT NULL DEFAULT '[]',
  files_changed INTEGER NOT NULL DEFAULT 0,
  lines_changed INTEGER NOT NULL DEFAULT 0,
  -- 1 = diff chạm file trong danh sách bảo vệ; luôn phải Owner duyệt tay.
  touches_protected INTEGER NOT NULL DEFAULT 0 CHECK (touches_protected IN (0, 1)),
  test_output TEXT NOT NULL DEFAULT '',
  tests_passed INTEGER NOT NULL DEFAULT 0 CHECK (tests_passed IN (0, 1)),
  branch TEXT NOT NULL DEFAULT '',
  commit_sha TEXT NOT NULL DEFAULT '',
  error TEXT NOT NULL DEFAULT '',
  decided_by TEXT NOT NULL DEFAULT '',
  decided_at TEXT,
  auto_applied INTEGER NOT NULL DEFAULT 0 CHECK (auto_applied IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TEXT,
  finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_threads_dashboard ON agent_threads(dashboard_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_messages_thread ON agent_messages(thread_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_code_requests_dashboard ON code_change_requests(dashboard_id, created_at DESC);
-- Hai hàng đợi mà orchestrator runner quét.
CREATE INDEX IF NOT EXISTS idx_code_requests_queue ON code_change_requests(runner_key, status, created_at ASC);
