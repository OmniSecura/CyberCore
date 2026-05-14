-- ============================================================
-- CyberCore Scan Service — MySQL 8.0+
-- ============================================================

-- scan_jobs: one row per submitted scan
-- Scans are always scoped to an organization and a user who triggered them.
-- The celery_task_id links this row to the async worker result in Redis.

CREATE TABLE scan_jobs (
    id                  CHAR(36)        NOT NULL DEFAULT (UUID()),
    organization_id     CHAR(36)        NOT NULL,
    created_by          CHAR(36)        NOT NULL,   -- user_id of whoever submitted the scan

    name                VARCHAR(255)    NOT NULL,
    scan_type           VARCHAR(32)     NOT NULL DEFAULT 'sast',   -- 'sast' | 'dast' (future)

    -- Lifecycle: queued → running → completed | failed | cancelled
    status              VARCHAR(32)     NOT NULL DEFAULT 'queued',

    -- Target: either a public git URL or a path to an uploaded ZIP on the server
    target_type         VARCHAR(32)     NOT NULL,   -- 'git_url' | 'upload'
    target_url          TEXT            NULL,        -- set when target_type = 'git_url'
    target_path         TEXT            NULL,        -- set when target_type = 'upload'

    celery_task_id      VARCHAR(255)    NULL,        -- Celery AsyncResult ID

    started_at          DATETIME        NULL,
    completed_at        DATETIME        NULL,
    error_message       TEXT            NULL,        -- last error from the worker, if any

    -- Denormalised count so the list view doesn't need a JOIN
    findings_count      INT             NOT NULL DEFAULT 0,

    -- Free-form JSON for scan metadata (branch name, commit hash, semgrep config, …)
    extra               JSON            NULL,

    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at          DATETIME        NULL,

    PRIMARY KEY (id),

    -- No FK on organization_id — org validation is handled by the organization service.
    -- No FK on created_by — user validation is handled by the auth service.

    CONSTRAINT chk_scan_jobs_status
        CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),

    CONSTRAINT chk_scan_jobs_type
        CHECK (scan_type IN ('sast', 'dast')),

    CONSTRAINT chk_scan_jobs_target_type
        CHECK (target_type IN ('git_url', 'upload'))
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

-- The org listing query filters on (organization_id, deleted_at) and orders by
-- created_at DESC. The composite index serves both the WHERE and the ORDER BY
-- in a single scan AND covers any query that filters only by organization_id
-- (since organization_id is the leftmost column), so a standalone
-- idx_scan_jobs_org_id is redundant.
CREATE INDEX ix_scan_jobs_org_active_created ON scan_jobs(organization_id, deleted_at, created_at);
CREATE INDEX idx_scan_jobs_created_by        ON scan_jobs(created_by);
CREATE INDEX idx_scan_jobs_status            ON scan_jobs(status);
CREATE INDEX idx_scan_jobs_deleted_at        ON scan_jobs(deleted_at);
CREATE INDEX idx_scan_jobs_created_at        ON scan_jobs(created_at);
