import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .Base import Base, TimestampMixin


class OrganizationOwnershipTransfer(TimestampMixin, Base):
    __tablename__ = "organization_ownership_transfers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)

    from_owner_id: Mapped[str] = mapped_column(String(36), nullable=False)

    to_owner_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # SHA-256 hash of the plaintext token sent by email — never store plaintext
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # NULL = pending
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
