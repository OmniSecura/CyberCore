# Organization Service

Manages organizations, members, invitations, ownership transfers, and **custom roles with fine-grained privileges**.

---

## Privilege System

### How it works

Every user in an organization has a **privilege set** — the set of things they are allowed to do. Privileges are resolved in this order:

```
owner  →  ALL privileges (hardcoded, cannot be restricted)
  │
  └─ member with a custom role  →  that role's explicit privilege list (from DB)
       │
       └─ member with a built-in role  →  DEFAULT_ROLE_PRIVILEGES[role]
```

The single source of truth is `src/privileges.py`.

---

### Adding a new privilege

Open `src/privileges.py` and add **one line** to `PRIVILEGE_REGISTRY`:

```python
PRIVILEGE_REGISTRY = {
    # existing...
    "scans.run": {"label": "Run Scans", "group": "Scans"},  # ← add here
}
```

That's it. The privilege:
- Appears in `GET /organizations/roles/privileges` (used by the frontend role editor)
- Can be assigned to custom roles in the UI
- Can be checked on any endpoint with `require_privilege()`
- No migration needed — privileges are stored as a JSON array in `organization_roles.privileges`

---

### Checking privileges in a service method

Import and call `require_privilege`. It raises `PermissionError` if the user is missing the privilege, which the router catches and returns as HTTP 403.

```python
from ..privileges import require_privilege

class ScanService:
    def start_scan(self, slug: str, actor_id: str, target: str):
        org = _get_active_org(self.db, slug)
        require_privilege(self.db, org, actor_id, "scans.run")

        # ... rest of the logic
```

`require_privilege` signature:

```python
def require_privilege(
    db: Session,
    org: Organization,       # already-fetched org object
    user_id: str,            # the actor (current_user["id"])
    privilege: str,          # key from PRIVILEGE_REGISTRY
) -> None:
    ...  # raises PermissionError if denied
```

---

### Checking privileges in another microservice

Other services do not have direct DB access to `organization_roles`. The ready-made dependency lives in:

```
services/scan-service/src/security/org_privilege.py
```

Copy it to any service (adjust `ORG_SERVICE_URL` env var). It works as a FastAPI dependency factory — pass in the privilege string, and it reads the `{slug}` path parameter automatically from the same route.

**Step 1 — Copy `org_privilege.py` to your service's `src/security/` folder.**

**Step 2 — Use it in a router:**

```python
# services/scan-service/src/routers/v1/scan_router.py
from fastapi import APIRouter, Request
from ...security.org_privilege import require_org_privilege

scan_router = APIRouter(prefix="/organizations/{slug}/scans", tags=["Scans"]) # privilege slug is org slug from path 
                                                                              # {slug} is required for the dependency to work
# Anyone with scans.view can list
@scan_router.get("/", dependencies=[require_org_privilege("scans.view")])
async def list_scans(slug: str, request: Request):
    return {"scans": [], "org": slug}

# Only scans.run can start a scan
@scan_router.post("/", status_code=201, dependencies=[require_org_privilege("scans.run")])
async def start_scan(slug: str, request: Request):
    return {"message": "Scan started", "org": slug}

# Only scans.manage can change config
@scan_router.patch("/config", dependencies=[require_org_privilege("scans.manage")])
async def update_scan_config(slug: str, request: Request):
    return {"message": "Config updated", "org": slug}
```

**Step 3 — Set the env var:**

```env
ORG_SERVICE_URL=http://organization-service:8002
```

That's it. The dependency forwards the user's auth cookie to org-service, gets back the privilege set, and raises 403 if the required privilege is missing. The endpoint body only runs if the check passes.

---

### Built-in role → default privileges mapping

Defined in `DEFAULT_ROLE_PRIVILEGES` in `src/privileges.py`.

| Privilege              | owner | admin | member | viewer |
|------------------------|:-----:|:-----:|:------:|:------:|
| `members.view`         | ✓     | ✓     | ✓      |        |
| `members.invite`       | ✓     | ✓     |        |        |
| `members.remove`       | ✓     | ✓     |        |        |
| `members.manage_roles` | ✓     | ✓     |        |        |
| `roles.view`           | ✓     | ✓     |        |        |
| `roles.manage`         | ✓     |       |        |        |
| `org.view`             | ✓     | ✓     | ✓      | ✓      |
| `org.edit`             | ✓     | ✓     |        |        |
| `agents.view`          | ✓     | ✓     | ✓      |        |
| `agents.manage`        | ✓     | ✓     |        |        |
| `scans.view`           | ✓     | ✓     | ✓      |        |
| `scans.run`            | ✓     | ✓     |        |        |
| `scans.manage`         | ✓     | ✓     |        |        |
| `alerts.view`          | ✓     | ✓     | ✓      |        |
| `alerts.manage`        | ✓     | ✓     |        |        |
| `logs.view`            | ✓     | ✓     | ✓      |        |
| `logs.export`          | ✓     | ✓     |        |        |

Custom roles override this table entirely — a member with a custom role gets exactly the privileges listed in that role, no more, no less.

---

### Structural vs. privilege-gated operations

Not everything goes through `require_privilege`. Some operations are structurally restricted by role and are **not overridable** by custom roles:

| Operation | Guard | Reason |
|-----------|-------|--------|
| Delete organization | owner only | Structural; cannot be delegated |
| Edit organization settings | owner only | Structural |
| Transfer ownership | owner only | Structural |
| Manage custom roles | owner only | Roles define what others can do |
| Reactivate organization | owner only | Structural |

These use explicit `if org.owner_id != actor_id: raise PermissionError(...)` checks in `organization_service.py` and `role_service.py`.

---

## API Routes

### Roles & Privileges

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/v1/organizations/roles/privileges` | None | All privileges grouped by category |
| `GET` | `/v1/organizations/roles/{slug}/my-privileges` | User | Current user's privilege set in this org |
| `GET` | `/v1/organizations/roles/{slug}` | Member | List custom roles |
| `POST` | `/v1/organizations/roles/{slug}` | Owner | Create custom role |
| `PATCH` | `/v1/organizations/roles/{slug}/{role_id}` | Owner | Update custom role |
| `DELETE` | `/v1/organizations/roles/{slug}/{role_id}` | Owner | Delete custom role |

### Members

| Method | Path | Required privilege | Description |
|--------|------|--------------------|-------------|
| `GET` | `/v1/organizations/members/{slug}/members` | `members.view` | List members |
| `PATCH` | `/v1/organizations/members/{slug}/members/{user_id}` | `members.manage_roles` | Change member role |
| `DELETE` | `/v1/organizations/members/{slug}/members/{user_id}` | `members.remove` (or self) | Remove member |
| `GET` | `/v1/organizations/members/{slug}/invites` | `members.invite` | List pending invites |
| `POST` | `/v1/organizations/members/{slug}/invites` | `members.invite` | Send invite |
| `DELETE` | `/v1/organizations/members/{slug}/invites/{id}` | `members.invite` | Revoke invite |

---

## Database

Run in this order:

```sql
-- 1. Base tables
source database/sql/tables/organizations/organization.sql

-- 2. Custom roles + ALTER for organization_users
source database/sql/tables/organizations/organization_roles.sql
```

The `organization_roles` table stores privileges as a `JSON` column (array of strings). Adding a new privilege key requires no schema change — just add it to `PRIVILEGE_REGISTRY` in `privileges.py`.
