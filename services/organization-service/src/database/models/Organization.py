import uuid
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .Base import Base, AuditMixin


class Organization(AuditMixin, Base):
    __tablename__ = "organization"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)

    organization_slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    organization_description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
