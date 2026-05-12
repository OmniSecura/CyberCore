"""
Privilege registry — the single source of truth for all available privileges.

To add a new privilege (e.g. for scans):
    1. Add one entry to PRIVILEGE_REGISTRY below.
    2. That's it — the API, frontend, and DB all pick it up automatically.

Format:
    "category.action": {"label": "Human-readable name", "group": "UI group header"}
"""

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
    "org.view":     {"label": "View Organization Details", "group": "Organization"},
    "org.edit":     {"label": "Edit Organization Settings", "group": "Organization"},

    # ── Agents ────────────────────────────────────────────────────────────────
    "agents.view":   {"label": "View Agents",   "group": "Agents"},
    "agents.manage": {"label": "Manage Agents", "group": "Agents"},

    # ── Scans ─────────────────────────────────────────────────────────────────
    "scans.view":   {"label": "View Scans",               "group": "Scans"},
    "scans.run":    {"label": "Run Scans",                "group": "Scans"},
    "scans.manage": {"label": "Manage Scan Configurations", "group": "Scans"},

    # ── Alerts ────────────────────────────────────────────────────────────────
    "alerts.view":   {"label": "View Alerts",        "group": "Alerts"},
    "alerts.manage": {"label": "Manage Alert Rules", "group": "Alerts"},

    # ── Logs ──────────────────────────────────────────────────────────────────
    "logs.view":   {"label": "View Logs",   "group": "Logs"},
    "logs.export": {"label": "Export Logs", "group": "Logs"},

}

ALL_PRIVILEGES = set(PRIVILEGE_REGISTRY.keys())


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
