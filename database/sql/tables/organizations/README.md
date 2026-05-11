# Organization Service — Database Schema

## Overview

This schema covers everything the organization service owns: organization
identity and settings, membership with roles, and pending email invitations.

No other service writes to these tables directly. All access goes through
the organization service API.

---

## Tables

### `organization`

The core record for every organization on the platform.

Every resource in CyberCore (scans, agents, logs, API keys) is scoped to an
organization. The owner is stored directly on this table — they always retain
access regardless of their row in `organization_users`.

**Fields:**

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `CHAR(36)` | NO | `UUID()` | Primary key. A UUID generated at insert time. Used instead of an auto-increment integer to avoid exposing row count and to allow ID generation outside the database. |
| `owner_id` | `CHAR(36)` | NO | — | Foreign key to `users.id`. The user who created the organization. Always has full access regardless of their row in `organization_users`. Cascades on delete — if the owner's account is deleted, the organization is also deleted. Must be set explicitly at creation time, never generated automatically. |
| `organization_name` | `VARCHAR(255)` | NO | — | The human-readable display name of the organization, shown across the UI. Does not need to be globally unique — two organizations can have the same name. |
| `organization_slug` | `VARCHAR(100)` | NO | — | A URL-safe identifier for the organization, e.g. `acme-corp`. Used in dashboard URLs and API paths. Must be globally unique. Validated by the application to contain only lowercase letters, digits, and hyphens, and must not start or end with a hyphen. |
| `organization_description` | `VARCHAR(500)` | YES | `NULL` | An optional free-text description of the organization. NULL if not provided. |
| `plan` | `VARCHAR(50)` | NO | `'free'` | The organization's current subscription tier. Controls feature availability and usage limits. Expected values: `free`, `pro`, `enterprise`. Limits are enforced at the application level, not in the database. |
| `is_active` | `TINYINT(1)` | NO | `1` | Whether the organization is enabled. Setting this to `0` blocks access for all members without deleting any data. Used for suspension due to non-payment or policy violation. |
| `created_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of when the organization was created. Set once at insert and never changed. |
| `updated_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of the most recent update to any field on this row. Maintained automatically by MySQL via `ON UPDATE CURRENT_TIMESTAMP`. |
| `deleted_at` | `DATETIME` | YES | `NULL` | Soft delete marker. When set, the organization is treated as deleted by the application but the row is retained in the database. NULL means the organization is not deleted. Only the owner can soft-delete an organization. |

---

### `organization_users`

The membership table between users and organizations.

A user can belong to multiple organizations with a different role in each.
The owner is stored separately in `organization.owner_id` — they are not
required to have a row here, but one is inserted automatically at creation
time so they appear in membership listings.

**Fields:**

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `CHAR(36)` | NO | `UUID()` | Primary key. |
| `organization_id` | `CHAR(36)` | NO | — | Foreign key to `organization.id`. Identifies which organization this membership belongs to. Cascades on delete — removing the organization removes all memberships. |
| `user_id` | `CHAR(36)` | NO | — | Foreign key to `users.id`. Identifies the member. Cascades on delete — removing a user removes all their memberships. |
| `role` | `VARCHAR(50)` | NO | `'member'` | The user's role within this specific organization. Expected values: `admin` (manage members and org settings), `member` (create and manage own resources), `viewer` (read-only). The owner role is not stored here — it is derived from `organization.owner_id`. Enforced at the application level. |
| `invited_by` | `CHAR(36)` | YES | `NULL` | The `user_id` of the person who sent the invitation that led to this membership. NULL if the user is the organization's founding member (i.e. the owner at creation time). Not a foreign key — preserved even if the inviter's account is later deleted. |
| `joined_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of when the user accepted their invitation and became an active member. Set once at insert and never updated. |
| `created_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of when this membership row was created. |
| `updated_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of the most recent update, e.g. when the role was changed. Maintained automatically via `ON UPDATE CURRENT_TIMESTAMP`. |

---

### `organization_invites`

Pending email invitations to join an organization.

Mirrors the `user_tokens` pattern from the auth service: the plaintext token
is generated in memory, embedded in the invite link sent by email, and
immediately discarded. Only the SHA-256 hash is stored here.

The invited email address may not yet have a user account. If the invitee
does not have an account, they must register first and then accept the invite.

**Flow:**
1. Admin or owner calls `POST /organizations/{id}/invites`
2. A record is created here with `token_hash`, `role`, and `expires_at`
3. An email is sent with the plaintext token embedded in the invite link
4. The invitee clicks the link → `POST /organizations/invites/accept`
5. The application hashes the token, looks it up here, validates it, and creates an `organization_users` row
6. `used_at` is set on this record — the invite cannot be reused

**Fields:**

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `CHAR(36)` | NO | `UUID()` | Primary key. |
| `organization_id` | `CHAR(36)` | NO | — | Foreign key to `organization.id`. Identifies which organization this invite grants access to. Cascades on delete — removing the organization removes all pending invites. |
| `invited_email` | `VARCHAR(255)` | NO | — | The email address the invitation was sent to. May not correspond to an existing user account at the time the invite is created. Used to match the invite when the invitee registers and accepts. |
| `role` | `VARCHAR(50)` | NO | `'member'` | The role that will be assigned to the user when this invite is accepted. Expected values: `admin`, `member`, `viewer`. An admin cannot invite someone to a role equal to or higher than their own. |
| `invited_by` | `CHAR(36)` | NO | — | Foreign key to `users.id`. The user who created this invitation. Cascades on delete. |
| `token_hash` | `VARCHAR(255)` | NO | — | SHA-256 hash of the plaintext token sent in the invite email. The application hashes the token from the incoming request and looks up this column to find the invite — the plaintext is never stored. Must be unique. |
| `expires_at` | `DATETIME` | NO | — | Timestamp after which the invite link is no longer valid. Always set at creation. Default TTL is 48 hours. The application rejects any invite where this is in the past, even if `used_at` is still NULL. |
| `used_at` | `DATETIME` | YES | `NULL` | Timestamp of when the invite was accepted. NULL means the invite has not been used yet. Set on acceptance rather than deleting the row, so there is an audit trail of who joined and when. |
| `created_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of when the invite was created. |
| `updated_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of the most recent update to this row. |

---

## Role hierarchy

Roles are enforced at the application level, not in the database.

| Role | Can do |
|------|--------|
| `owner` | Everything. Delete org, transfer ownership, manage all members. Derived from `organization.owner_id` — not stored in `organization_users`. |
| `admin` | Invite and remove members, change roles (only roles below their own), edit org name and description. Cannot touch the owner or other admins. |
| `member` | View the org and use its resources. Cannot manage members or settings. |
| `viewer` | Read-only access. Cannot modify anything. |

Key rule: a user can only assign roles strictly below their own. An admin
cannot promote anyone to admin or owner.
