from sqlalchemy.orm import Session

from ..database.models.Organization import Organization
from ..database.models.OrganizationRole import OrganizationRole
from ..database.models.OrganizationUsers import OrganizationUser


def _get_active_org(db: Session, slug: str) -> Organization:
    org = (
        db.query(Organization)
        .filter(Organization.organization_slug == slug, Organization.deleted_at.is_(None))
        .first()
    )
    if not org:
        raise LookupError("Organization not found")
    return org


def _require_owner(org: Organization, user_id: str) -> None:
    if org.owner_id != user_id:
        raise PermissionError("Only the organization owner can manage custom roles")


class RoleService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_roles(self, slug: str, actor_id: str) -> list[OrganizationRole]:
        org = _get_active_org(self.db, slug)
        # Any member can view roles (so they know what they can be assigned)
        member = (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == org.id,
                OrganizationUser.user_id == actor_id,
            )
            .first()
        )
        if org.owner_id != actor_id and not member:
            raise PermissionError("You are not a member of this organization")

        return (
            self.db.query(OrganizationRole)
            .filter(OrganizationRole.organization_id == org.id)
            .all()
        )

    def get_role(self, slug: str, role_id: str, actor_id: str) -> OrganizationRole:
        org = _get_active_org(self.db, slug)
        member = (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == org.id,
                OrganizationUser.user_id == actor_id,
            )
            .first()
        )
        if org.owner_id != actor_id and not member:
            raise PermissionError("You are not a member of this organization")

        role = (
            self.db.query(OrganizationRole)
            .filter(
                OrganizationRole.id == role_id,
                OrganizationRole.organization_id == org.id,
            )
            .first()
        )
        if not role:
            raise LookupError("Role not found")
        return role

    def create_role(
        self,
        slug: str,
        actor_id: str,
        name: str,
        description: str | None,
        color: str | None,
        privileges: list[str],
    ) -> OrganizationRole:
        org = _get_active_org(self.db, slug)
        _require_owner(org, actor_id)

        existing = (
            self.db.query(OrganizationRole)
            .filter(
                OrganizationRole.organization_id == org.id,
                OrganizationRole.name == name,
            )
            .first()
        )
        if existing:
            raise ValueError(f"A role named '{name}' already exists in this organization")

        role = OrganizationRole(
            organization_id=org.id,
            name=name,
            description=description,
            color=color,
            privileges=privileges,
            created_by=actor_id,
        )
        self.db.add(role)
        self.db.flush()
        return role

    def update_role(
        self,
        slug: str,
        role_id: str,
        actor_id: str,
        name: str | None,
        description: str | None,
        color: str | None,
        privileges: list[str] | None,
    ) -> OrganizationRole:
        org = _get_active_org(self.db, slug)
        _require_owner(org, actor_id)

        role = (
            self.db.query(OrganizationRole)
            .filter(
                OrganizationRole.id == role_id,
                OrganizationRole.organization_id == org.id,
            )
            .first()
        )
        if not role:
            raise LookupError("Role not found")

        if name is not None and name != role.name:
            conflict = (
                self.db.query(OrganizationRole)
                .filter(
                    OrganizationRole.organization_id == org.id,
                    OrganizationRole.name == name,
                    OrganizationRole.id != role_id,
                )
                .first()
            )
            if conflict:
                raise ValueError(f"A role named '{name}' already exists in this organization")
            role.name = name

        if description is not None:
            role.description = description
        if color is not None:
            role.color = color
        if privileges is not None:
            role.privileges = privileges

        self.db.flush()
        return role

    def delete_role(self, slug: str, role_id: str, actor_id: str) -> None:
        org = _get_active_org(self.db, slug)
        _require_owner(org, actor_id)

        role = (
            self.db.query(OrganizationRole)
            .filter(
                OrganizationRole.id == role_id,
                OrganizationRole.organization_id == org.id,
            )
            .first()
        )
        if not role:
            raise LookupError("Role not found")

        # Unassign role from all members before deleting (FK SET NULL handles it in DB,
        # but we flush explicitly so the response is consistent)
        self.db.delete(role)
        self.db.flush()
