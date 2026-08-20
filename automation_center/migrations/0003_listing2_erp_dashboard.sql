ALTER TABLE approvals ADD COLUMN runner_run_id TEXT;

CREATE INDEX IF NOT EXISTS idx_approvals_runner_run ON approvals(runner_run_id, created_at ASC);
