-- Bảng log cho mỗi file được load vào Bronze (Task 1.3.2).
-- Idempotent: db_utils.ensure_ingest_log() chạy file này ở đầu mỗi lần chạy loader.
CREATE TABLE IF NOT EXISTS raw.ingest_log (
    log_id          BIGSERIAL   PRIMARY KEY,
    batch_id        UUID        NOT NULL,
    source_name     TEXT        NOT NULL,
    source_file     TEXT,
    source_platform TEXT,
    rows_loaded     INTEGER     NOT NULL DEFAULT 0,
    status          TEXT        NOT NULL CHECK (status IN ('SUCCESS', 'FAILED')),
    error_message   TEXT,
    duration_sec    NUMERIC(10, 2),
    logged_at       TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ingest_log_batch  ON raw.ingest_log (batch_id);
CREATE INDEX IF NOT EXISTS ix_ingest_log_source ON raw.ingest_log (source_name, logged_at);
