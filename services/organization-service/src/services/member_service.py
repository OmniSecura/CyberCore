import logging

from sqlalchemy.orm import Session

from ..database.models.Organization import Organization
from ..database.models.OrganizationRole import OrganizationRole
from ..database.models.OrganizationUsers import OrganizationUser
from ..privileges import require_privilege

logger = logging.getLogger(__name__)


def _get_active_org(db: Session, slug: str) -> Organization:
    org = (
        db.query(Organization)
        .filter(Organization.organization_slug == slug, Organization.deleted_at.is_(None))
        .first()
    )
    if not org:
        raise LookupError("Organization not found")
    return org


# ── Member service ─────────────────────────────────────────────────────────────

class MemberService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_members(self, slug: str, actor_id: str) -> list[OrganizationUser]:
        org = _get_active_org(self.db, slug)
        require_privilege(self.db, org, actor_id, "members.view")
        return (
            self.db.query(OrganizationUser)
            .filter(OrganizationUser.organization_id == org.id)
            .all()
        )

    def update_member_role(
        self,
        slug: str,
        user_id: str,
        actor_id: str,
        role: str | None,
        custom_role_id: str | None,
    ) -> OrganizationUser:
        org = _get_active_org(self.db, slug)
        require_privilege(self.db, org, actor_id, "members.manage_roles")

        if user_id == org.owner_id:
            raise ValueError("Cannot change the owner's role")

        if user_id == actor_id:
            raise ValueError("Cannot change your own role")

        member = (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == org.id,
                OrganizationUser.user_id == user_id,
            )
            .first()
        )
        if not member:
            raise LookupError("Member not found")

        if custom_role_id is not None:
            custom_role = (
                self.db.query(OrganizationRole)
                .filter(
                    OrganizationRole.id == custom_role_id,
                    OrganizationRole.organization_id == org.id,
                )
                .first()
            )
            if not custom_role:
                raise LookupError("Custom role not found in this organization")
            member.custom_role_id = custom_role_id
            member.role = "member"
        else:
            member.role = role
            member.custom_role_id = None

        self.db.flush()
        return member

    def remove_member(self, slug: str, user_id: str, actor_id: str) -> None:
        org = _get_active_org(self.db, slug)

        if user_id == org.owner_id:
            raise ValueError("Cannot remove the organization owner")

        # Members can always leave themselves; removing others requires the privilege
        if actor_id != user_id:
            require_privilege(self.db, org, actor_id, "members.remove")

        member = (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == org.id,
                OrganizationUser.user_id == user_id,
            )
            .first()
        )
        if not member:
            raise LookupError("Member not found")

        self.db.delete(member)
        self.db.flush()
