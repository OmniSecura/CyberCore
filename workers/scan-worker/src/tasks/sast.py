from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..celery_app import celery_app
from ..database.db_connection import db_session
from ..database.models.ScanJob import ScanJob
from ..database.models.ScanFinding import ScanFinding
from ..global_settings import SCAN_WORKSPACE_DIR
from ..runners import bandit_runner, semgrep_runner
from ..parsers import bandit_parser, semgrep_parser
from ..utils.git_utils import clone_repo, extract_zip, cleanup

log = logging.getLogger(__name__)


@celery_app.task(
    name="scan_worker.tasks.sast.run_sast_scan",
    bind=True,
    max_retries=0,       # SAST scans are expensive; don't retry automatically
    time_limit=600,      # hard kill at 10 min
    soft_time_limit=540, # SoftTimeLimitExceeded raised at 9 min so we can clean up
)
def run_sast_scan(self, job_id: str) -> dict:
    """
    Main SAST task.
    1. Load the ScanJob from DB.
    2. Prepare source code (clone or extract).
    3. Run Bandit + Semgrep.
    4. Parse & persist findings.
    5. Update job status to completed/failed.
    """
    workspace = Path(SCAN_WORKSPACE_DIR) / job_id

    try:
        with db_session() as db:
            job: ScanJob | None = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if not job:
                log.error("ScanJob %s not found — skipping", job_id)
                return {"status": "not_found"}

            if job.status == "cancelled":
                log.info("ScanJob %s was cancelled before worker picked it up", job_id)
                return {"status": "cancelled"}

            job.status = "running"
            job.started_at = datetime.now(tz=timezone.utc)
            db.flush()

        # ── Prepare source ─────────────────────────────────────────────────────
        source_dir = workspace / "source"

        with db_session() as db:
            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            target_type = job.target_type
            target_url = job.target_url
            target_path = job.target_path

        if target_type == "git_url":
            clone_repo(target_url, source_dir)
        elif target_type == "upload":
            extract_zip(target_path, source_dir)
        else:
            raise ValueError(f"Unknown target_type: {target_type!r}")

        # ── Run tools ──────────────────────────────────────────────────────────
        all_findings: list[dict] = []
        errors: list[str] = []

        try:
            bandit_report = bandit_runner.run(source_dir)
            all_findings.extend(bandit_parser.parse(bandit_report, source_dir))
            log.info("Bandit finished: %d findings", len(all_findings))
        except Exception as exc:
            log.warning("Bandit failed for job %s: %s", job_id, exc)
            errors.append(f"bandit: {exc}")

        try:
            semgrep_report = semgrep_runner.run(source_dir)
            semgrep_findings = semgrep_parser.parse(semgrep_report, source_dir)
            all_findings.extend(semgrep_findings)
            log.info("Semgrep finished: %d findings total", len(all_findings))
        except Exception as exc:
            log.warning("Semgrep failed for job %s: %s", job_id, exc)
            errors.append(f"semgrep: {exc}")

        # ── Dedup by fingerprint ───────────────────────────────────────────────
        seen: set[str] = set()
        unique_findings = []
        for f in all_findings:
            fp = f["fingerprint"]
            if fp not in seen:
                seen.add(fp)
                unique_findings.append(f)

        # ── Persist findings ───────────────────────────────────────────────────
        with db_session() as db:
            for f in unique_findings:
                db.add(ScanFinding(
                    id=f["id"],
                    scan_job_id=job_id,
                    tool=f["tool"],
                    rule_id=f["rule_id"],
                    severity=f["severity"],
                    confidence=f.get("confidence"),
                    title=f["title"],
                    message=f["message"],
                    file_path=f["file_path"],
                    line_start=f.get("line_start"),
                    line_end=f.get("line_end"),
                    code_snippet=f.get("code_snippet"),
                    cwe=f.get("cwe"),
                    owasp=f.get("owasp"),
                    fingerprint=f["fingerprint"],
                ))

            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            job.status = "completed"
            job.findings_count = len(unique_findings)
            job.completed_at = datetime.now(tz=timezone.utc)
            if errors:
                job.error_message = "; ".join(errors)

        return {"status": "completed", "findings": len(unique_findings)}

    except Exception as exc:
        log.exception("SAST task failed for job %s", job_id)
        try:
            with db_session() as db:
                job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)
                    job.completed_at = datetime.now(tz=timezone.utc)
        except Exception:
            pass
        raise

    finally:
        cleanup(workspace)
