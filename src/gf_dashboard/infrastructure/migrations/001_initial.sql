CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'local',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE local_profiles (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    display_name TEXT NOT NULL,
    timezone TEXT NOT NULL,
    locale TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    server_name TEXT NOT NULL,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE characters (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    class_name TEXT NOT NULL,
    level INTEGER NOT NULL CHECK (level >= 0),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE activities (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('dungeon', 'special')),
    frequency_type TEXT NOT NULL CHECK (frequency_type IN ('daily', 'occasional')),
    default_target_amount INTEGER NOT NULL CHECK (default_target_amount >= 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    is_special INTEGER NOT NULL DEFAULT 0 CHECK (is_special IN (0, 1)),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE character_activities (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE RESTRICT,
    activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE RESTRICT,
    target_amount INTEGER NOT NULL CHECK (target_amount >= 0),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE activity_rule_versions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE RESTRICT,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    max_completions INTEGER CHECK (max_completions >= 0),
    target_amount INTEGER NOT NULL CHECK (target_amount >= 0),
    rules_status TEXT NOT NULL CHECK (rules_status IN ('confirmed', 'informational', 'unknown')),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE items (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    rarity TEXT,
    icon_ref TEXT,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE activity_reward_rules (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    rule_version_id TEXT NOT NULL REFERENCES activity_rule_versions(id) ON DELETE RESTRICT,
    mission_key TEXT NOT NULL,
    mission_limit_type TEXT NOT NULL CHECK (mission_limit_type IN ('limited', 'unlimited')),
    reward_type TEXT NOT NULL CHECK (reward_type IN ('gold', 'item')),
    item_id TEXT REFERENCES items(id) ON DELETE RESTRICT,
    amount_per_completion INTEGER NOT NULL CHECK (amount_per_completion >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    CHECK ((reward_type = 'gold' AND item_id IS NULL) OR (reward_type = 'item' AND item_id IS NOT NULL))
);

CREATE TABLE activity_cost_rules (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    rule_version_id TEXT NOT NULL REFERENCES activity_rule_versions(id) ON DELETE RESTRICT,
    cost_type TEXT NOT NULL,
    item_id TEXT REFERENCES items(id) ON DELETE RESTRICT,
    amount INTEGER NOT NULL CHECK (amount >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE activity_windows (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    rule_version_id TEXT NOT NULL REFERENCES activity_rule_versions(id) ON DELETE RESTRICT,
    weekday INTEGER CHECK (weekday BETWEEN 0 AND 6),
    opens_at_local TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
    timezone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE market_price_quotes (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE RESTRICT,
    unit_value_gold INTEGER NOT NULL CHECK (unit_value_gold >= 0),
    observed_at TEXT NOT NULL,
    source TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE gold_exchange_quotes (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    gold_amount INTEGER NOT NULL CHECK (gold_amount > 0),
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    observed_at TEXT NOT NULL,
    source TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE daily_activity_entries (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    character_activity_id TEXT NOT NULL REFERENCES character_activities(id) ON DELETE RESTRICT,
    activity_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped')),
    progress_amount INTEGER NOT NULL DEFAULT 0 CHECK (progress_amount >= 0),
    started_at TEXT,
    completed_at TEXT,
    skipped_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (character_activity_id, activity_date),
    CHECK ((status = 'completed' AND completed_at IS NOT NULL) OR status != 'completed')
);

CREATE TABLE activity_completions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    daily_activity_entry_id TEXT NOT NULL REFERENCES daily_activity_entries(id) ON DELETE RESTRICT,
    sequence_no INTEGER NOT NULL CHECK (sequence_no > 0),
    completed_at TEXT NOT NULL,
    gold_reward_snapshot INTEGER NOT NULL CHECK (gold_reward_snapshot >= 0),
    pve_bags_snapshot INTEGER NOT NULL CHECK (pve_bags_snapshot >= 0),
    rule_version_id TEXT NOT NULL REFERENCES activity_rule_versions(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (daily_activity_entry_id, sequence_no)
);

CREATE TABLE farm_sessions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    session_type TEXT NOT NULL CHECK (session_type IN ('activity', 'tower')),
    primary_character_id TEXT REFERENCES characters(id) ON DELETE RESTRICT,
    activity_id TEXT REFERENCES activities(id) ON DELETE RESTRICT,
    activity_date TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    duration_seconds INTEGER CHECK (duration_seconds >= 0),
    runs_count INTEGER NOT NULL DEFAULT 0 CHECK (runs_count >= 0),
    gold_earned INTEGER NOT NULL DEFAULT 0 CHECK (gold_earned >= 0),
    pve_bags_earned INTEGER NOT NULL DEFAULT 0 CHECK (pve_bags_earned >= 0),
    status TEXT NOT NULL CHECK (status IN ('planned', 'completed', 'cancelled')),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE farm_session_participants (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    farm_session_id TEXT NOT NULL REFERENCES farm_sessions(id) ON DELETE RESTRICT,
    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE RESTRICT,
    role TEXT,
    joined_at TEXT,
    left_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (farm_session_id, character_id)
);

CREATE TABLE tower_session_details (
    farm_session_id TEXT PRIMARY KEY REFERENCES farm_sessions(id) ON DELETE RESTRICT,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    guild_name_snapshot TEXT,
    opened_at TEXT NOT NULL,
    entry_cost_gold_snapshot INTEGER NOT NULL CHECK (entry_cost_gold_snapshot = 25000),
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    completed_at TEXT,
    rules_version_id TEXT REFERENCES activity_rule_versions(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    CHECK ((completed = 1 AND completed_at IS NOT NULL) OR completed = 0)
);

CREATE TABLE farm_session_items (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    farm_session_id TEXT NOT NULL REFERENCES farm_sessions(id) ON DELETE RESTRICT,
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    estimated_unit_value_at_drop INTEGER CHECK (estimated_unit_value_at_drop >= 0),
    obtained_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE inventory_movements (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE RESTRICT,
    character_id TEXT REFERENCES characters(id) ON DELETE RESTRICT,
    farm_session_id TEXT REFERENCES farm_sessions(id) ON DELETE RESTRICT,
    movement_type TEXT NOT NULL CHECK (movement_type IN ('acquisition', 'sale', 'adjustment')),
    quantity_delta INTEGER NOT NULL CHECK (quantity_delta != 0),
    unit_value_snapshot INTEGER CHECK (unit_value_snapshot >= 0),
    occurred_at TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE sales (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    sale_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'completed', 'cancelled')),
    gold_quantity INTEGER NOT NULL DEFAULT 0 CHECK (gold_quantity >= 0),
    real_amount_minor INTEGER CHECK (real_amount_minor >= 0),
    currency TEXT CHECK (currency IS NULL OR length(currency) = 3),
    buyer_reference TEXT,
    sold_at TEXT,
    fees_minor INTEGER NOT NULL DEFAULT 0 CHECK (fees_minor >= 0),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer', 'adjustment')),
    category TEXT NOT NULL,
    amount_gold INTEGER NOT NULL DEFAULT 0 CHECK (amount_gold >= 0),
    amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (amount_minor >= 0),
    currency TEXT CHECK (currency IS NULL OR length(currency) = 3),
    character_id TEXT REFERENCES characters(id) ON DELETE RESTRICT,
    item_id TEXT REFERENCES items(id) ON DELETE RESTRICT,
    sale_id TEXT REFERENCES sales(id) ON DELETE RESTRICT,
    farm_session_id TEXT REFERENCES farm_sessions(id) ON DELETE RESTRICT,
    occurred_at TEXT NOT NULL,
    description TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE devices (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    app_version TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE settings (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (workspace_id, scope, key)
);

CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    before_json TEXT,
    after_json TEXT,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE dashboard_layouts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
    layout_version INTEGER NOT NULL DEFAULT 1 CHECK (layout_version > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE dashboard_layout_items (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    layout_id TEXT NOT NULL REFERENCES dashboard_layouts(id) ON DELETE RESTRICT,
    module_key TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    sort_order INTEGER NOT NULL DEFAULT 0,
    region TEXT NOT NULL,
    column_span INTEGER NOT NULL DEFAULT 1 CHECK (column_span > 0),
    row_span INTEGER NOT NULL DEFAULT 1 CHECK (row_span > 0),
    settings_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (layout_id, module_key)
);

CREATE TABLE routine_schedules (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    start_time_local TEXT NOT NULL,
    timezone TEXT NOT NULL,
    weekdays_mask INTEGER NOT NULL CHECK (weekdays_mask >= 0),
    notification_offset_minutes INTEGER NOT NULL DEFAULT 0 CHECK (notification_offset_minutes >= 0),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
