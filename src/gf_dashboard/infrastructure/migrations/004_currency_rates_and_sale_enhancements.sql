CREATE TABLE currency_rates (
    id TEXT PRIMARY KEY,
    base_currency TEXT NOT NULL CHECK (length(base_currency) = 3),
    quote_currency TEXT NOT NULL CHECK (length(quote_currency) = 3),
    rate_micros INTEGER NOT NULL CHECK (rate_micros > 0),
    rate_date TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (base_currency, quote_currency, rate_date)
);

ALTER TABLE sales ADD COLUMN original_amount_minor INTEGER;
ALTER TABLE sales ADD COLUMN exchange_rate_micros INTEGER;
ALTER TABLE sales ADD COLUMN item_quantity INTEGER DEFAULT 1;
