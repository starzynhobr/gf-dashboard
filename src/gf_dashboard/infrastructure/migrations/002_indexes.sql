CREATE UNIQUE INDEX accounts_workspace_name_active_unique
    ON accounts (workspace_id, name COLLATE NOCASE)
    WHERE deleted_at IS NULL AND is_active = 1;

CREATE UNIQUE INDEX characters_account_name_active_unique
    ON characters (account_id, name COLLATE NOCASE)
    WHERE deleted_at IS NULL AND is_active = 1;

CREATE INDEX characters_workspace_account_idx ON characters (workspace_id, account_id, sort_order);
CREATE INDEX character_activities_character_idx ON character_activities (workspace_id, character_id, sort_order);
CREATE INDEX activity_rule_versions_lookup_idx
    ON activity_rule_versions (workspace_id, activity_id, effective_from, effective_to);
CREATE INDEX daily_activity_entries_date_idx
    ON daily_activity_entries (workspace_id, activity_date, status);
CREATE INDEX activity_completions_entry_idx
    ON activity_completions (workspace_id, daily_activity_entry_id, sequence_no);
CREATE INDEX farm_sessions_date_idx ON farm_sessions (workspace_id, activity_date, session_type);
CREATE INDEX farm_session_items_item_idx ON farm_session_items (workspace_id, item_id, obtained_at);
CREATE INDEX inventory_movements_item_idx ON inventory_movements (workspace_id, item_id, occurred_at);
CREATE INDEX market_price_quotes_item_idx ON market_price_quotes (workspace_id, item_id, observed_at DESC);
CREATE INDEX transactions_occurred_idx ON transactions (workspace_id, occurred_at);
