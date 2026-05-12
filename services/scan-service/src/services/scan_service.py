from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from celery import Celery
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from ..database.models.ScanJob import ScanJob
from ..database.models.ScanFinding import ScanFinding
from ..schemas.scan import SubmitGitScanRequest

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
SCAN_UPLOAD_DIR = os.getenv("SCAN_UPLOAD_DIR", "/tmp/cybercore/uploads")

_celery = Celery(broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


class ScanService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Submit ─────────────────────────────────────────────────────────────────

    def submit_git_scan(
        self,
        organization_id: str,
        user_id: str,
        body: SubmitGitScanRequest,
    ) -> ScanJob:
        job = ScanJob(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            created_by=user_id,
            name=body.name,
            scan_type="sast",
            status="queued",
            target_type="git_url",
            target_url=body.target_url,
        )
        self.db.add(job)
        self.db.flush()

        task = _celery.send_task(
            "scan_worker.tasks.sast.run_sast_scan",
            args=[job.id],
            queue="sast",
        )
        job.celery_task_id = task.id
        self.db.commit()
        self.db.refresh(job)
        return job

    async def submit_upload_scan(
        self,
        organization_id: str,
        user_id: str,
        name: str,
        file: UploadFile,
    ) -> ScanJob:
        os.makedirs(SCAN_UPLOAD_DIR, exist_ok=True)

        file_id = str(uuid.uuid4())
        dest = os.path.join(SCAN_UPLOAD_DIR, f"{file_id}.zip")
        content = await file.read()
        with open(dest, "wb") as fh:
            fh.write(content)

        job = ScanJob(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            created_by=user_id,
            name=name,
            scan_type="sast",
            status="queued",
            target_type="upload",
            target_path=dest,
        )
        self.db.add(job)
        self.db.flush()

        task = _celery.send_task(
            "scan_worker.tasks.sast.run_sast_scan",
            args=[job.id],
            queue="sast",
        )
        job.celery_task_id = task.id
        self.db.commit()
        self.db.refresh(job)
        return job

    # ── Read ───────────────────────────────────────────────────────────────────

    def list_jobs(
        self,
        organization_id: str,
        offset: int = 0,
        limit: int = 20,
        status_filter: str | None = None,
    ) -> tuple[int, list[ScanJob]]:
        q = (
            self.db.query(ScanJob)
            .filter(
                ScanJob.organization_id == organization_id,
                ScanJob.deleted_at.is_(None),
            )
        )
        if status_filter:
            q = q.filter(ScanJob.status == status_filter)

        total = q.count()
        items = q.order_by(ScanJob.created_at.desc()).offset(offset).limit(limit).all()
        return total, items

    def get_job(self, organization_id: str, job_id: str) -> ScanJob:
        job = (
            self.db.query(ScanJob)
            .filter(
                ScanJob.id == job_id,
                ScanJob.organization_id == organization_id,
                ScanJob.deleted_at.is_(None),
            )
            .first()
        )
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan job not found")
        return job

    def list_findings(
        self,
        organization_id: str,
        job_id: str,
        offset: int = 0,
        limit: int = 50,
        severity_filter: str | None = None,
        tool_filter: str | None = None,
    ) -> tuple[int, list[ScanFinding], dict[str, int]]:
        job = self.get_job(organization_id, job_id)

        q = self.db.query(ScanFinding).filter(ScanFinding.scan_job_id == job.id)
        if severity_filter:
            q = q.filter(ScanFinding.severity == severity_filter)
        if tool_filter:
            q = q.filter(ScanFinding.tool == tool_filter)

        total = q.count()
        items = q.order_by(ScanFinding.severity, ScanFinding.file_path).offset(offset).limit(limit).all()

        severity_counts: dict[str, int] = {}
        for sev in ("critical", "high", "medium", "low", "info"):
            severity_counts[sev] = (
                self.db.query(ScanFinding)
                .filter(ScanFinding.scan_job_id == job.id, ScanFinding.severity == sev)
                .count()
            )

        return total, items, severity_counts

    # ── Cancel ─────────────────────────────────────────────────────────────────

    def cancel_job(self, organization_id: str, job_id: str) -> ScanJob:
        job = self.get_job(organization_id, job_id)

        if job.status not in ("queued", "running"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel a job with status '{job.status}'",
            )

        if job.celery_task_id:
            try:
                _celery.control.revoke(job.celery_task_id, terminate=True)
            except Exception:
                pass

        job.status = "cancelled"
        job.completed_at = datetime.now(tz=timezone.utc)
        self.db.commit()
        self.db.refresh(job)
        return job

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_job(self, organization_id: str, job_id: str) -> None:
        job = self.get_job(organization_id, job_id)

        if job.status == "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a running scan. Cancel it first.",
            )

        job.deleted_at = datetime.now(tz=timezone.utc)
        self.db.commit()
