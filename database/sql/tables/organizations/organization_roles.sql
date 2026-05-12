-- ============================================================
-- CyberCore — Custom Roles & Privileges
-- Run AFTER organization.sql (depends on organization table)
-- ============================================================

-- ── Custom roles per organization ────────────────────────────────────────────

CREATE TABLE organization_roles (
    id              CHAR(36)     NOT NULL DEFAULT (UUID()),
    organization_id CHAR(36)     NOT NULL,

    -- Role display name (unique within the org)
    name            VARCHAR(100) NOT NULL,
    description     VARCHAR(500) NULL,

    -- Hex colour for UI badge, e.g. #3B82F6
    color           VARCHAR(7)   NULL,

    -- JSON array of privilege keys, e.g. '["members.view","scans.run"]'
    -- To add a new privilege: add it to privileges.py — no schema change needed.
    privileges      JSON         NOT NULL DEFAULT ('[]'),

    -- Who created this role
    created_by      CHAR(36)     NULL,

    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_org_role_name (organization_id, name),

    CONSTRAINT fk_org_role_org
        FOREIGN KEY (organization_id) REFERENCES organization(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_org_role_creator
        FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE SET NULL
);

-- ── Link custom role to members ───────────────────────────────────────────────
-- When a custom role is deleted the column is set to NULL (member reverts to
-- their built-in `role` value).

ALTER TABLE organization_users
    ADD COLUMN custom_role_id CHAR(36) NULL
        REFERENCES organization_roles(id)
        ON DELETE SET NULL;

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX idx_org_roles_org_id         ON organization_roles(organization_id);
CREATE INDEX idx_org_users_custom_role_id ON organization_users(custom_role_id);
