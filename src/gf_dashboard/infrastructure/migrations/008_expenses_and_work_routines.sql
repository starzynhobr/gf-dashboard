CREATE INDEX transactions_expense_category_idx
    ON transactions (workspace_id, type, category, occurred_at);

CREATE TABLE work_routine_sessions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (status IN ('running', 'paused', 'completed')),
    started_at TEXT NOT NULL,
    paused_at TEXT,
    finished_at TEXT,
    accumulated_seconds INTEGER NOT NULL DEFAULT 0 CHECK (accumulated_seconds >= 0),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    CHECK (
        (status = 'running' AND paused_at IS NULL AND finished_at IS NULL)
        OR (status = 'paused' AND paused_at IS NOT NULL AND finished_at IS NULL)
        OR (status = 'completed' AND finished_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX work_routine_sessions_one_active_idx
    ON work_routine_sessions (workspace_id)
    WHERE status IN ('running', 'paused') AND deleted_at IS NULL;

CREATE INDEX work_routine_sessions_workspace_finished_idx
    ON work_routine_sessions (workspace_id, finished_at);
