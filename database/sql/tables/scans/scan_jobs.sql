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

    CONSTRAINT fk_scan_jobs_org
        FOREIGN KEY (organization_id) REFERENCES organization(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_scan_jobs_user
        FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_scan_jobs_status
        CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),

    CONSTRAINT chk_scan_jobs_type
        CHECK (scan_type IN ('sast', 'dast')),

    CONSTRAINT chk_scan_jobs_target_type
        CHECK (target_type IN ('git_url', 'upload'))
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX idx_scan_jobs_org_id       ON scan_jobs(organization_id);
CREATE INDEX idx_scan_jobs_created_by   ON scan_jobs(created_by);
CREATE INDEX idx_scan_jobs_status       ON scan_jobs(status);
CREATE INDEX idx_scan_jobs_deleted_at   ON scan_jobs(deleted_at);
CREATE INDEX idx_scan_jobs_created_at   ON scan_jobs(created_at);
