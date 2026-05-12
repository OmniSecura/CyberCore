-- ============================================================
-- CyberCore Scan Service — MySQL 8.0+
-- ============================================================

-- scan_findings: individual vulnerabilities reported by a scan tool
-- Each row belongs to exactly one scan_job.
-- The fingerprint column is a SHA-256 hash of (rule_id + file + line + message)
-- and is used to deduplicate identical findings across re-scans.
CREATE TABLE scan_findings (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    scan_job_id     CHAR(36)        NOT NULL,

    -- Which tool produced this finding: 'bandit' | 'semgrep'
    tool            VARCHAR(32)     NOT NULL,

    -- Tool-native rule identifier, e.g. 'B301' (Bandit) or 'python.lang.security.audit.pickle' (Semgrep)
    rule_id         VARCHAR(128)    NOT NULL,

    -- Normalised severity: critical | high | medium | low | info
    severity        VARCHAR(16)     NOT NULL,

    -- Normalised confidence (Bandit only): high | medium | low
    confidence      VARCHAR(16)     NULL,

    title           VARCHAR(512)    NOT NULL,
    message         TEXT            NOT NULL,

    -- Path relative to the scanned root, e.g. 'src/auth/login.py'
    file_path       TEXT            NOT NULL,
    line_start      INT             NULL,
    line_end        INT             NULL,
    code_snippet    TEXT            NULL,

    -- Taxonomy
    cwe             VARCHAR(256)    NULL,   -- e.g. 'CWE-79: ...' (semgrep returns full description)
    owasp           VARCHAR(64)     NULL,   -- e.g. 'A03:2021'

    -- SHA-256(rule_id:file_path:line_start:message), first 64 hex chars
    fingerprint     CHAR(64)        NOT NULL,

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    CONSTRAINT fk_scan_findings_job
        FOREIGN KEY (scan_job_id) REFERENCES scan_jobs(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_scan_findings_severity
        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),

    CONSTRAINT chk_scan_findings_tool
        CHECK (tool IN ('bandit', 'semgrep'))
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

-- Primary access pattern: all findings for a job
CREATE INDEX idx_scan_findings_job_id      ON scan_findings(scan_job_id);

-- Filtered views (by severity or tool within a job)
CREATE INDEX idx_scan_findings_severity    ON scan_findings(scan_job_id, severity);
CREATE INDEX idx_scan_findings_tool        ON scan_findings(scan_job_id, tool);

-- Deduplication lookups
CREATE INDEX idx_scan_findings_fingerprint ON scan_findings(fingerprint);
