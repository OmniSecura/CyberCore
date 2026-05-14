from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from celery import Celery
from fastapi import HTTPException, status, UploadFile
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from ..database.models.ScanJob import ScanJob
from ..database.models.ScanFinding import ScanFinding
from ..schemas.scan import SubmitGitScanRequest, SubmitWebScanRequest

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
_DEFAULT_TMP = "C:/tmp/cybercore" if os.name == "nt" else "/tmp/cybercore"
SCAN_UPLOAD_DIR = os.getenv("SCAN_UPLOAD_DIR", f"{_DEFAULT_TMP}/uploads")

# Hard upload cap (bytes). Configurable so ops can bump it without a code change.
MAX_UPLOAD_BYTES = int(os.getenv("SCAN_UPLOAD_MAX_BYTES", str(500 * 1024 * 1024)))
# Stream chunk size for the upload writer.
_UPLOAD_CHUNK = 1 * 1024 * 1024  # 1 MiB

# Free-plan quota — enforced server-side. The 3-active-scans limit the UI shows
# is the same number; the backend is the source of truth.
FREE_PLAN_ACTIVE_LIMIT = int(os.getenv("SCAN_FREE_PLAN_ACTIVE_LIMIT", "3"))
FREE_PLAN_DAILY_LIMIT = int(os.getenv("SCAN_FREE_PLAN_DAILY_LIMIT", "3"))

_celery = Celery(broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


def _revoke_task(task_id: str | None) -> None:
    """Best-effort revoke of a Celery task. Safe to call with None."""
    if not task_id:
        return
    try:
        _celery.control.revoke(task_id, terminate=True)
    except Exception:
        pass


class ScanService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Quota ─────────────────────────────────────────────────────────────────

    def _enforce_quota(self, organization_id: str) -> None:
        """
        Free-plan quota — enforced on every submit. Two limits:
          • Active scans (queued|running) cannot exceed FREE_PLAN_ACTIVE_LIMIT.
          • Scans created in the last 24 h cannot exceed FREE_PLAN_DAILY_LIMIT.
        Both keep an attacker (or a buggy frontend) from bypassing the UI cap
        by hitting the API directly.

        Implemented as a single query with conditional aggregation so submit
        only pays one round-trip to MySQL.
        """
        since = datetime.now(tz=timezone.utc) - timedelta(hours=24)
        active_count, daily_count = self.db.query(
            func.coalesce(
                func.sum(case((ScanJob.status.in_(("queued", "running")), 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((ScanJob.created_at >= since, 1), else_=0)),
                0,
            ),
        ).filter(
            ScanJob.organization_id == organization_id,
            ScanJob.deleted_at.is_(None),
        ).one()

        if (active_count or 0) >= FREE_PLAN_ACTIVE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Active scan limit reached ({FREE_PLAN_ACTIVE_LIMIT}). "
                    "Wait for a running scan to finish or cancel one."
                ),
            )
        if (daily_count or 0) >= FREE_PLAN_DAILY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Daily scan limit reached ({FREE_PLAN_DAILY_LIMIT}/24h). "
                    "Try again later."
                ),
            )

    # ── Submit ─────────────────────────────────────────────────────────────────

    def submit_git_scan(
        self,
        organization_id: str,
        user_id: str,
        body: SubmitGitScanRequest,
    ) -> ScanJob:
        self._enforce_quota(organization_id)

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
        self.db.commit()
        self.db.refresh(job)  # populate server-side defaults (timestamps, etc.)

        task = _celery.send_task(
            "scan_worker.tasks.sast.run_sast_scan",
            args=[job.id],
            queue="sast",
        )
        job.celery_task_id = task.id
        self.db.commit()
        # No second refresh — `expire_on_commit=False` keeps `job` populated and
        # we just assigned celery_task_id locally.
        return job

    async def submit_upload_scan(
        self,
        organization_id: str,
        user_id: str,
        name: str,
        file: UploadFile,
    ) -> ScanJob:
        self._enforce_quota(organization_id)

        os.makedirs(SCAN_UPLOAD_DIR, exist_ok=True)

        file_id = str(uuid.uuid4())
        dest = os.path.join(SCAN_UPLOAD_DIR, f"{file_id}.zip")

        # Stream to disk in chunks. Reading the whole upload into memory would
        # let any caller burn `Content-Length` bytes of RAM in the API process;
        # streaming + an explicit size cap keeps the upload bounded.
        written = 0
        try:
            with open(dest, "wb") as fh:
                while True:
                    chunk = await file.read(_UPLOAD_CHUNK)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_UPLOAD_BYTES:
                        fh.close()
                        try:
                            os.remove(dest)
                        except OSError:
                            pass
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=(
                                f"Upload exceeds maximum size of "
                                f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MiB"
                            ),
                        )
                    fh.write(chunk)
        except HTTPException:
            raise
        except Exception:
            # Any other write failure: clean up the partial file before re-raising
            try:
                os.remove(dest)
            except OSError:
                pass
            raise

        if written == 0:
            try:
                os.remove(dest)
            except OSError:
                pass
            raise HTTPException(status_code=400, detail="Empty upload")

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
        self.db.commit()
        self.db.refresh(job)  # populate server-side defaults (timestamps, etc.)

        task = _celery.send_task(
            "scan_worker.tasks.sast.run_sast_scan",
            args=[job.id],
            queue="sast",
        )
        job.celery_task_id = task.id
        self.db.commit()
        return job

    # ── Submit DAST ────────────────────────────────────────────────────────────

    def submit_web_scan(
        self,
        organization_id: str,
        user_id: str,
        body: SubmitWebScanRequest,
    ) -> ScanJob:
        """
        Queue a DAST scan against a live web target. The profile (`passive` or
        `active`) is stored in `extra` and read by the worker — the row schema
        is otherwise identical to a SAST job, so the existing list/detail/
        cancel/delete endpoints keep working without changes.
        """
        self._enforce_quota(organization_id)

        job = ScanJob(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            created_by=user_id,
            name=body.name,
            scan_type="dast",
            status="queued",
            target_type="web_url",
            target_url=body.target_url,
            extra={
                "profile": body.profile,
                "discovery_mode": body.discovery_mode,
                "openapi_url": body.openapi_url,
                # Stored as a list; the runner translates to ZAP regex patterns
                # at scan time. Empty list means "no exclusions".
                "exclude_paths": list(body.exclude_paths or []),
            },
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        task = _celery.send_task(
            "scan_worker.tasks.dast.run_dast_scan",
            args=[job.id],
            queue="dast",
        )
        job.celery_task_id = task.id
        self.db.commit()
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

    def get_status_counts(self, organization_id: str) -> dict[str, int]:
        """
        One-query count of jobs per status for an organization.

        Replaces the previous frontend pattern of issuing three list() calls
        (one for the page + one each for queued/running counts), each of which
        triggered the full auth + org-privilege + org-resolve chain.
        """
        rows = (
            self.db.query(ScanJob.status, func.count(ScanJob.id))
            .filter(
                ScanJob.organization_id == organization_id,
                ScanJob.deleted_at.is_(None),
            )
            .group_by(ScanJob.status)
            .all()
        )
        counts = {s: 0 for s in ("queued", "running", "completed", "failed", "cancelled")}
        for st, n in rows:
            counts[st] = n
        counts["total"] = sum(counts.values())
        return counts

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

        # Severity counts are over ALL findings for this job (not the filtered
        # set) so the summary bar always reflects reality. Single GROUP BY
        # instead of five COUNTs.
        rows = (
            self.db.query(ScanFinding.severity, func.count(ScanFinding.id))
            .filter(ScanFinding.scan_job_id == job.id)
            .group_by(ScanFinding.severity)
            .all()
        )
        severity_counts: dict[str, int] = {sev: 0 for sev in ("critical", "high", "medium", "low", "info")}
        for sev, n in rows:
            severity_counts[sev] = n

        return total, items, severity_counts

    # ── Cancel ─────────────────────────────────────────────────────────────────

    def cancel_job(self, organization_id: str, job_id: str) -> ScanJob:
        job = self.get_job(organization_id, job_id)

        if job.status not in ("queued", "running"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel a job with status '{job.status}'",
            )

        _revoke_task(job.celery_task_id)

        job.status = "cancelled"
        job.completed_at = datetime.now(tz=timezone.utc)
        self.db.commit()
        return job

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_job(self, organization_id: str, job_id: str) -> None:
        job = self.get_job(organization_id, job_id)

        if job.status == "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a running scan. Cancel it first.",
            )

        # If the job is still queued, the Celery task is sitting in the broker.
        # Soft-deleting the row alone leaves the worker free to pick it up,
        # mark it running, and write findings to a "deleted" row. Revoke first.
        if job.status == "queued":
            _revoke_task(job.celery_task_id)
            job.status = "cancelled"
            job.completed_at = datetime.now(tz=timezone.utc)

        # Best-effort cleanup of the on-disk upload.
        if job.target_type == "upload" and job.target_path:
            try:
                os.remove(job.target_path)
            except OSError:
                pass

        job.deleted_at = datetime.now(tz=timezone.utc)
        self.db.commit()
