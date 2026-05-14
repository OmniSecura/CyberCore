"""
Free-plan org-ownership cap.

Each user can own at most MAX_FREE_ORGS_PER_OWNER active free-plan orgs.
Enforcement points: create, reactivate, initiate-transfer, accept-transfer.

Soft-deleted (deleted_at IS NOT NULL) and paid-plan orgs are NOT counted.
"""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from src.database.models.OrganizationOwnershipTransfer import OrganizationOwnershipTransfer
from src.database.models.OrganizationUsers import OrganizationUser
from src.schemas.organization import CreateOrganizationRequest
from src.services.organization_service import OrgService

# Pin a known cap for the suite so changing the env var doesn't break tests.
CAP = 3


@pytest.fixture(autouse=True)
def _set_cap(monkeypatch):
    monkeypatch.setattr("src.services.organization_service.MAX_FREE_ORGS_PER_OWNER", CAP)


@pytest.fixture(autouse=True)
def _silence_email(monkeypatch):
    """OrgEmailClient hits real SMTP — stub it out for transfer tests."""
    def _noop(self, **kwargs):
        return None
    monkeypatch.setattr(
        "src.services.organization_service.OrgEmailClient.send_ownership_transfer",
        _noop,
    )


# ── count_owned_free_orgs ─────────────────────────────────────────────────────

class TestCountOwnedFreeOrgs:
    def test_counts_only_active_free_orgs(self, db_session, make_user_factory, make_org_factory):
        user = make_user_factory()
        # 2 active free — counted
        make_org_factory(owner_id=user.id, plan="free")
        make_org_factory(owner_id=user.id, plan="free")
        # paid — not counted
        make_org_factory(owner_id=user.id, plan="pro")
        # soft-deleted free — not counted
        make_org_factory(
            owner_id=user.id, plan="free",
            is_active=False, deleted_at=datetime.now(timezone.utc),
        )
        # inactive (but not soft-deleted) — not counted
        make_org_factory(owner_id=user.id, plan="free", is_active=False)
        # owned by someone else — not counted
        other = make_user_factory()
        make_org_factory(owner_id=other.id, plan="free")

        assert OrgService(db_session).count_owned_free_orgs(user.id) == 2


# ── create_organization ───────────────────────────────────────────────────────

class TestCreateOrganization:
    def test_allows_when_under_cap(self, db_session, make_user_factory, make_org_factory):
        user = make_user_factory()
        for _ in range(CAP - 1):
            make_org_factory(owner_id=user.id, plan="free")

        svc = OrgService(db_session)
        org = svc.create_organization(
            CreateOrganizationRequest(
                organization_name="new", organization_slug="brand-new",
            ),
            creator_id=user.id,
        )
        assert org.id is not None

    def test_blocks_at_cap(self, db_session, make_user_factory, make_org_factory):
        user = make_user_factory()
        for _ in range(CAP):
            make_org_factory(owner_id=user.id, plan="free")

        svc = OrgService(db_session)
        with pytest.raises(ValueError, match="maximum"):
            svc.create_organization(
                CreateOrganizationRequest(
                    organization_name="overflow", organization_slug="overflow",
                ),
                creator_id=user.id,
            )

    def test_soft_deleted_dont_count(self, db_session, make_user_factory, make_org_factory):
        """Regression guard: cycling delete → create must not be a loophole.
        If soft-deleted orgs were counted, a user could never recover after
        hitting and recovering from the cap."""
        user = make_user_factory()
        # CAP soft-deleted orgs
        for _ in range(CAP):
            make_org_factory(
                owner_id=user.id, plan="free",
                is_active=False, deleted_at=datetime.now(timezone.utc),
            )

        svc = OrgService(db_session)
        # Should succeed — all existing are soft-deleted
        org = svc.create_organization(
            CreateOrganizationRequest(
                organization_name="fresh", organization_slug="fresh",
            ),
            creator_id=user.id,
        )
        assert org.id is not None

    def test_paid_orgs_dont_count(self, db_session, make_user_factory, make_org_factory):
        user = make_user_factory()
        for _ in range(CAP):
            make_org_factory(owner_id=user.id, plan="pro")

        svc = OrgService(db_session)
        org = svc.create_organization(
            CreateOrganizationRequest(
                organization_name="still ok", organization_slug="still-ok",
            ),
            creator_id=user.id,
        )
        assert org.id is not None


# ── reactivate_organization ───────────────────────────────────────────────────

class TestReactivateOrganization:
    def test_blocks_when_at_cap_for_free(self, db_session, make_user_factory, make_org_factory):
        user = make_user_factory()
        # CAP active free orgs already
        for _ in range(CAP):
            make_org_factory(owner_id=user.id, plan="free")
        # And one soft-deleted free we want to bring back
        dormant = make_org_factory(
            owner_id=user.id, plan="free",
            is_active=False, deleted_at=datetime.now(timezone.utc),
        )

        svc = OrgService(db_session)
        with pytest.raises(ValueError, match="maximum"):
            svc.reactivate_organization(org_id=dormant.id, actor_id=user.id)

    def test_allows_under_cap(self, db_session, make_user_factory, make_org_factory):
        user = make_user_factory()
        # CAP-1 active free
        for _ in range(CAP - 1):
            make_org_factory(owner_id=user.id, plan="free")
        dormant = make_org_factory(
            owner_id=user.id, plan="free",
            is_active=False, deleted_at=datetime.now(timezone.utc),
        )

        svc = OrgService(db_session)
        out = svc.reactivate_organization(org_id=dormant.id, actor_id=user.id)
        assert out.is_active is True
        assert out.deleted_at is None

    def test_paid_org_reactivation_ignores_cap(self, db_session, make_user_factory, make_org_factory):
        """Cap is only on free-plan orgs — reactivating a paid one is unaffected
        even if the user is at the free cap."""
        user = make_user_factory()
        for _ in range(CAP):
            make_org_factory(owner_id=user.id, plan="free")
        dormant = make_org_factory(
            owner_id=user.id, plan="pro",
            is_active=False, deleted_at=datetime.now(timezone.utc),
        )

        svc = OrgService(db_session)
        out = svc.reactivate_organization(org_id=dormant.id, actor_id=user.id)
        assert out.is_active is True


# ── initiate_transfer_ownership ───────────────────────────────────────────────

class TestInitiateTransfer:
    def test_blocks_when_recipient_at_cap_and_org_is_free(
        self, db_session, make_user_factory, make_org_factory,
    ):
        owner = make_user_factory()
        recipient = make_user_factory()
        # Recipient is at the cap
        for _ in range(CAP):
            make_org_factory(owner_id=recipient.id, plan="free")

        # Owner's free org being transferred
        org = make_org_factory(owner_id=owner.id, plan="free", slug="being-handed-off")
        # Recipient must be a member of the org
        db_session.add(OrganizationUser(
            organization_id=org.id, user_id=recipient.id, role="admin",
        ))
        db_session.flush()

        svc = OrgService(db_session)
        with pytest.raises(ValueError, match="Recipient"):
            svc.initiate_transfer_ownership(
                slug=org.organization_slug,
                actor_id=owner.id,
                new_owner_id=recipient.id,
            )

    def test_allows_when_org_is_paid_even_if_recipient_at_free_cap(
        self, db_session, make_user_factory, make_org_factory,
    ):
        """Paid orgs don't count toward the recipient's free cap, so the
        transfer should go through."""
        owner = make_user_factory()
        recipient = make_user_factory()
        for _ in range(CAP):
            make_org_factory(owner_id=recipient.id, plan="free")

        org = make_org_factory(owner_id=owner.id, plan="pro", slug="paid-org")
        db_session.add(OrganizationUser(
            organization_id=org.id, user_id=recipient.id, role="admin",
        ))
        db_session.flush()

        svc = OrgService(db_session)
        # Should not raise
        svc.initiate_transfer_ownership(
            slug=org.organization_slug,
            actor_id=owner.id,
            new_owner_id=recipient.id,
        )


# ── accept_ownership_transfer ─────────────────────────────────────────────────

class TestAcceptTransfer:
    def _create_pending_transfer(self, db_session, org_id, from_id, to_id):
        """Insert a transfer row directly — bypasses the initiate-time cap check
        so we can independently test accept-time enforcement."""
        token = "plain-token-" + org_id[:8]
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        transfer = OrganizationOwnershipTransfer(
            organization_id=org_id,
            from_owner_id=from_id,
            to_owner_id=to_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db_session.add(transfer)
        db_session.flush()
        return token

    def test_blocks_if_recipient_hit_cap_between_initiate_and_accept(
        self, db_session, make_user_factory, make_org_factory,
    ):
        """Recipient passed the cap at initiate time (had 2 free orgs), then
        created/accepted more before clicking the link. Accept must re-check."""
        owner = make_user_factory()
        recipient = make_user_factory()
        org = make_org_factory(owner_id=owner.id, plan="free", slug="x-org")
        token = self._create_pending_transfer(db_session, org.id, owner.id, recipient.id)

        # Now recipient hits the cap with other orgs
        for _ in range(CAP):
            make_org_factory(owner_id=recipient.id, plan="free")

        svc = OrgService(db_session)
        with pytest.raises(ValueError, match="maximum"):
            svc.accept_ownership_transfer(token=token, user_id=recipient.id)

    def test_allows_when_recipient_under_cap(
        self, db_session, make_user_factory, make_org_factory,
    ):
        owner = make_user_factory()
        recipient = make_user_factory()
        org = make_org_factory(owner_id=owner.id, plan="free", slug="ok-org")
        # Recipient has CAP-1 free orgs — accepting this one brings them to CAP, exact fit
        for _ in range(CAP - 1):
            make_org_factory(owner_id=recipient.id, plan="free")

        token = self._create_pending_transfer(db_session, org.id, owner.id, recipient.id)

        svc = OrgService(db_session)
        out = svc.accept_ownership_transfer(token=token, user_id=recipient.id)
        assert out.owner_id == recipient.id
