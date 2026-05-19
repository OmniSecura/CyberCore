import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, JSON, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from .Base import Base


class Log(Base):
    """
    A single log entry ingested from the cyberlog client.

    Logs are write-once, never updated — no `updated_at`, no soft-delete.
    Bulk-inserted by log-consumer (one INSERT per batch popped from Redis).
    """
    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Owning organization (resolved from the API key on ingest).
    org_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Free-form project name supplied by the client (e.g. "my-backend").
    project: Mapped[str] = mapped_column(String(120), nullable=False)

    # info | warning | error | debug | critical
    level: Mapped[str] = mapped_column(String(16), nullable=False)

    # Main log message. Text type to allow long messages without truncation.
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Arbitrary structured fields passed by the user (`order_id="x"`, …).
    fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Wall-clock time AT THE CLIENT when the log was emitted.
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # When log-consumer wrote this entry to the database.
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        # Dashboard's most common query: "logs for org X in reverse-chronological order".
        Index("ix_logs_org_timestamp", "org_id", "timestamp"),
        # Filtering by level inside an org.
        Index("ix_logs_org_level_ts", "org_id", "level", "timestamp"),
        # Filtering by project inside an org.
        Index("ix_logs_org_project_ts", "org_id", "project", "timestamp"),
    )
