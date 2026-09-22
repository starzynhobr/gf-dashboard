CREATE TABLE character_daily_missions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE RESTRICT,
    activity_date TEXT NOT NULL,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (workspace_id, character_id, activity_date)
);

CREATE INDEX character_daily_missions_workspace_date_idx
    ON character_daily_missions (workspace_id, activity_date);

CREATE TABLE monthly_gold_targets (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    target_month TEXT NOT NULL,
    target_gold INTEGER NOT NULL CHECK (target_gold > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (workspace_id, target_month)
);
