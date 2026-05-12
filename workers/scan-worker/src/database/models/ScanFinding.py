import uuid

from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .Base import Base, TimestampMixin


class ScanFinding(TimestampMixin, Base):
    __tablename__ = "scan_findings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scan_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    tool: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    cwe: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owasp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    job: Mapped["ScanJob"] = relationship("ScanJob", back_populates="findings")  # noqa: F821
