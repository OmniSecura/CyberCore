import uuid
from sqlalchemy import String, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .Base import Base, TimestampMixin


class OrganizationRole(TimestampMixin, Base):
    __tablename__ = "organization_roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_org_role_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    organization_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # hex e.g. #3B82F6

    # JSON array of privilege keys, e.g. ["members.view", "scans.run"]
    privileges: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
