# Auth Service — Database Schema

## Overview

This schema covers everything the auth service owns: user identity, OAuth
providers, organizations (tenants), membership and roles, short-lived tokens
for email flows, and long-lived API keys for programmatic access.

No other service writes to these tables directly. All access goes through
the auth service API.

---

## Tables

### `users`

The central identity record for every person on the platform.

Stores only identity data — who the user is, how they authenticate, and
account-level security state. Organization membership and roles live in
`organization_members`, not here, because a user can belong to multiple
organizations with different roles in each.

**Fields:**

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `CHAR(36)` | NO | `UUID()` | Primary key. A UUID generated at insert time. Used instead of an auto-increment integer to avoid exposing row count and to allow ID generation outside the database. |
| `email` | `VARCHAR(255)` | NO | — | The user's email address. Must be unique across the entire platform. Used as the login identifier for password-based auth and as the delivery address for verification and reset emails. |
| `email_verified` | `TINYINT(1)` | NO | `0` | Whether the user has confirmed ownership of their email address by clicking a verification link. Unverified users may have restricted access depending on application policy. |
| `password_hash` | `VARCHAR(255)` | YES | `NULL` | Bcrypt hash of the user's password. NULL for users who registered exclusively via OAuth and have never set a password. Must never store plaintext. |
| `full_name` | `VARCHAR(255)` | NO | — | The user's display name shown across the UI. Not used for authentication. |
| `avatar_url` | `VARCHAR(500)` | YES | `NULL` | URL to the user's profile picture. Populated automatically when the account is linked via OAuth. Can be updated manually. NULL if no avatar has been set. |
| `is_active` | `TINYINT(1)` | NO | `1` | Whether the account is enabled. Setting this to `0` blocks all logins without deleting the record. Used for manual suspension by a superadmin. |
| `is_superadmin` | `TINYINT(1)` | NO | `0` | Grants access to the internal platform administration panel. Not the same as being an `owner` inside an organization. Should be `1` only for internal CyberCore staff accounts. |
| `mfa_enabled` | `TINYINT(1)` | NO | `0` | Whether the user has completed TOTP setup and MFA is actively enforced on login. |
| `mfa_secret` | `VARCHAR(64)` | YES | `NULL` | The TOTP seed used to validate one-time codes. Encrypted by the application before being written here — the database never holds the plaintext value. NULL until the user completes MFA enrollment. |
| `failed_login_attempts` | `INT` | NO | `0` | Running count of consecutive failed password attempts. Reset to `0` on successful login. Incremented on each failure. Used together with `locked_until` to enforce brute-force lockout. |
| `locked_until` | `DATETIME` | YES | `NULL` | If set, the account is locked and login attempts are rejected until this timestamp passes. Set by the application after `failed_login_attempts` exceeds the configured threshold. NULL means the account is not currently locked. |
| `last_login_at` | `DATETIME` | YES | `NULL` | Timestamp of the most recent successful login. Updated on every successful authentication. NULL if the user has never logged in. |
| `last_login_ip` | `VARCHAR(45)` | YES | `NULL` | IP address of the most recent successful login. Supports both IPv4 and IPv6. Shown in the security activity section of the user's profile. NULL if the user has never logged in. |
| `created_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of when the user record was created. Set once at insert and never changed. |
| `updated_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of the most recent update to any field on this row. Maintained automatically by MySQL via `ON UPDATE CURRENT_TIMESTAMP`. |
| `deleted_at` | `DATETIME` | YES | `NULL` | Soft delete marker. When set, the user is treated as deleted by the application but the row is retained in the database. NULL means the account is not deleted. A scheduled job handles GDPR erasure by anonymizing personal fields on rows where the retention period has elapsed. |

---

### `user_oauth_providers`

Links external OAuth identities to a user record.

A single user account can be connected to multiple providers — for example,
a user who initially signed up with Google can later also link their GitHub
account. Both logins resolve to the same `users` row.

**Fields:**

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `CHAR(36)` | NO | `UUID()` | Primary key. |
| `user_id` | `CHAR(36)` | NO | — | Foreign key to `users.id`. Identifies which user account this OAuth identity belongs to. Cascades on delete — removing a user removes all their linked providers. |
| `provider` | `VARCHAR(50)` | NO | — | Name of the OAuth provider. Expected values: `google`, `github`, `microsoft`. Stored as a lowercase string. |
| `provider_uid` | `VARCHAR(255)` | NO | — | The unique user identifier issued by the external provider (e.g. Google's `sub` claim, GitHub's numeric user ID). Used together with `provider` to look up the local user during an OAuth callback. |
| `access_token` | `TEXT` | YES | `NULL` | The OAuth access token returned by the provider. Only stored if the platform needs to make API calls on behalf of the user (e.g. listing GitHub repositories for a scan). NULL otherwise. |
| `refresh_token` | `TEXT` | YES | `NULL` | The OAuth refresh token, used to obtain a new access token when the current one expires. NULL if the provider does not issue refresh tokens or if token storage is not needed. |
| `token_expires_at` | `DATETIME` | YES | `NULL` | Expiry timestamp of the current access token. The application checks this before using the token and refreshes it if expired. NULL if no access token is stored. |
| `created_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of when this provider was linked to the user account. |

---

### `organizations`

Represents a tenant on the platform.

Every resource in CyberCore (scans, agents, logs, API keys) belongs to an
organization. The `slug` is used in URLs and must be globally unique.

**Fields:**

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `CHAR(36)` | NO | `UUID()` | Primary key. |
| `name` | `VARCHAR(255)` | NO | — | The human-readable display name of the organization, shown in the UI. Does not need to be unique. |
| `slug` | `VARCHAR(100)` | NO | — | A URL-safe identifier for the organization, e.g. `acme-corp`. Used in dashboard URLs and must be globally unique. Validated by the application to contain only lowercase letters, digits, and hyphens. |
| `plan` | `VARCHAR(50)` | NO | `'free'` | The organization's current subscription tier. Controls feature availability and usage limits. Expected values: `free`, `pro`, `enterprise`. Limits are enforced at the application level, not in the database. |
| `is_active` | `TINYINT(1)` | NO | `1` | Whether the organization is enabled. Setting this to `0` blocks access for all members without deleting any data. Used for suspension due to non-payment or policy violation. |
| `created_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of when the organization was created. |
| `updated_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of the most recent update to this row. Maintained automatically via `ON UPDATE CURRENT_TIMESTAMP`. |

---

### `organization_members`

The join table between `users` and `organizations`.

Because a user can belong to many organizations, roles cannot live on the
`users` table. This table assigns each user a role within a specific
organization. The same user can be an `owner` in one organization and a
`viewer` in another.

**Fields:**

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `CHAR(36)` | NO | `UUID()` | Primary key. |
| `organization_id` | `CHAR(36)` | NO | — | Foreign key to `organizations.id`. Identifies which organization this membership belongs to. Cascades on delete. |
| `user_id` | `CHAR(36)` | NO | — | Foreign key to `users.id`. Identifies the member. Cascades on delete. |
| `role` | `VARCHAR(50)` | NO | `'member'` | The user's role within this specific organization. Expected values: `owner` (full control, can delete the org), `admin` (manage members and all resources), `member` (create and manage own resources), `viewer` (read-only). Enforced at the application level. |
| `invited_by` | `CHAR(36)` | YES | `NULL` | Foreign key to `users.id` of the person who sent the invitation. NULL if the user was the organization's founding member (i.e. they created it). Set to NULL on delete of the inviter rather than cascading, to preserve the membership record. |
| `joined_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of when the user accepted their invitation and became an active member. |

---

### `user_tokens`

Short-lived, single-use tokens for transactional email flows.

Used for email address verification, password reset links, and organization
invitations. The plaintext token is generated in memory, sent to the user
once, and immediately discarded. Only the SHA-256 hash is written here.

**Fields:**

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `CHAR(36)` | NO | `UUID()` | Primary key. |
| `user_id` | `CHAR(36)` | NO | — | Foreign key to `users.id`. Identifies which user this token was issued for. Cascades on delete. |
| `token_hash` | `VARCHAR(255)` | NO | — | SHA-256 hash of the plaintext token. The application hashes the token from the incoming request and looks up this column — the plaintext is never stored. Must be unique. |
| `token_type` | `VARCHAR(50)` | NO | — | Classifies the purpose of the token. Expected values: `email_verification`, `password_reset`, `org_invite`. The application validates that the token is being used for the correct flow. |
| `expires_at` | `DATETIME` | NO | — | Timestamp after which the token is no longer valid. Always set at creation. The application rejects any token where this is in the past, even if `used_at` is still NULL. |
| `used_at` | `DATETIME` | YES | `NULL` | Timestamp of when the token was consumed. NULL means the token has not been used yet. Set on successful use rather than deleting the row, so there is an audit trail of completed flows. A cleanup job removes fully expired and used rows periodically. |
| `created_at` | `DATETIME` | NO | `CURRENT_TIMESTAMP` | Timestamp of when the token was issued. |

---

### `api_keys`

Long-lived keys for programmatic access — used by the CyberLog SDK,
CI/CD pipelines, and the agent installer.

The full key is generated once, shown to the user once, and never stored.
Only the prefix and hash are persisted.

**Fields:**

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `CHAR(36)` | NO | `UUID()` | Primary key. |
| `user_id` | `CHAR(36)` | NO | — | Foreign key to `users.id`. The user who created and owns this key. Cascades on delete. |
| `organization_id` | `CHAR(36)` | NO | — | Foreign key to `organizations.id`. The organization this key is scoped to. A key can only access resources within this organization. Cascades on delete. |
| `name` | `VARCHAR(100)` | NO | — | A human-readable label for the key, set by the user at creation time. Shown in the UI to help identify keys, e.g. `CI pipeline key` or `production agent`. |
| `key_prefix` | `VARCHAR(10)` | NO | — | The first 8 characters of the full key, stored in plaintext. Displayed in the UI alongside the `name` so the user can identify which physical key corresponds to which record, without exposing the full secret. |
| `key_hash` | `VARCHAR(255)` | NO | — | SHA-256 hash of the full API key. Used by the auth service to verify incoming keys — the application hashes the presented key and compares it to this column. Must be unique. |
| `scopes` | `JSON` | NO | `[]` | A JSON array of permission