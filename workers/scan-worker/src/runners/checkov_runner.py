from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def run(source_dir: Path) -> dict:
    """
    Run Checkov against IaC files in source_dir.
    Covers Dockerfiles, Terraform, Kubernetes, CloudFormation, GitHub Actions, etc.
    Returns a merged dict with a "failed_checks" list.
    Exit code 0 = all passed, 1 = failed checks, 2+ = error.
    Raises FileNotFoundError if checkov binary is not installed.
    """
    result = subprocess.run(
        [
            "checkov",
            "-d", str(source_dir),
            "--output", "json",
            "--quiet",
            "--compact",
            "--skip-check", "CKV_GIT_1",  # skip git history checks (no git context)
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=300,
    )

    # 0 = passed, 1 = failed checks, 2+ = hard error
    if result.returncode >= 2:
        log.warning("checkov error (exit %d): %s", result.returncode, result.stderr.strip()[:256])
        return {"failed_checks": []}

    raw = result.stdout.strip()
    if not raw:
        return {"failed_checks": []}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("checkov produced invalid JSON")
        return {"failed_checks": []}

    # checkov returns a list when scanning multiple frameworks
    if isinstance(data, list):
        merged: list[dict] = []
        for entry in data:
            merged.extend(entry.get("results", {}).get("failed_checks", []))
        return {"failed_checks": merged}

    return {"failed_checks": data.get("results", {}).get("failed_checks", [])}
