CREATE TABLE character_vip_subscriptions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE RESTRICT,
    activated_on TEXT NOT NULL,
    expires_on TEXT NOT NULL,
    paid_gold INTEGER NOT NULL CHECK (paid_gold > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    CHECK (expires_on > activated_on)
);

CREATE INDEX character_vip_subscriptions_active_idx
    ON character_vip_subscriptions (workspace_id, character_id, expires_on);
