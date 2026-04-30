-- CodeBurn v2 Phase 1 schema
-- Observability-first, advisory-only telemetry model.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  task TEXT NOT NULL,
  repo_path TEXT,
  git_branch TEXT,
  created_at TEXT NOT NULL,
  ended_at TEXT,
  ended_by TEXT DEFAULT 'manual',
  data_quality TEXT NOT NULL CHECK (data_quality IN ('complete', 'partial', 'recovered', 'invalid')),
  provider_summary TEXT,
  comparability_token INTEGER NOT NULL DEFAULT 0 CHECK (comparability_token IN (0, 1)),
  comparability_duration INTEGER NOT NULL DEFAULT 1 CHECK (comparability_duration IN (0, 1)),
  comparability_change INTEGER NOT NULL DEFAULT 1 CHECK (comparability_change IN (0, 1))
);

CREATE TABLE IF NOT EXISTS steps (
  step_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  step_kind TEXT NOT NULL CHECK (step_kind IN ('planning', 'execution', 'test', 'retry', 'reflection', 'other')),
  command TEXT NOT NULL,
  provider TEXT,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  duration_ms INTEGER,
  exit_code INTEGER,
  stdout_bytes INTEGER,
  stderr_bytes INTEGER,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  total_tokens INTEGER,
  token_source TEXT CHECK (token_source IN ('provider', 'estimated', 'unknown')),
  retry_of TEXT,
  git_status_before TEXT,
  git_status_after TEXT,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id),
  FOREIGN KEY(retry_of) REFERENCES steps(step_id)
);

CREATE TABLE IF NOT EXISTS changed_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  step_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  change_kind TEXT,
  source TEXT NOT NULL DEFAULT 'git_diff_name_only',
  FOREIGN KEY(step_id) REFERENCES steps(step_id)
);

CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  step_id TEXT,
  signal TEXT NOT NULL,
  type TEXT NOT NULL,
  advisory_only INTEGER NOT NULL CHECK (advisory_only IN (0, 1)),
  can_block INTEGER NOT NULL CHECK (can_block IN (0, 1)),
  confidence TEXT NOT NULL,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id),
  FOREIGN KEY(step_id) REFERENCES steps(step_id)
);

CREATE TABLE IF NOT EXISTS recovery_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  previous_session_id TEXT NOT NULL,
  new_session_id TEXT,
  action_taken TEXT NOT NULL CHECK (action_taken IN ('auto_close_previous', 'resume_previous', 'abort_start')),
  reason TEXT NOT NULL,
  operator TEXT,
  created_at TEXT NOT NULL
);
