import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from ..database.models.Organization import Organization
from ..database.models.OrganizationInvites import OrganizationInvite
from ..database.models.OrganizationRole import OrganizationRole
from ..database.models.OrganizationUsers import OrganizationUser
from ..utils.email_client import OrgEmailClient

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


def _require_admin_or_owner(db: Session, org: Organization, user_id: str) -> None:
    if org.owner_id == user_id:
        return
    member = (
        db.query(OrganizationUser)
        .filter(
            OrganizationUser.organization_id == org.id,
            OrganizationUser.user_id == user_id,
        )
        .first()
    )
    if not member or member.role != "admin":
        raise PermissionError("Only owners and admins can perform this action")


def _require_any_member(db: Session, org: Organization, user_id: str) -> None:
    if org.owner_id == user_id:
        return
    member = (
        db.query(OrganizationUser)
        .filter(
            OrganizationUser.organization_id == org.id,
            OrganizationUser.user_id == user_id,
        )
        .first()
    )
    if not member:
        raise PermissionError("You are not a member of this organization")


# ── Member service ─────────────────────────────────────────────────────────────

class MemberService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_members(self, slug: str, actor_id: str) -> list[OrganizationUser]:
        org = _get_active_org(self.db, slug)
        _require_any_member(self.db, org, actor_id)
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
        _require_admin_or_owner(self.db, org, actor_id)

        if user_id == org.owner_id:
            raise ValueError("Cannot change the owner's role")

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
            # Verify the custom role belongs to this org
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
            member.role = "member"  # base access level when using a custom role
        else:
            # Assigning a built-in role clears any custom role
            member.role = role
            member.custom_role_id = None

        self.db.flush()
        return member

    def remove_member(self, slug: str, user_id: str, actor_id: str) -> None:
        org = _get_active_org(self.db, slug)

        if user_id == org.owner_id:
            raise ValueError("Cannot remove the organization owner")

        # Members can leave themselves; otherwise must be owner/admin
        if actor_id != user_id:
            _require_admin_or_owner(self.db, org, actor_id)

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
