ALTER TABLE activity_reward_rules
    ADD COLUMN pve_bags_per_completion INTEGER NOT NULL DEFAULT 0
    CHECK (pve_bags_per_completion >= 0);
