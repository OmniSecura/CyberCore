-- ============================================================
-- CyberCore Organization Service — MySQL 8.0+
-- ============================================================

CREATE TABLE organization (
    id                       CHAR(36)      NOT NULL DEFAULT (UUID()),
    owner_id                 CHAR(36)      NOT NULL,  -- no DEFAULT — must be set explicitly

    organization_name        VARCHAR(255)  NOT NULL,
    organization_slug        VARCHAR(100)  NOT NULL,
    organization_description VARCHAR(500)  NULL,      -- fixed typo: organizations_ → organization_

    plan                     VARCHAR(50)   NOT NULL DEFAULT 'free',
    is_active                TINYINT(1)    NOT NULL DEFAULT 1,

    created_at               DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at               DATETIME      NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uq_organization_slug (organization_slug),

    CONSTRAINT fk_organization_owner
        FOREIGN KEY (owner_id) REFERENCES users(id)
        ON DELETE CASCADE
);

-- ── Organization members ──────────────────────────────────────────────────────

CREATE TABLE organization_users (
    id              CHAR(36)     NOT NULL DEFAULT (UUID()),
    organization_id CHAR(36)     NOT NULL,
    user_id         CHAR(36)     NOT NULL,

    -- 'admin' | 'member' | 'viewer'
    -- owner is stored in organization.owner_id, not here
    role            VARCHAR(50)  NOT NULL DEFAULT 'member',

    -- user_id of the person who sent the invite, NULL if founding member
    invited_by      CHAR(36)     NULL,

    joined_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_org_user (organization_id, user_id),

    CONSTRAINT fk_org_users_org
        FOREIGN KEY (organization_id) REFERENCES organization(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_org_users_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

-- ── Pending email invitations ─────────────────────────────────────────────────
-- Mirrors the user_tokens pattern from auth-service:
-- plaintext token is sent once by email, only the SHA-256 hash is stored here.

CREATE TABLE organization_invites (
    id              CHAR(36)     NOT NULL DEFAULT (UUID()),
    organization_id CHAR(36)     NOT NULL,

    -- Email the invite was sent to — may not yet have a user account
    invited_email   VARCHAR(255) NOT NULL,

    -- Role that will be assigned when the invite is accepted
    role            VARCHAR(50)  NOT NULL DEFAULT 'member',

    -- user_id of the person who created this invite
    invited_by      CHAR(36)     NOT NULL,

    -- SHA-256 of the plaintext token embedded in the invite link
    token_hash      VARCHAR(255) NOT NULL,

    expires_at      DATETIME     NOT NULL,
    used_at         DATETIME     NULL,  -- NULL = not yet accepted

    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_invite_token (token_hash),

    CONSTRAINT fk_invite_org
        FOREIGN KEY (organization_id) REFERENCES organization(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_invite_invited_by
        FOREIGN KEY (invited_by) REFERENCES users(id)
        ON DELETE CASCADE
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX idx_organization_owner      ON organization(owner_id);
CREATE INDEX idx_organization_deleted_at ON organization(deleted_at);

CREATE INDEX idx_org_users_org_id        ON organization_users(organization_id);
CREATE INDEX idx_org_users_user_id       ON organization_users(user_id);

CREATE INDEX idx_org_invites_org_id      ON organization_invites(organization_id);
CREATE INDEX idx_org_invites_email       ON organization_invites(invited_email);
CREATE INDEX idx_org_invites_expires_at  ON organization_invites(expires_at);
