"""
Mirror of log-service's Log model. They MUST stay in sync — both services
write/read the same `logs` table in log_db.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, JSON, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from .Base import Base


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    org_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_logs_org_timestamp", "org_id", "timestamp"),
        Index("ix_logs_org_level_ts", "org_id", "level", "timestamp"),
        Index("ix_logs_org_project_ts", "org_id", "project", "timestamp"),
    )
