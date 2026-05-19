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
from ..cyberlog_client import log

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
            log.warning(
                "Quota exceeded — active scan limit",
                org_id=organization_id,
                active_count=int(active_count or 0),
                limit=FREE_PLAN_ACTIVE_LIMIT,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Active scan limit reached ({FREE_PLAN_ACTIVE_LIMIT}). "
                    "Wait for a running scan to finish or cancel one."
                ),
            )
        if (daily_count or 0) >= FREE_PLAN_DAILY_LIMIT:
            log.warning(
                "Quota exceeded — daily scan limit",
                org_id=organization_id,
                daily_count=int(daily_count or 0),
                limit=FREE_PLAN_DAILY_LIMIT,
            )
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

        log.info(
            "Git scan queued",
            org_id=organization_id,
            scan_id=job.id,
            scan_type="sast",
            created_by=user_id,
            target=body.target_url,
        )
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

        log.info(
            "Upload scan queued",
            org_id=organization_id,
            scan_id=job.id,
            scan_type="sast",
            created_by=user_id,
            size_bytes=written,
        )
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

        # Credentials never go into `extra` (which is returned by the read
        # API). We only record the type so the UI can show "Authenticated as
        # bearer/form" on the detail view. The actual token/password is
        # passed through Celery args and discarded after the worker reads it.
        auth_type_label = body.auth.type if body.auth else None
        auth_payload = body.auth.model_dump(exclude_none=True) if body.auth else None

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
                # Display-only label. NEVER contains credentials.
                "auth_type": auth_type_label,
            },
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        # `kwargs` here goes into the broker message in Redis. Once the
        # worker acks the task and the message is removed from the queue,
        # the credentials are gone — they're never written to the result
        # backend (we don't return them from the task).
        task = _celery.send_task(
            "scan_worker.tasks.dast.run_dast_scan",
            args=[job.id],
            kwargs={"auth": auth_payload},
            queue="dast",
        )
        job.celery_task_id = task.id
        self.db.commit()

        log.info(
            "Web scan queued",
            org_id=organization_id,
            scan_id=job.id,
            scan_type="dast",
            created_by=user_id,
            target=body.target_url,
            profile=body.profile,
            auth_type=auth_type_label,
        )
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

    def get_org_summary(self, organization_id: str) -> dict:
        """
        One-query aggregate for the org dashboard overview tab.

        Returns severity counts across all findings for the org, status counts
        for all jobs, and the 8 most recent jobs — all in a single pass so the
        overview tab pays two DB round-trips (this + the privileges check that
        runs before routing) rather than N separate list/stats/findings calls.
        """
        # Severity distribution across every finding recorded for this org
        sev_rows = (
            self.db.query(ScanFinding.severity, func.count(ScanFinding.id))
            .join(ScanJob, ScanFinding.scan_job_id == ScanJob.id)
            .filter(
                ScanJob.organization_id == organization_id,
                ScanJob.deleted_at.is_(None),
            )
            .group_by(ScanFinding.severity)
            .all()
        )
        severity_counts: dict[str, int] = {s: 0 for s in ("critical", "high", "medium", "low", "info")}
        for sev, n in sev_rows:
            severity_counts[sev] = n

        # Per-status job counts (mirrors get_status_counts)
        status_rows = (
            self.db.query(ScanJob.status, func.count(ScanJob.id))
            .filter(
                ScanJob.organization_id == organization_id,
                ScanJob.deleted_at.is_(None),
            )
            .group_by(ScanJob.status)
            .all()
        )
        status_counts: dict[str, int] = {s: 0 for s in ("queued", "running", "completed", "failed", "cancelled")}
        for st, n in status_rows:
            status_counts[st] = n
        status_counts["total"] = sum(status_counts.values())

        # 8 most recent scans for the activity feed
        recent = (
            self.db.query(ScanJob)
            .filter(
                ScanJob.organization_id == organization_id,
                ScanJob.deleted_at.is_(None),
            )
            .order_by(ScanJob.created_at.desc())
            .limit(8)
            .all()
        )

        return {
            "severity_counts": severity_counts,
            "total_findings": sum(severity_counts.values()),
            "status_counts": status_counts,
            "recent_scans": recent,
        }

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

    # ── Export ─────────────────────────────────────────────────────────────────

    def export_findings(
        self,
        organization_id: str,
        job_id: str,
        fmt: str,
    ) -> tuple[str, str, str]:
        """
        Build a downloadable report for a scan.

        Returns `(content, content_type, filename)` so the router can stream
        it back without re-deriving any of those values.

        Supported formats:
          • json — structured dump of the job + all findings, suitable for
                   programmatic consumption / ingestion into other tools.
          • html — single-file HTML with inline CSS, ready to print to PDF
                   from the browser. We deliberately avoid a server-side
                   PDF library to keep the worker slim.
        """
        from datetime import datetime, timezone
        import html
        import json as _json

        fmt = (fmt or "json").lower()
        if fmt not in ("json", "html"):
            raise HTTPException(status_code=400, detail="format must be 'json' or 'html'")

        job = self.get_job(organization_id, job_id)
        findings = (
            self.db.query(ScanFinding)
            .filter(ScanFinding.scan_job_id == job.id)
            .order_by(ScanFinding.severity, ScanFinding.tool, ScanFinding.file_path)
            .all()
        )

        # Per-severity tally — derived here rather than re-queried so HTML
        # and JSON exports stay consistent with each other.
        sev_order = ("critical", "high", "medium", "low", "info")
        counts = {s: 0 for s in sev_order}
        for f in findings:
            if f.severity in counts:
                counts[f.severity] += 1

        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in (job.name or "scan"))[:64]
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")

        if fmt == "json":
            report = {
                "scan": {
                    "id": job.id,
                    "name": job.name,
                    "scan_type": job.scan_type,
                    "status": job.status,
                    "target_type": job.target_type,
                    "target_url": job.target_url,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "findings_count": job.findings_count,
                    "error_message": job.error_message,
                    "extra": job.extra,
                },
                "summary": {
                    "severity_counts": counts,
                    "total": sum(counts.values()),
                },
                "findings": [
                    {
                        "id": f.id,
                        "tool": f.tool,
                        "rule_id": f.rule_id,
                        "severity": f.severity,
                        "confidence": f.confidence,
                        "title": f.title,
                        "message": f.message,
                        "file_path": f.file_path,
                        "line_start": f.line_start,
                        "line_end": f.line_end,
                        "code_snippet": f.code_snippet,
                        "cwe": f.cwe,
                        "owasp": f.owasp,
                        "fingerprint": f.fingerprint,
                        "created_at": f.created_at.isoformat() if f.created_at else None,
                    }
                    for f in findings
                ],
                "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            }
            return (
                _json.dumps(report, indent=2, ensure_ascii=False),
                "application/json",
                f"cybercore-{safe_name}-{ts}.json",
            )

        # ── HTML ──────────────────────────────────────────────────────────────
        # Single-file report. No external assets — easy to email or print.
        # Severity colours match the dashboard's CSS palette.
        def esc(v: object) -> str:
            return html.escape("" if v is None else str(v))

        sev_color = {
            "critical": "#7C1D1D",
            "high":     "#C53030",
            "medium":   "#D69E2E",
            "low":      "#3182CE",
            "info":     "#8899AA",
        }

        rows = []
        for f in findings:
            sev = (f.severity or "info").lower()
            color = sev_color.get(sev, "#8899AA")
            rows.append(f"""
              <tr>
                <td><span class="sev" style="background:{color}">{esc(sev)}</span></td>
                <td><b>{esc(f.title)}</b><div class="rule">{esc(f.rule_id)}</div></td>
                <td class="mono break">{esc(f.file_path)}{f' :{f.line_start}' if f.line_start else ''}</td>
                <td class="msg">{esc(f.message)}</td>
                <td>{esc(f.cwe or '—')}</td>
              </tr>
            """)

        summary_chips = "".join(
            f'<span class="chip" style="background:{sev_color[s]}">{counts[s]} {s}</span>'
            for s in sev_order if counts[s] > 0
        ) or '<span class="chip" style="background:#3FA86F">No findings</span>'

        scan_meta = (
            f"<tr><th>Target</th><td class='mono break'>{esc(job.target_url) or '—'}</td></tr>"
            f"<tr><th>Type</th><td>{esc((job.scan_type or '').upper())}</td></tr>"
            f"<tr><th>Status</th><td>{esc(job.status)}</td></tr>"
            f"<tr><th>Started</th><td>{esc(job.started_at)}</td></tr>"
            f"<tr><th>Finished</th><td>{esc(job.completed_at)}</td></tr>"
        )
        if job.extra:
            for k in ("profile", "discovery_mode", "auth_type"):
                if job.extra.get(k):
                    scan_meta += f"<tr><th>{esc(k.replace('_', ' ').title())}</th><td>{esc(job.extra[k])}</td></tr>"

        html_doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>CyberCore Report — {esc(job.name)}</title>
<style>
  body {{ font: 14px/1.5 system-ui, -apple-system, sans-serif; color: #0A1628; max-width: 1100px; margin: 24px auto; padding: 0 24px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #8899AA; margin-bottom: 24px; }}
  .chip {{ display: inline-block; color: #fff; font-weight: 600; font-size: 12px; padding: 4px 10px; border-radius: 12px; margin-right: 6px; text-transform: capitalize; }}
  table.meta {{ border-collapse: collapse; margin-bottom: 28px; }}
  table.meta th {{ text-align: left; font-weight: 500; color: #4A6080; padding: 4px 12px 4px 0; width: 160px; vertical-align: top; }}
  table.meta td {{ padding: 4px 0; }}
  table.findings {{ width: 100%; border-collapse: collapse; }}
  table.findings th, table.findings td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #E6EEF6; vertical-align: top; }}
  table.findings th {{ background: #F4F8FC; font-weight: 600; font-size: 12px; text-transform: uppercase; color: #4A6080; }}
  .sev {{ display: inline-block; color: #fff; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; }}
  .rule {{ font: 11px/1.2 ui-monospace, monospace; color: #8899AA; margin-top: 2px; }}
  .mono {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12px; }}
  .break {{ word-break: break-all; }}
  .msg {{ font-size: 12.5px; color: #364B66; white-space: pre-wrap; max-width: 520px; }}
  .footer {{ margin-top: 32px; color: #8899AA; font-size: 12px; text-align: center; }}
</style>
</head><body>
<h1>{esc(job.name)}</h1>
<div class="sub">CyberCore security report · generated {esc(datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))}</div>

<div style="margin-bottom: 24px;">{summary_chips}</div>

<table class="meta">{scan_meta}</table>

<h2 style="font-size: 16px; margin: 0 0 12px;">Findings ({len(findings)})</h2>
<table class="findings">
  <thead><tr><th>Severity</th><th>Title</th><th>Location</th><th>Details</th><th>CWE</th></tr></thead>
  <tbody>{''.join(rows) or '<tr><td colspan="5" style="text-align:center; color:#3FA86F; padding:32px;">No findings — clean scan.</td></tr>'}</tbody>
</table>

<div class="footer">CyberCore · scan {esc(job.id)}</div>
</body></html>"""

        return (
            html_doc,
            "text/html; charset=utf-8",
            f"cybercore-{safe_name}-{ts}.html",
        )

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

        log.info("Scan cancelled", org_id=organization_id, scan_id=job_id)
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

        log.info("Scan deleted", org_id=organization_id, scan_id=job_id)
