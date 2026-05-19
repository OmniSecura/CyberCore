-- ============================================================
-- CyberCore Log Service — MySQL 8.0+
-- All ingested log entries, scoped per organization
-- ============================================================

-- logs: one row per log entry shipped by the cyberlog client.
-- Write-once: rows are never updated or soft-deleted. The log-consumer
-- worker bulk-inserts batches popped from the `cyberlog:queue` Redis list.
CREATE TABLE logs (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),

    -- Owning organization (resolved from the API key on ingest).
    -- No FK — the organization service is the source of truth for orgs.
    org_id          CHAR(36)        NOT NULL,

    -- Free-form project name supplied by the client (e.g. "my-backend").
    project         VARCHAR(120)    NOT NULL,

    -- info | warning | error | debug | critical
    level           VARCHAR(16)     NOT NULL,

    -- Main log message. TEXT so long messages aren't truncated.
    message         TEXT            NOT NULL,

    -- Arbitrary structured fields the user passed as kwargs to log.info(…).
    fields          JSON            NOT NULL DEFAULT (JSON_OBJECT()),

    -- Wall-clock time AT THE CLIENT when the log was emitted.
    timestamp       DATETIME        NOT NULL,

    -- When log-consumer wrote this entry to the database.
    ingested_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    CONSTRAINT chk_logs_level
        CHECK (level IN ('debug', 'info', 'warning', 'error', 'critical'))
);

-- ============================================================
-- Indexes
-- ============================================================

-- Dashboard's most common query: latest events for an org.
CREATE INDEX ix_logs_org_timestamp     ON logs(org_id, timestamp);

-- Filtering by level inside an org (e.g. "show me errors only").
CREATE INDEX ix_logs_org_level_ts      ON logs(org_id, level, timestamp);

-- Filtering by project inside an org.
CREATE INDEX ix_logs_org_project_ts    ON logs(org_id, project, timestamp);
