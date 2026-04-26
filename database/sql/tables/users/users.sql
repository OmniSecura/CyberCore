-- ============================================================
-- CyberCore Auth Service — MySQL 8.0+
-- ============================================================

-- Users: core identity table
-- Stores only identity data, no org/role context
CREATE TABLE users (
    id                      CHAR(36)        NOT NULL DEFAULT (UUID()),
    email                   VARCHAR(255)    NOT NULL,
    email_verified          TINYINT(1)      NOT NULL DEFAULT 0,

    -- NULL if user registered via OAuth only
    password_hash           VARCHAR(255)    NULL,

    full_name               VARCHAR(255)    NOT NULL,
    avatar_url              VARCHAR(500)    NULL,

    -- Account status
    is_active               TINYINT(1)      NOT NULL DEFAULT 1,
    is_superadmin           TINYINT(1)      NOT NULL DEFAULT 0,

    -- MFA (TOTP seed stored encrypted at application level)
    mfa_enabled             TINYINT(1)      NOT NULL DEFAULT 0,
    mfa_secret              VARCHAR(64)     NULL,

    -- Brute-force lockout
    failed_login_attempts   INT             NOT NULL DEFAULT 0,
    locked_until            DATETIME        NULL,

    -- Session metadata
    last_login_at           DATETIME        NULL,
    last_login_ip           VARCHAR(45)     NULL,

    -- Audit
    created_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at              DATETIME        NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email)
);

-- user_oauth_providers: linked OAuth accounts per user
-- One user can have multiple providers (Google + GitHub)
CREATE TABLE user_oauth_providers (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    user_id         CHAR(36)        NOT NULL,

    provider        VARCHAR(50)     NOT NULL,   -- 'google' | 'github' | 'microsoft'
    provider_uid    VARCHAR(255)    NOT NULL,   -- ID issued by the external provider
    access_token    TEXT            NULL,
    refresh_token   TEXT            NULL,
    token_expires_at DATETIME       NULL,

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_oauth_provider_uid (provider, provider_uid),
    CONSTRAINT fk_oauth_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

-- organizations: tenants on the platform
-- Each organization has its own plan and isolated data
CREATE TABLE organizations (
    id          CHAR(36)        NOT NULL DEFAULT (UUID()),
    name        VARCHAR(255)    NOT NULL,
    slug        VARCHAR(100)    NOT NULL,   -- used in URLs, e.g. "acme-corp"
    plan        VARCHAR(50)     NOT NULL DEFAULT 'free',  -- 'free' | 'pro' | 'enterprise'

    is_active   TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_organizations_slug (slug)
);

-- organization_members: user <-> org relationship with role
-- A user can belong to multiple organizations with different roles
CREATE TABLE organization_members (
    id                  CHAR(36)        NOT NULL DEFAULT (UUID()),
    organization_id     CHAR(36)        NOT NULL,
    user_id             CHAR(36)        NOT NULL,

    -- 'owner' | 'admin' | 'member' | 'viewer'
    role                VARCHAR(50)     NOT NULL DEFAULT 'member',

    invited_by          CHAR(36)        NULL,   -- user_id of the inviter
    joined_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    -- A user can only appear once per organization
    UNIQUE KEY uq_members_org_user (organization_id, user_id),
    CONSTRAINT fk_members_org
        FOREIGN KEY (organization_id) REFERENCES organizations(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_members_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_members_invited_by
        FOREIGN KEY (invited_by) REFERENCES users(id)
        ON DELETE SET NULL
);

-- user_tokens: short-lived tokens for email flows and invites
-- Only the hash is stored — plaintext is sent to the user once and discarded
CREATE TABLE user_tokens (
    id          CHAR(36)        NOT NULL DEFAULT (UUID()),
    user_id     CHAR(36)        NOT NULL,

    token_hash  VARCHAR(255)    NOT NULL,
    -- 'email_verification' | 'password_reset' | 'org_invite'
    token_type  VARCHAR(50)     NOT NULL,

    expires_at  DATETIME        NOT NULL,
    used_at     DATETIME        NULL,   -- NULL means token has not been used yet

    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_tokens_hash (token_hash),
    CONSTRAINT fk_tokens_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

-- api_keys: long-lived keys for SDK and CI/CD integrations
-- Full key is shown to the user once on creation, only the hash is persisted
CREATE TABLE api_keys (
    id                  CHAR(36)        NOT NULL DEFAULT (UUID()),
    user_id             CHAR(36)        NOT NULL,
    organization_id     CHAR(36)        NOT NULL,

    name                VARCHAR(100)    NOT NULL,   -- e.g. "CI pipeline key"
    key_prefix          VARCHAR(10)     NOT NULL,   -- first 8 chars, shown in UI for identification
    key_hash            VARCHAR(255)    NOT NULL,   -- SHA-256 of the full key

    -- JSON array of permission scopes
    -- e.g. ["scan:read", "scan:write", "logs:write"]
    scopes              JSON            NOT NULL DEFAULT (JSON_ARRAY()),

    last_used_at        DATETIME        NULL,
    last_used_ip        VARCHAR(45)     NULL,
    expires_at          DATETIME        NULL,       -- NULL means key never expires
    revoked_at          DATETIME        NULL,       -- NULL means key is active

    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_api_keys_hash (key_hash),
    CONSTRAINT fk_api_keys_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_api_keys_org
        FOREIGN KEY (organization_id) REFERENCES organizations(id)
        ON DELETE CASCADE
);

-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX idx_users_deleted_at           ON users(deleted_at);
CREATE INDEX idx_oauth_user_id              ON user_oauth_providers(user_id);
CREATE INDEX idx_members_org_id             ON organization_members(organization_id);
CREATE INDEX idx_members_user_id            ON organization_members(user_id);
CREATE INDEX idx_tokens_user_id             ON user_tokens(user_id);
CREATE INDEX idx_tokens_expires_at          ON user_tokens(expires_at);
CREATE INDEX idx_api_keys_user_id           ON api_keys(user_id);
CREATE INDEX idx_api_keys_org_id            ON api_keys(organization_id);