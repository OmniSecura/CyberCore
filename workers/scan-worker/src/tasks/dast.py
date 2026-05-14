"""
DAST task — drives ZAP daemon against a live web target.

Mirrors the structure of `tasks/sast.py` so the two read the same way:
  1. load job + flip to running
  2. read profile from `extra`
  3. run ZAP runner with progress callback
  4. parse alerts → bulk-insert findings
  5. always cleanup the ZAP context in finally
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import insert

from ..celery_app import celery_app
from ..database.db_connection import db_session
from ..database.models.ScanJob import ScanJob
from ..database.models.ScanFinding import ScanFinding
from ..runners import zap_runner
from ..parsers import zap_parser

log = logging.getLogger(__name__)


def _make_progress_cb(job_id: str):
    """
    Return a callback that mirrors ZAP phase/percent into ScanJob.extra so the
    dashboard can show real-time progress. Errors writing to DB are swallowed
    — the scan must not fail because we couldn't update a progress field.
    """
    def cb(phase: str, percent: int) -> None:
        try:
            with db_session() as db:
                job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
                if not job:
                    return
                extra = dict(job.extra or {})
                extra["current_phase"] = phase
                extra["progress"] = percent
                job.extra = extra
        except Exception as exc:
            log.debug("Progress write failed (%s %d%%): %s", phase, percent, exc)
    return cb


@celery_app.task(
    name="scan_worker.tasks.dast.run_dast_scan",
    bind=True,
    max_retries=0,
    # Active scans can legitimately run for an hour. Hard kill after 75 min
    # so a wedged scan eventually frees the worker slot, soft kill ~73 min
    # earlier so the cleanup `finally` block has time to run.
    time_limit=75 * 60,
    soft_time_limit=73 * 60,
)
def run_dast_scan(self, job_id: str) -> dict:
    try:
        # ── Load job + flip to running ────────────────────────────────────────
        with db_session() as db:
            job: ScanJob | None = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if not job:
                log.error("ScanJob %s not found — skipping", job_id)
                return {"status": "not_found"}
            if job.status == "cancelled":
                log.info("ScanJob %s cancelled before pickup", job_id)
                return {"status": "cancelled"}
            if job.deleted_at is not None:
                log.info("ScanJob %s deleted before pickup", job_id)
                return {"status": "deleted"}

            job.status     = "running"
            job.started_at = datetime.now(tz=timezone.utc)

            target_url  = job.target_url or ""
            extra       = dict(job.extra or {})
            profile     = str(extra.get("profile") or "passive").lower()
            # Seed initial progress so the UI doesn't show a blank phase.
            extra["progress"] = 0
            extra["current_phase"] = "starting"
            job.extra = extra

        if not target_url:
            raise ValueError("DAST job has no target_url")

        context_name = f"job-{job_id}"

        # ── Run ZAP ───────────────────────────────────────────────────────────
        alerts = zap_runner.run(
            target_url=target_url,
            profile=profile,
            context_name=context_name,
            progress_cb=_make_progress_cb(job_id),
        )

        # ── Parse + dedup ─────────────────────────────────────────────────────
        findings = zap_parser.parse(alerts)
        seen: set[str] = set()
        unique: list[dict] = []
        for f in findings:
            fp = f["fingerprint"]
            if fp not in seen:
                seen.add(fp)
                unique.append(f)
        log.info(
            "DAST job %s — profile=%s, %d raw alerts → %d unique findings",
            job_id, profile, len(findings), len(unique),
        )

        # ── Persist ───────────────────────────────────────────────────────────
        # Same chunking strategy as SAST — keeps us well under MySQL's default
        # max_allowed_packet on big scans.
        BULK_CHUNK = 500
        with db_session() as db:
            if unique:
                rows = [
                    {
                        "id": f["id"],
                        "scan_job_id": job_id,
                        "tool": f["tool"],
                        "rule_id": f["rule_id"],
                        "severity": f["severity"],
                        "confidence": f.get("confidence"),
                        "title": f["title"],
                        "message": f["message"],
                        "file_path": f["file_path"],
                        "line_start": f.get("line_start"),
                        "line_end": f.get("line_end"),
                        "code_snippet": f.get("code_snippet"),
                        "cwe": f.get("cwe"),
                        "owasp": f.get("owasp"),
                        "fingerprint": f["fingerprint"],
                    }
                    for f in unique
                ]
                stmt = insert(ScanFinding)
                for i in range(0, len(rows), BULK_CHUNK):
                    db.execute(stmt, rows[i : i + BULK_CHUNK])

            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            job.status         = "completed"
            job.findings_count = len(unique)
            job.completed_at   = datetime.now(tz=timezone.utc)
            extra = dict(job.extra or {})
            extra["progress"] = 100
            extra["current_phase"] = "done"
            job.extra = extra

        return {"status": "completed", "findings": len(unique)}

    except Exception as exc:
        log.exception("DAST task failed for job %s", job_id)
        try:
            with db_session() as db:
                job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
                if job:
                    job.status        = "failed"
                    job.error_message = str(exc)
                    job.completed_at  = datetime.now(tz=timezone.utc)
        except Exception:
            pass
        raise
