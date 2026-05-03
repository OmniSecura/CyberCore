import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .Base import Base, TimestampMixin


class OrganizationInvite(TimestampMixin, Base):
    __tablename__ = "organization_invites"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )

    # Email the invite was sent to — may not have a user account yet
    invited_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role assigned on acceptance
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")

    # user_id of the person who sent the invite
    invited_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # SHA-256 hash of the plaintext token sent by email — never store plaintext
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # NULL = not yet accepted
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
