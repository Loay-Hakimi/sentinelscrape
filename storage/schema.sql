-- SentinelScrape storage schema.
-- Payloads are stored encrypted; only metadata needed for querying and
-- deduplication is kept in clear.

CREATE TABLE IF NOT EXISTS records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT    NOT NULL,
    source_url TEXT    NOT NULL,
    data_hash  TEXT    NOT NULL UNIQUE,   -- sha256 of canonical record; dedup key
    payload    BLOB    NOT NULL,          -- encrypted record (Fernet / AES-256-GCM)
    scraped_at TEXT    NOT NULL           -- ISO-8601 UTC timestamp
);

CREATE INDEX IF NOT EXISTS idx_records_session ON records (session_id);
CREATE INDEX IF NOT EXISTS idx_records_scraped ON records (scraped_at);
