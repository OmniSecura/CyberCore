-- ============================================================
-- CyberCore Scan Service — MySQL 8.0+
-- ============================================================

CREATE TABLE scan_findings (
    id              CHAR(36)            NOT NULL DEFAULT (UUID()),
    scan_job_id     CHAR(36)            NOT NULL,

    tool            VARCHAR(32)         NOT NULL,
    rule_id         VARCHAR(256)        NOT NULL,

    severity        VARCHAR(16)         NOT NULL,
    confidence      VARCHAR(16)         NULL,

    title           VARCHAR(1024)       NOT NULL,
    message         MEDIUMTEXT          NOT NULL,

    file_path       VARCHAR(2048)       NOT NULL,
    line_start      INT                 NULL,
    line_end        INT                 NULL,
    code_snippet    MEDIUMTEXT          NULL,

    cwe             VARCHAR(256)        NULL,
    owasp           VARCHAR(128)        NULL,

    fingerprint     CHAR(64)            NOT NULL,

    created_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    CONSTRAINT fk_scan_findings_job
        FOREIGN KEY (scan_job_id) REFERENCES scan_jobs(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_scan_findings_severity
        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),

    CONSTRAINT chk_scan_findings_tool
        CHECK (tool IN ('bandit', 'semgrep', 'gitleaks', 'trivy', 'hadolint', 'pip-audit', 'npm-audit', 'gosec')),

    -- Per-job dedup is enforced at the DB level. Two concurrent worker tasks
    -- (or a Celery retry) cannot insert duplicate findings for the same scan
    -- even if the in-memory dedup is bypassed.
    CONSTRAINT uq_findings_job_fp
        UNIQUE (scan_job_id, fingerprint)
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX idx_scan_findings_job_id      ON scan_findings(scan_job_id);
CREATE INDEX idx_scan_findings_severity    ON scan_findings(scan_job_id, severity);
CREATE INDEX idx_scan_findings_tool        ON scan_findings(scan_job_id, tool);
CREATE INDEX idx_scan_findings_fingerprint ON scan_findings(fingerprint);
