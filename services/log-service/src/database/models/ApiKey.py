import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from .Base import Base, TimestampMixin


class ApiKey(TimestampMixin, Base):
    """
    Per-organization API key used by the `cyberlog` Python client to authenticate
    when ingesting logs.

    Storage policy:
        * The plaintext key is shown to the user EXACTLY ONCE — right after creation.
        * Only the SHA-256 hash is persisted (`key_hash`).
        * `key_prefix` (first 12 chars) is stored separately so the dashboard can
          display "ccl_abc123…" without exposing the full key.
    """
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # The organization that owns this key. Logs ingested with the key are tagged
    # with this org_id so the dashboard can scope queries.
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Free-form label for the dashboard ("production", "staging", "ci").
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # SHA-256 hex digest of the plaintext key (64 chars).
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # First 12 chars of the plaintext (e.g. "ccl_abc123de") — safe to show in UI.
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)

    # Soft-disable without deleting. Cached lookups respect this flag.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optional usage stats — last time this key was seen on an ingest call.
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # When the key stops being valid. NULL = never expires. Auth dependency
    # rejects keys past this timestamp and the cache TTL is capped at the
    # remaining lifetime so expiry takes effect promptly.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_api_keys_org_active", "org_id", "is_active"),
        Index("ix_api_keys_expires_at", "expires_at"),
    )
