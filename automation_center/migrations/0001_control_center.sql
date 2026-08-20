PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  email TEXT PRIMARY KEY,
  display_name TEXT NOT NULL DEFAULT '',
  global_role TEXT NOT NULL DEFAULT 'viewer'
    CHECK (global_role IN ('owner', 'admin', 'operator', 'reviewer', 'viewer')),
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dashboards (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  icon TEXT NOT NULL DEFAULT 'grid',
  color TEXT NOT NULL DEFAULT 'teal',
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('active', 'paused', 'draft')),
  runner_required INTEGER NOT NULL DEFAULT 1 CHECK (runner_required IN (0, 1)),
  created_by TEXT NOT NULL REFERENCES users(email),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dashboard_members (
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  user_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'reviewer', 'viewer')),
  granted_by TEXT NOT NULL REFERENCES users(email),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (dashboard_id, user_email)
);

CREATE TABLE IF NOT EXISTS dashboard_projects (
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL,
  project_name TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (dashboard_id, project_id)
);

CREATE TABLE IF NOT EXISTS bots (
  id TEXT PRIMARY KEY,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  purpose TEXT NOT NULL DEFAULT '',
  runner_key TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'paused'
    CHECK (status IN ('running', 'paused', 'needs_runner', 'error')),
  last_run_at TEXT,
  last_run_status TEXT NOT NULL DEFAULT 'never',
  created_by TEXT NOT NULL REFERENCES users(email),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY,
  dashboard_id TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected')),
  requested_by TEXT NOT NULL DEFAULT '',
  reviewed_by TEXT NOT NULL DEFAULT '',
  reviewed_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id TEXT PRIMARY KEY,
  dashboard_id TEXT REFERENCES dashboards(id) ON DELETE SET NULL,
  actor_email TEXT NOT NULL,
  action TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dashboard_members_email ON dashboard_members(user_email);
CREATE INDEX IF NOT EXISTS idx_bots_dashboard ON bots(dashboard_id);
CREATE INDEX IF NOT EXISTS idx_approvals_dashboard_status ON approvals(dashboard_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_dashboard_created ON audit_logs(dashboard_id, created_at DESC);
