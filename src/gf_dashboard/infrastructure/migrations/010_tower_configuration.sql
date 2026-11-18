CREATE TABLE tower_configurations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL UNIQUE REFERENCES workspaces(id) ON DELETE RESTRICT,
    guild_name TEXT NOT NULL DEFAULT '' CHECK (length(guild_name) <= 120),
    entry_cost_gold INTEGER NOT NULL DEFAULT 25000 CHECK (entry_cost_gold BETWEEN 0 AND 9007199254740991),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE tower_configuration_participants (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    configuration_id TEXT NOT NULL REFERENCES tower_configurations(id) ON DELETE RESTRICT,
    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE RESTRICT,
    sort_order INTEGER NOT NULL CHECK (sort_order >= 0),
    UNIQUE (configuration_id, character_id)
);

CREATE TABLE tower_configuration_items (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    configuration_id TEXT NOT NULL REFERENCES tower_configurations(id) ON DELETE RESTRICT,
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE RESTRICT,
    estimated_unit_value_gold INTEGER CHECK (estimated_unit_value_gold BETWEEN 0 AND 9007199254740991),
    sort_order INTEGER NOT NULL CHECK (sort_order >= 0),
    UNIQUE (configuration_id, item_id)
);

CREATE TABLE tower_configuration_requests (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    idempotency_key TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (workspace_id, idempotency_key)
);

CREATE TABLE tower_registration_requests (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    idempotency_key TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    farm_session_id TEXT NOT NULL REFERENCES farm_sessions(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    UNIQUE (workspace_id, idempotency_key)
);

CREATE TABLE tower_session_details_updated (
    farm_session_id TEXT PRIMARY KEY REFERENCES farm_sessions(id) ON DELETE RESTRICT,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    guild_name_snapshot TEXT,
    opened_at TEXT NOT NULL,
    entry_cost_gold_snapshot INTEGER NOT NULL CHECK (entry_cost_gold_snapshot BETWEEN 0 AND 9007199254740991),
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    completed_at TEXT,
    rules_version_id TEXT REFERENCES activity_rule_versions(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    CHECK ((completed = 1 AND completed_at IS NOT NULL) OR completed = 0)
);
INSERT INTO tower_session_details_updated SELECT * FROM tower_session_details;
DROP TABLE tower_session_details;
ALTER TABLE tower_session_details_updated RENAME TO tower_session_details;
