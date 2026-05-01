from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared declarative base — ALL models must inherit from this so that
    SQLAlchemy uses a single metadata registry and can resolve foreign keys
    across tables (e.g. user_tokens.user_id → users.id).

    Audit columns are NOT defined here — use the mixins below instead,
    so models that don't need soft-delete (like UserToken) stay clean.
    """
    pass


# ── Mixins ────────────────────────────────────────────────────────────────────

class TimestampMixin:
    """Adds created_at and updated_at to a model."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    """Adds deleted_at for soft-delete support."""
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditMixin(TimestampMixin, SoftDeleteMixin):
    """Full audit trail: created_at + updated_at + deleted_at."""
    pass
