import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from ..database.models.Organization import Organization
from ..database.models.OrganizationOwnershipTransfer import OrganizationOwnershipTransfer
from ..database.models.OrganizationUsers import OrganizationUser
from ..database.models.User import User
from ..schemas.organization import CreateOrganizationRequest, UpdateOrganizationRequest
from ..utils.email_client import OrgEmailClient

logger = logging.getLogger(__name__)


class OrgService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_by_slug(self, slug: str) -> Organization | None:
        return (
            self.db.query(Organization)
            .filter(
                Organization.organization_slug == slug,
                Organization.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_id(self, org_id: str) -> Organization | None:
        return (
            self.db.query(Organization)
            .filter(
                Organization.id == org_id,
                Organization.deleted_at.is_(None),
            )
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
            self.db.query(OrganizationUser.organization_id)
            .filter(OrganizationUser.user_id == user_id)
            .subquery()
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

        org.owner_id = transfer.to_owner_id
        transfer.accepted_at = datetime.now(timezone.utc)
        self.db.flush()
        return org

    def reactivate_organization(
            self, org_id: str, actor_id: str, new_slug: str | None = None
    ) -> type[Organization]:
        org = (
            self.db.query(Organization)
            .filter(Organization.id == org_id)
            .first()
        )
        if not org:
            raise LookupError("Organization not found")

        if org.owner_id != actor_id:
            raise PermissionError("Only the owner can reactivate the organization")

        # Resolve which slug to use after reactivation
        if new_slug:
            # User explicitly provided a new slug — check availability
            if self.get_by_slug(new_slug):
                raise ValueError(
                    f"Slug '{new_slug}' is already taken — please choose a different one"
                )
            restored_slug = new_slug
        else:
            # Attempt to restore original slug by stripping the _deleted_ suffix
            original_slug = org.organization_slug.split("_deleted_")[0]
            if self.get_by_slug(original_slug):
                raise ValueError(
                    f"Original slug '{original_slug}' is already taken. "
                    f"Please provide a new slug via the 'new_slug' field."
                )
            restored_slug = original_slug

        org.organization_slug = restored_slug
        org.deleted_at = None
        org.is_active = True
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
        org = self.get_by_slug(slug)
        if not org:
            raise LookupError(f"Organization '{slug}' not found")

        if org.owner_id != actor_id:
            raise PermissionError("Only the owner can delete the organization")

        org.organization_slug = f"{org.organization_slug}_deleted_{org.id[:8]}"
        org.deleted_at = datetime.now(timezone.utc)
        org.is_active = False
        self.db.flush()
