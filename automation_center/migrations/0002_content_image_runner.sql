CREATE TABLE IF NOT EXISTS runners (
  runner_key TEXT PRIMARY KEY,
  label TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'offline'
    CHECK (status IN ('online', 'offline', 'error')),
  version TEXT NOT NULL DEFAULT '',
  last_seen_at TEXT,
  last_error TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_runs (
  id TEXT PRIMARY KEY,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  bot_id TEXT NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
  runner_key TEXT NOT NULL,
  requested_by TEXT NOT NULL REFERENCES users(email),
  title TEXT NOT NULL DEFAULT '',
  prompt TEXT NOT NULL DEFAULT '',
  aspect TEXT NOT NULL DEFAULT 'landscape',
  image_count INTEGER NOT NULL DEFAULT 1 CHECK (image_count BETWEEN 1 AND 4),
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'cancel_requested', 'cancelled', 'completed', 'failed')),
  runner_job_id TEXT NOT NULL DEFAULT '',
  result_json TEXT NOT NULL DEFAULT '{}',
  error TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TEXT,
  finished_at TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bot_runs_runner_queue ON bot_runs(runner_key, status, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_bot_runs_dashboard_created ON bot_runs(dashboard_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_runs_bot_active ON bot_runs(bot_id, status, created_at DESC);

ALTER TABLE approvals ADD COLUMN artifact_url TEXT NOT NULL DEFAULT '';
