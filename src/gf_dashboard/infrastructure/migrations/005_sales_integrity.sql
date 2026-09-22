ALTER TABLE sales ADD COLUMN item_description TEXT;
ALTER TABLE sales ADD COLUMN exchange_rate_source TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE sales ADD COLUMN converted_currency TEXT NOT NULL DEFAULT 'BRL' CHECK (length(converted_currency) = 3);
ALTER TABLE sales ADD COLUMN idempotency_key TEXT;

UPDATE sales
SET item_description = COALESCE(buyer_reference, CASE sale_type WHEN 'gold' THEN 'Gold' ELSE 'Item comercializado' END)
WHERE item_description IS NULL;

CREATE UNIQUE INDEX sales_workspace_idempotency_unique
    ON sales (workspace_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX sales_workspace_sold_at_idx ON sales (workspace_id, sold_at);
