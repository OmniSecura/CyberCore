import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from ..database.models.Organization import Organization
from ..database.models.OrganizationInvites import OrganizationInvite
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

class InviteService:

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_invite(
        self,
        slug: str,
        actor_id: str,
        actor_name: str,
        email: str,
        role: str,
    ) -> OrganizationInvite:
        org = _get_active_org(self.db, slug)
        _require_admin_or_owner(self.db, org, actor_id)

        existing = (
            self.db.query(OrganizationInvite)
            .filter(
                OrganizationInvite.organization_id == org.id,
                OrganizationInvite.invited_email == email,
                OrganizationInvite.used_at.is_(None),
                OrganizationInvite.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )
        if existing:
            raise ValueError(f"A pending invite already exists for {email}")

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        invite = OrganizationInvite(
            organization_id=org.id,
            invited_email=email,
            role=role,
            invited_by=actor_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        )
        self.db.add(invite)
        self.db.flush()

        try:
            OrgEmailClient().send_org_invite(
                to=email,
                invited_by_name=actor_name,
                org_name=org.organization_name,
                role=role,
                token=token,
            )
        except Exception as exc:
            # Log but don't fail — invite is valid, admin can resend
            logger.warning("Invite email failed for %s: %s", email, exc)

        return invite

    def list_invites(self, slug: str, actor_id: str) -> list[OrganizationInvite]:
        org = _get_active_org(self.db, slug)
        _require_admin_or_owner(self.db, org, actor_id)
        return (
            self.db.query(OrganizationInvite)
            .filter(
                OrganizationInvite.organization_id == org.id,
                OrganizationInvite.used_at.is_(None),
            )
            .all()
        )

    def revoke_invite(self, slug: str, invite_id: str, actor_id: str) -> None:
        org = _get_active_org(self.db, slug)
        _require_admin_or_owner(self.db, org, actor_id)

        invite = (
            self.db.query(OrganizationInvite)
            .filter(
                OrganizationInvite.id == invite_id,
                OrganizationInvite.organization_id == org.id,
            )
            .first()
        )
        if not invite:
            raise LookupError("Invite not found")

        self.db.delete(invite)
        self.db.flush()

    def accept_invite(self, token: str, user_id: str, user_email: str) -> OrganizationInvite:
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        invite = (
            self.db.query(OrganizationInvite)
            .filter(
                OrganizationInvite.token_hash == token_hash,
                OrganizationInvite.used_at.is_(None),
            )
            .first()
        )
        if not invite:
            raise LookupError("Invalid or already-used invite token")

        if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise ValueError("This invite has expired")

        if invite.invited_email != user_email.lower():
            raise PermissionError("This invite was sent to a different email address")

        already = (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == invite.organization_id,
                OrganizationUser.user_id == user_id,
            )
            .first()
        )
        if already:
            raise ValueError("You are already a member of this organization")

        membership = OrganizationUser(
            organization_id=invite.organization_id,
            user_id=user_id,
            role=invite.role,
            invited_by=invite.invited_by,
        )
        self.db.add(membership)
        invite.used_at = datetime.now(timezone.utc)
        self.db.flush()
        return invite
