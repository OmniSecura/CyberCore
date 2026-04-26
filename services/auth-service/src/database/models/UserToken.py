import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .Base import Base, TimestampMixin


class UserToken(TimestampMixin, Base):
    __tablename__ = "user_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # 'email_verification' | 'password_reset' | 'org_invite'
    token_type: Mapped[str] = mapped_column(String(50), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # NULL = not yet used
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)