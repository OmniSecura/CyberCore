"""
Privilege registry — the single source of truth for all available privileges.

To add a new privilege (e.g. for scans):
    1. Add one entry to PRIVILEGE_REGISTRY below.
    2. That's it — the API, frontend, and DB all pick it up automatically.

Format:
    "category.action": {"label": "Human-readable name", "group": "UI group header"}
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from .database.models.Organization import Organization

PRIVILEGE_REGISTRY: dict[str, dict[str, str]] = {

    # ── Members ───────────────────────────────────────────────────────────────
    "members.view":         {"label": "View Members",         "group": "Members"},
    "members.invite":       {"label": "Invite Members",       "group": "Members"},
    "members.remove":       {"label": "Remove Members",       "group": "Members"},
    "members.manage_roles": {"label": "Manage Member Roles",  "group": "Members"},

    # ── Roles ─────────────────────────────────────────────────────────────────
    "roles.view":   {"label": "View Custom Roles",   "group": "Roles"},
    "roles.manage": {"label": "Manage Custom Roles", "group": "Roles"},

    # ── Organization ─────────────────────────────────────────────────────────
    "org.view":     {"label": "View Organization Details",  "group": "Organization"},
    "org.edit":     {"label": "Edit Organization Settings", "group": "Organization"},

    # ── Agents ────────────────────────────────────────────────────────────────
    "agents.view":   {"label": "View Agents",   "group": "Agents"},
    "agents.manage": {"label": "Manage Agents", "group": "Agents"},

    # ── Scans ─────────────────────────────────────────────────────────────────
    "scans.view":   {"label": "View Scans",                "group": "Scans"},
    "scans.run":    {"label": "Run Scans",                 "group": "Scans"},
    "scans.manage": {"label": "Manage Scan Configurations", "group": "Scans"},

    # ── Alerts ────────────────────────────────────────────────────────────────
    "alerts.view":   {"label": "View Alerts",        "group": "Alerts"},
    "alerts.manage": {"label": "Manage Alert Rules", "group": "Alerts"},

    # ── Logs ──────────────────────────────────────────────────────────────────
    "logs.view":   {"label": "View Logs",   "group": "Logs"},
    "logs.export": {"label": "Export Logs", "group": "Logs"},

}

ALL_PRIVILEGES: set[str] = set(PRIVILEGE_REGISTRY.keys())

# ── Default privilege sets for built-in roles ─────────────────────────────────
# To change what a built-in role can do, edit this dict.
# Custom roles bypass this entirely — they carry their own explicit privilege list.

DEFAULT_ROLE_PRIVILEGES: dict[str, set[str]] = {
    "owner": ALL_PRIVILEGES,
    "admin": {
        "members.view",
        "members.invite",
        "members.remove",
        "members.manage_roles",
        "roles.view",
        "org.view",
        "org.edit",
        "agents.view",
        "agents.manage",
        "scans.view",
        "scans.run",
        "scans.manage",
        "alerts.view",
        "alerts.manage",
        "logs.view",
        "logs.export",
    },
    "member": {
        "members.view",
        "org.view",
        "agents.view",
        "scans.view",
        "alerts.view",
        "logs.view",
    },
    "viewer": {
        "org.view",
    },
}


def is_valid_privilege(key: str) -> bool:
    return key in ALL_PRIVILEGES


def get_registry_for_api() -> list[dict]:
    """Returns the registry grouped by category for the frontend."""
    groups: dict[str, list[dict]] = {}
    for key, meta in PRIVILEGE_REGISTRY.items():
        g = meta["group"]
        groups.setdefault(g, [])
        groups[g].append({"key": key, "label": meta["label"]})
    return [{"group": g, "privileges": privs} for g, privs in groups.items()]


def get_user_privileges(db: "Session", org: "Organization", user_id: str) -> set[str]:
    """
    Returns the full set of privileges this user has in the given org.

    Resolution order:
      1. Owner → ALL privileges
      2. Member with a custom role → that role's explicit privilege list
      3. Member with a built-in role → DEFAULT_ROLE_PRIVILEGES[role]
      4. Not a member → empty set
    """
    # Lazy import to avoid circular dependencies at module load time
    from .database.models.OrganizationUsers import OrganizationUser
    from .database.models.OrganizationRole import OrganizationRole

    if org.owner_id == user_id:
        return ALL_PRIVILEGES

    member = (
        db.query(OrganizationUser)
        .filter(
            OrganizationUser.organization_id == org.id,
            OrganizationUser.user_id == user_id,
        )
        .first()
    )
    if not member:
        return set()

    if member.custom_role_id:
        custom_role = (
            db.query(OrganizationRole)
            .filter(OrganizationRole.id == member.custom_role_id)
            .first()
        )
        if custom_role:
            return set(custom_role.privileges or [])

    return DEFAULT_ROLE_PRIVILEGES.get(member.role, set())


def require_privilege(db: "Session", org: "Organization", user_id: str, privilege: str) -> None:
    """Raises PermissionError if the user does not have the required privilege."""
    privs = get_user_privileges(db, org, user_id)
    if privilege not in privs:
        raise PermissionError(f"Missing privilege: {privilege}")
