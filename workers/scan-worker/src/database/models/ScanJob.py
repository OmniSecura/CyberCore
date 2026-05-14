import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .Base import Base, AuditMixin


class ScanJob(AuditMixin, Base):
    __tablename__ = "scan_jobs"
    __table_args__ = (
        Index(
            "ix_scan_jobs_org_active_created",
            "organization_id",
            "deleted_at",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # No standalone index — the composite ix_scan_jobs_org_active_created
    # below covers organization_id (leftmost column).
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scan_type: Mapped[str] = mapped_column(String(32), nullable=False, default="sast")

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)

    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    findings: Mapped[list["ScanFinding"]] = relationship(  # noqa: F821
        "ScanFinding", back_populates="job", cascade="all, delete-orphan"
    )
