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
from ..runners import (
    bandit_runner,
    semgrep_runner,
    gitleaks_runner,
    pip_audit_runner,
    npm_audit_runner,
    gosec_runner,
)
from ..parsers import (
    bandit_parser,
    semgrep_parser,
    gitleaks_parser,
    pip_audit_parser,
    npm_audit_parser,
    gosec_parser,
)
from ..utils.git_utils import clone_repo, extract_zip, cleanup

log = logging.getLogger(__name__)


def _has_ext(directory: Path, *extensions: str) -> bool:
    """Return True if any file with one of the given extensions exists in directory."""
    for ext in extensions:
        try:
            next(directory.rglob(f"*{ext}"))
            return True
        except StopIteration:
            continue
    return False


def _run_tool(name: str, runner_fn, parser_fn, *args) -> tuple[list[dict], str | None]:
    """
    Run a single tool, parse its output, and return (findings, error_or_none).
    Gracefully handles missing binaries (FileNotFoundError) and tool crashes.
    """
    try:
        raw = runner_fn(*args)
        findings = parser_fn(raw, args[-1])  # last positional arg is source_dir
        log.info("%s finished: %d finding(s)", name, len(findings))
        return findings, None
    except FileNotFoundError:
        log.info("%s not installed — skipping", name)
        return [], None
    except Exception as exc:
        log.warning("%s failed: %s", name, exc)
        return [], f"{name}: {exc}"


@celery_app.task(
    name="scan_worker.tasks.sast.run_sast_scan",
    bind=True,
    max_retries=0,
    time_limit=1800,       # hard kill at 30 min (more tools now)
    soft_time_limit=1740,  # graceful cleanup at 29 min
)
def run_sast_scan(self, job_id: str) -> dict:
    """
    Main SAST task. Runs all applicable security tools against the target code:

      Always:
        • Bandit     — Python static analysis
        • Semgrep    — Multi-language OWASP + language-specific rules (auto-detected)
        • Gitleaks   — Secret / credential detection

      Conditional (based on project type detection):
        • pip-audit  — Python dependency CVEs   (if requirements*.txt / pyproject.toml)
        • npm audit  — Node.js dependency CVEs  (if package.json)
        • gosec      — Go security analysis     (if *.go files)
    """
    workspace = Path(SCAN_WORKSPACE_DIR) / job_id

    try:
        # ── Load job ──────────────────────────────────────────────────────────
        with db_session() as db:
            job: ScanJob | None = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if not job:
                log.error("ScanJob %s not found — skipping", job_id)
                return {"status": "not_found"}

            if job.status == "cancelled":
                log.info("ScanJob %s was cancelled before worker picked it up", job_id)
                return {"status": "cancelled"}

            job.status     = "running"
            job.started_at = datetime.now(tz=timezone.utc)
            db.flush()

        # ── Prepare source ────────────────────────────────────────────────────
        source_dir = workspace / "source"

        with db_session() as db:
            job         = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            target_type = job.target_type
            target_url  = job.target_url
            target_path = job.target_path

        if target_type == "git_url":
            clone_repo(target_url, source_dir)
        elif target_type == "upload":
            extract_zip(target_path, source_dir)
        else:
            raise ValueError(f"Unknown target_type: {target_type!r}")

        # ── Detect project type ───────────────────────────────────────────────
        has_python   = _has_ext(source_dir, ".py", ".pyw")
        has_go       = _has_ext(source_dir, ".go")
        has_js_ts    = _has_ext(source_dir, ".js", ".ts", ".jsx", ".tsx", ".mjs")
        has_pkg_json = (source_dir / "package.json").exists()
        has_py_deps  = (
            bool(list(source_dir.rglob("requirements*.txt"))[:1])
            or (source_dir / "pyproject.toml").exists()
            or (source_dir / "Pipfile").exists()
        )

        log.info(
            "Project detection — python=%s go=%s js/ts=%s pkg.json=%s py-deps=%s",
            has_python, has_go, has_js_ts, has_pkg_json, has_py_deps,
        )

        # ── Run tools ─────────────────────────────────────────────────────────
        all_findings: list[dict] = []
        errors: list[str] = []

        def collect(name, runner_fn, parser_fn, *args):
            findings, err = _run_tool(name, runner_fn, parser_fn, *args)
            all_findings.extend(findings)
            if err:
                errors.append(err)

        # Bandit — Python (gracefully produces 0 findings on non-Python)
        collect("bandit",    bandit_runner.run,    bandit_parser.parse,    source_dir)

        # Semgrep — auto-detects languages, always runs OWASP + secrets rulesets
        collect("semgrep",   semgrep_runner.run,   semgrep_parser.parse,   source_dir)

        # Gitleaks — secrets in any language
        try:
            raw_secrets = gitleaks_runner.run(source_dir)
            secrets = gitleaks_parser.parse(raw_secrets, source_dir)
            all_findings.extend(secrets)
            log.info("gitleaks finished: %d finding(s)", len(secrets))
        except FileNotFoundError:
            log.info("gitleaks not installed — skipping")
        except Exception as exc:
            log.warning("gitleaks failed: %s", exc)
            errors.append(f"gitleaks: {exc}")

        # pip-audit — Python dependency CVEs
        if has_py_deps:
            collect("pip-audit", pip_audit_runner.run, pip_audit_parser.parse, source_dir)

        # npm audit — Node.js dependency CVEs
        if has_pkg_json:
            collect("npm-audit", npm_audit_runner.run, npm_audit_parser.parse, source_dir)

        # gosec — Go security
        if has_go:
            collect("gosec",    gosec_runner.run,    gosec_parser.parse,    source_dir)

        # ── Dedup by fingerprint ──────────────────────────────────────────────
        seen: set[str] = set()
        unique_findings: list[dict] = []
        for f in all_findings:
            fp = f["fingerprint"]
            if fp not in seen:
                seen.add(fp)
                unique_findings.append(f)

        log.info(
            "Dedup: %d raw → %d unique findings (tools: bandit, semgrep, gitleaks%s%s%s)",
            len(all_findings),
            len(unique_findings),
            ", pip-audit" if has_py_deps  else "",
            ", npm-audit" if has_pkg_json else "",
            ", gosec"     if has_go       else "",
        )

        # ── Persist ───────────────────────────────────────────────────────────
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
            job.status         = "completed"
            job.findings_count = len(unique_findings)
            job.completed_at   = datetime.now(tz=timezone.utc)
            if errors:
                job.error_message = "; ".join(errors)

        return {"status": "completed", "findings": len(unique_findings)}

    except Exception as exc:
        log.exception("SAST task failed for job %s", job_id)
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

    finally:
        cleanup(workspace)
