-- =============================================================================
-- Migration: scan_security_fixes
-- Date     : 2026-05-14
-- Purpose  : Bring an existing scan database in line with the model changes
--            shipped with the security/perf fixes:
--              * scan_jobs   — add composite (organization_id, deleted_at, created_at)
--              * scan_findings — add UNIQUE (scan_job_id, fingerprint)
--
-- Idempotent: each statement first checks information_schema and only runs the
-- DDL if the index/constraint does not already exist. Safe to re-run.
--
-- Usage (replace <db>):
--   mysql -u <user> -p <db> < 2026_05_14_scan_security_fixes.sql
--
-- WARNING — duplicates in scan_findings will block the UNIQUE constraint.
-- The script first reports the duplicate count; if it is > 0 the ALTER will
-- fail with errno 1062. Resolve them with the cleanup query at the bottom of
-- this file before re-running.
-- =============================================================================

-- ── 1. scan_jobs: composite index ───────────────────────────────────────────
SET @ix_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'scan_jobs'
      AND INDEX_NAME   = 'ix_scan_jobs_org_active_created'
);

SET @sql := IF(
    @ix_exists = 0,
    'CREATE INDEX ix_scan_jobs_org_active_created
        ON scan_jobs (organization_id, deleted_at, created_at)',
    'SELECT ''ix_scan_jobs_org_active_created already exists — skipping'' AS note'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ── 1b. scan_jobs: drop now-redundant idx_scan_jobs_org_id ──────────────────
-- The composite index above starts with organization_id, so a standalone
-- index on the same column is dead weight (extra writes, extra disk).
SET @drop_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'scan_jobs'
      AND INDEX_NAME   = 'idx_scan_jobs_org_id'
);

SET @sql := IF(
    @drop_exists = 1,
    'DROP INDEX idx_scan_jobs_org_id ON scan_jobs',
    'SELECT ''idx_scan_jobs_org_id already absent — skipping'' AS note'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ── 2. scan_findings: report duplicates BEFORE attempting the constraint ────
-- A non-zero result here means the ALTER below will fail. Clean up first.
SELECT
    COUNT(*) AS duplicate_groups,
    SUM(c)   AS duplicate_rows
FROM (
    SELECT scan_job_id, fingerprint, COUNT(*) AS c
    FROM scan_findings
    GROUP BY scan_job_id, fingerprint
    HAVING COUNT(*) > 1
) dups;


-- ── 3. scan_findings: UNIQUE (scan_job_id, fingerprint) ─────────────────────
SET @uq_exists := (
    SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA   = DATABASE()
      AND TABLE_NAME     = 'scan_findings'
      AND CONSTRAINT_NAME = 'uq_findings_job_fp'
      AND CONSTRAINT_TYPE = 'UNIQUE'
);

SET @sql := IF(
    @uq_exists = 0,
    'ALTER TABLE scan_findings
        ADD CONSTRAINT uq_findings_job_fp UNIQUE (scan_job_id, fingerprint)',
    'SELECT ''uq_findings_job_fp already exists — skipping'' AS note'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- =============================================================================
-- OPTIONAL — duplicate cleanup (run only if step 2 reported duplicates)
-- =============================================================================
-- Keeps the row with the smallest id per (scan_job_id, fingerprint) and deletes
-- the rest. Review before running on production.
--
-- DELETE f
-- FROM scan_findings f
-- JOIN (
--     SELECT MIN(id) AS keep_id, scan_job_id, fingerprint
--     FROM scan_findings
--     GROUP BY scan_job_id, fingerprint
--     HAVING COUNT(*) > 1
-- ) keepers
--   ON f.scan_job_id = keepers.scan_job_id
--  AND f.fingerprint = keepers.fingerprint
--  AND f.id <> keepers.keep_id;
