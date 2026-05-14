"""
Shared pytest fixtures.

Uses an in-memory SQLite engine with StaticPool so all sessions in a test
share the same connection (otherwise each session gets its own empty DB).
"""
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Import every model module so their tables are registered on Base.metadata
# before create_all runs.
from src.database.models.Base import Base
from src.database.models.Organization import Organization  # noqa: F401
from src.database.models.OrganizationInvites import OrganizationInvite  # noqa: F401
from src.database.models.OrganizationOwnershipTransfer import OrganizationOwnershipTransfer  # noqa: F401
from src.database.models.OrganizationRole import OrganizationRole  # noqa: F401
from src.database.models.OrganizationUsers import OrganizationUser  # noqa: F401
from src.database.models.User import User


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ── Builders ──────────────────────────────────────────────────────────────────

def make_user(db: Session, *, email: str | None = None, full_name: str = "Test User") -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email or f"{uuid.uuid4().hex[:8]}@test.local",
        full_name=full_name,
    )
    db.add(user)
    db.flush()
    return user


def make_org(
    db: Session,
    *,
    owner_id: str,
    plan: str = "free",
    is_active: bool = True,
    deleted_at=None,
    slug: str | None = None,
    name: str | None = None,
) -> Organization:
    org = Organization(
        owner_id=owner_id,
        organization_slug=slug or f"org-{uuid.uuid4().hex[:8]}",
        organization_name=name or "Test Org",
        plan=plan,
        is_active=is_active,
        deleted_at=deleted_at,
    )
    db.add(org)
    db.flush()
    return org


@pytest.fixture
def make_user_factory(db_session):
    def _make(**kwargs):
        return make_user(db_session, **kwargs)
    return _make


@pytest.fixture
def make_org_factory(db_session):
    def _make(**kwargs):
        return make_org(db_session, **kwargs)
    return _make
