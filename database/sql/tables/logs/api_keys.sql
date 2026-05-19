-- ============================================================
-- CyberCore Log Service — MySQL 8.0+
-- Per-organization API keys used by the `cyberlog` Python client
-- ============================================================

-- api_keys: one row per generated key (an org may have many)
-- The plaintext key is shown to the user ONCE on creation; only the SHA-256
-- hash is persisted. `key_prefix` is kept separately so the dashboard can
-- display "ccl_abc123…" without exposing the full secret.
CREATE TABLE api_keys (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),

    -- Owning organization. Logs ingested with this key are tagged with
    -- this org_id so the dashboard can scope queries by organization.
    -- No FK — org validation is handled by the organization service.
    org_id          CHAR(36)        NOT NULL,

    -- Free-form label shown in the dashboard ("production", "staging", …).
    name            VARCHAR(120)    NOT NULL,

    -- SHA-256 hex digest of the plaintext (64 chars). Unique so we can look
    -- a key up in O(1) at ingest time.
    key_hash        CHAR(64)        NOT NULL,

    -- First 12 chars of the plaintext (e.g. "ccl_abc123de"). Safe to display
    -- in the UI so the owner can recognise which key is which.
    key_prefix      VARCHAR(16)     NOT NULL,

    -- Soft-disable without deleting. The cache layer respects this flag.
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,

    -- Optional usage stats.
    last_used_at    DATETIME        NULL,

    -- When the key stops being valid. NULL = never expires. Auth dependency
    -- rejects keys past this timestamp.
    expires_at      DATETIME        NULL,

    -- Audit
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_api_keys_hash (key_hash)
);

-- ============================================================
-- Indexes
-- ============================================================

-- Owner-side listing: "show all active keys for this org".
CREATE INDEX ix_api_keys_org_active   ON api_keys(org_id, is_active);

-- Background cleanup / "expiring soon" notifications.
CREATE INDEX ix_api_keys_expires_at   ON api_keys(expires_at);
