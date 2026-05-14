import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.models.Organization import Organization
from ..database.models.OrganizationOwnershipTransfer import OrganizationOwnershipTransfer
from ..database.models.OrganizationUsers import OrganizationUser
from ..database.models.User import User
from ..global_settings import MAX_FREE_ORGS_PER_OWNER
from ..schemas.organization import CreateOrganizationRequest, UpdateOrganizationRequest
from ..utils.email_client import OrgEmailClient

logger = logging.getLogger(__name__)


class OrgService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_by_slug(self, slug: str) -> Organization | None:
        # NOTE: returns inactive (soft-deleted) orgs too. deleted_at is a retention
        # marker for cleanup jobs, not a hide flag. Callers gate on is_active when
        # needed.
        return (
            self.db.query(Organization)
            .filter(Organization.organization_slug == slug)
            .first()
        )

    def get_by_id(self, org_id: str) -> Organization | None:
        return (
            self.db.query(Organization)
            .filter(Organization.id == org_id)
            .first()
        )

    def get_by_owner_id(self, owner_id: str) -> list[type[Organization]]:  # str nie int
        return (
            self.db.query(Organization)
            .filter(
                Organization.owner_id == owner_id,
                Organization.deleted_at.is_(None),
            )
            .all()
        )

    def list_user_orgs(self, user_id: str) -> list[type[Organization]]:
        member_org_ids = (
            select(OrganizationUser.organization_id)
            .where(OrganizationUser.user_id == user_id)
        )
        return (
            self.db.query(Organization)
            .filter(
                Organization.deleted_at.is_(None),
                Organization.is_active == True,
                (Organization.owner_id == user_id) |
                (Organization.id.in_(member_org_ids))
            )
            .all()
        )

    def list_user_orgs_paginated(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[tuple[Organization, str]], int]:
        """Returns ([(org, role)], total) — role is the actor's role on each org."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        member_org_ids = (
            select(OrganizationUser.organization_id)
            .where(OrganizationUser.user_id == user_id)
        )

        base = (
            self.db.query(Organization)
            .filter(
                (Organization.owner_id == user_id) |
                (Organization.id.in_(member_org_ids))
            )
            .order_by(Organization.is_active.desc(), Organization.id)
        )

        total = base.count()
        orgs = base.offset((page - 1) * page_size).limit(page_size).all()

        member_roles = {
            ou.organization_id: ou.role
            for ou in self.db.query(OrganizationUser)
                              .filter(OrganizationUser.user_id == user_id)
                              .all()
        }

        result: list[tuple[Organization, str]] = []
        for org in orgs:
            if org.owner_id == user_id:
                role = "owner"
            else:
                role = member_roles.get(org.id, "viewer")
            result.append((org, role))

        return result, total

    def get_user_role(self, org: Organization, user_id: str) -> str:
        if org.owner_id == user_id:
            return "owner"
        member = (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == org.id,
                OrganizationUser.user_id == user_id,
            )
            .first()
        )
        return member.role if member else "viewer"

    def count_owned_free_orgs(self, user_id: str) -> int:
        """Active (not soft-deleted) free-plan orgs owned by user. Soft-deleted
        orgs are excluded so users can't be permanently locked out by orgs they
        already deleted."""
        return (
            self.db.query(Organization)
            .filter(
                Organization.owner_id == user_id,
                Organization.plan == "free",
                Organization.deleted_at.is_(None),
                Organization.is_active == True,
            )
            .count()
        )

    def count_org_members(self, org_id: str) -> int:
        """Member count = OrganizationUser rows + 1 (for the owner)."""
        members = (
            self.db.query(OrganizationUser)
            .filter(OrganizationUser.organization_id == org_id)
            .count()
        )
        return members + 1

    def get_org_for_user(self, slug: str, user_id: str) -> Organization:
        org = self.get_by_slug(slug)
        if not org:
            raise LookupError("Organization not found")

        is_owner = org.owner_id == user_id
        is_member = (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == org.id,
                OrganizationUser.user_id == user_id,
            )
            .first()
        )

        if not is_owner and not is_member:
            raise PermissionError("You are not a member of this organization")

        return org

    def initiate_transfer_ownership(
            self, slug: str, actor_id: str, new_owner_id: str
    ) -> None:
        org = self.get_by_slug(slug)
        if not org:
            raise LookupError("Organization not found")

        if org.owner_id != actor_id:
            raise PermissionError("Only the owner can transfer ownership")

        if actor_id == new_owner_id:
            raise ValueError("You are already the owner")

        new_owner_member = (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == org.id,
                OrganizationUser.user_id == new_owner_id,
            )
            .first()
        )
        if not new_owner_member:
            raise ValueError("New owner must be a member of the organization")

        new_owner = self.db.query(User).filter(User.id == new_owner_id).first()
        if not new_owner:
            raise LookupError("New owner user not found")

        # Free-plan cap on the recipient — fail fast so we don't email someone
        # who'd be blocked at accept-time anyway. The same check runs at accept-time
        # to cover state changes between initiate and accept.
        if (
            org.plan == "free"
            and self.count_owned_free_orgs(new_owner_id) >= MAX_FREE_ORGS_PER_OWNER
        ):
            raise ValueError(
                f"Recipient already owns the maximum of {MAX_FREE_ORGS_PER_OWNER} "
                f"free-plan organizations"
            )

        # Cancel any existing pending transfer for this org
        existing = (
            self.db.query(OrganizationOwnershipTransfer)
            .filter(
                OrganizationOwnershipTransfer.organization_id == org.id,
                OrganizationOwnershipTransfer.accepted_at.is_(None),
                OrganizationOwnershipTransfer.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )
        if existing:
            self.db.delete(existing)

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        transfer = OrganizationOwnershipTransfer(
            organization_id=org.id,
            from_owner_id=actor_id,
            to_owner_id=new_owner_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        )
        self.db.add(transfer)
        self.db.flush()

        actor = self.db.query(User).filter(User.id == actor_id).first()
        actor_name = actor.full_name if actor else "Your organization owner"

        try:
            OrgEmailClient().send_ownership_transfer(
                to=new_owner.email,
                from_owner_name=actor_name,
                org_name=org.organization_name,
                token=token,
            )
        except Exception as exc:
            logger.warning("Ownership transfer email failed for %s: %s", new_owner.email, exc)

    def accept_ownership_transfer(self, token: str, user_id: str) -> Organization:
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        transfer = (
            self.db.query(OrganizationOwnershipTransfer)
            .filter(
                OrganizationOwnershipTransfer.token_hash == token_hash,
                OrganizationOwnershipTransfer.accepted_at.is_(None),
            )
            .first()
        )
        if not transfer:
            raise LookupError("Invalid or already-used transfer token")

        if transfer.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise ValueError("This transfer request has expired")

        if transfer.to_owner_id != user_id:
            raise PermissionError("This transfer was not sent to you")

        org = self.get_by_id(transfer.organization_id)
        if not org:
            raise LookupError("Organization not found")

        # Re-check the recipient's free-plan cap — state may have changed since
        # the transfer was initiated (recipient created/accepted other free orgs).
        if (
            org.plan == "free"
            and self.count_owned_free_orgs(user_id) >= MAX_FREE_ORGS_PER_OWNER
        ):
            raise ValueError(
                f"You already own the maximum of {MAX_FREE_ORGS_PER_OWNER} "
                f"free-plan organizations"
            )

        prev_owner_id = org.owner_id

        # The new owner was a member — drop the membership row (they become owner now).
        self.db.query(OrganizationUser).filter(
            OrganizationUser.organization_id == org.id,
            OrganizationUser.user_id == transfer.to_owner_id,
        ).delete(synchronize_session=False)

        # The previous owner needs an explicit row now (was implicit before).
        # Give them admin so they don't lose access on the spot.
        already = (
            self.db.query(OrganizationUser)
            .filter(
                OrganizationUser.organization_id == org.id,
                OrganizationUser.user_id == prev_owner_id,
            )
            .first()
        )
        if not already:
            self.db.add(OrganizationUser(
                organization_id=org.id,
                user_id=prev_owner_id,
                role="admin",
                invited_by=transfer.to_owner_id,
            ))

        org.owner_id = transfer.to_owner_id
        transfer.accepted_at = datetime.now(timezone.utc)
        self.db.flush()
        return org

    def reactivate_organization(
            self, org_id: str, actor_id: str, new_slug: str | None = None
    ) -> Organization:
        org = self.get_by_id(org_id)
        if not org:
            raise LookupError("Organization not found")

        if org.owner_id != actor_id:
            raise PermissionError("Only the owner can reactivate the organization")

        if org.is_active:
            raise ValueError("Organization is already active")

        # Reactivation revives an org into the active set — re-check the free-plan
        # cap so users can't exceed it by deleting, creating, then reactivating.
        if (
            org.plan == "free"
            and self.count_owned_free_orgs(actor_id) >= MAX_FREE_ORGS_PER_OWNER
        ):
            raise ValueError(
                f"You already own the maximum of {MAX_FREE_ORGS_PER_OWNER} "
                f"free-plan organizations"
            )

        # Optional rename on reactivation — uniqueness is checked against other orgs.
        if new_slug and new_slug != org.organization_slug:
            existing = self.get_by_slug(new_slug)
            if existing and existing.id != org.id:
                raise ValueError(
                    f"Slug '{new_slug}' is already taken — please choose a different one"
                )
            org.organization_slug = new_slug

        org.is_active = True
        org.deleted_at = None
        self.db.flush()
        return org

    # ── Mutations ─────────────────────────────────────────────────────────────

    def create_organization(
        self, data: CreateOrganizationRequest, creator_id: str
    ) -> Organization:
        if self.get_by_slug(data.organization_slug):
            raise ValueError(
                f"Slug '{data.organization_slug}' is already taken"
            )

        # New orgs default to the free plan — enforce the per-owner free-plan cap.
        if self.count_owned_free_orgs(creator_id) >= MAX_FREE_ORGS_PER_OWNER:
            raise ValueError(
                f"You already own the maximum of {MAX_FREE_ORGS_PER_OWNER} "
                f"free-plan organizations"
            )

        org = Organization(
            owner_id=creator_id,
            organization_slug=data.organization_slug,
            organization_name=data.organization_name,
            organization_description=data.organization_description,
        )
        self.db.add(org)
        self.db.flush()
        return org

    def update_organization(
        self, slug: str, data: UpdateOrganizationRequest, actor_id: str
    ) -> Organization:
        org = self.get_by_slug(slug)
        if not org:
            raise LookupError(f"Organization not found")

        if org.owner_id != actor_id:
            raise PermissionError("Only the owner can update the organization")

        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "organization_slug" and value != org.organization_slug:
                if self.get_by_slug(value):
                    raise ValueError(f"Slug '{value}' is already taken")
            setattr(org, field, value)

        self.db.flush()
        return org

    def soft_delete_organization(self, slug: str, actor_id: str) -> None:
        """
        Soft-delete the organization. The row stays in the database with
        is_active=False and deleted_at=now() — visible to the owner as 'Inactive'
        and reactivatable. A scheduled cleanup job is expected to hard-delete
        rows whose deleted_at is older than the retention window.
        """
        org = self.get_by_slug(slug)
        if not org:
            raise LookupError(f"Organization '{slug}' not found")

        if org.owner_id != actor_id:
            raise PermissionError("Only the owner can delete the organization")

        org.is_active = False
        org.deleted_at = datetime.now(timezone.utc)
        self.db.flush()
