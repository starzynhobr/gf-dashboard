ALTER TABLE character_vip_subscriptions ADD COLUMN activated_at TEXT;
ALTER TABLE character_vip_subscriptions ADD COLUMN expires_at TEXT;

UPDATE character_vip_subscriptions
SET activated_at = activated_on || 'T00:00:00+00:00',
    expires_at = expires_on || 'T00:00:00+00:00'
WHERE activated_at IS NULL OR expires_at IS NULL;

CREATE INDEX character_vip_subscriptions_active_at_idx
    ON character_vip_subscriptions (workspace_id, character_id, expires_at);
