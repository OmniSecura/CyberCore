from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def run(source_dir: Path) -> dict:
    """
    Run Trivy filesystem scan against source_dir.
    Covers dependency vulnerabilities (pip, npm, go, gem, cargo, …) and
    IaC misconfigurations (Dockerfile, Terraform, K8s, CloudFormation).
    Returns the Trivy JSON report dict with a "Results" list.
    Exit code 0 = clean, 1 = findings, 2+ = error.
    Raises FileNotFoundError if trivy binary is not installed.
    """
    result = subprocess.run(
        [
            "trivy", "fs",
            "--format", "json",
            "--quiet",
            "--no-progress",
            "--skip-dirs", ".git",
            str(source_dir),
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=300,
    )

    if result.returncode >= 2:
        raise RuntimeError(
            f"Trivy error (exit {result.returncode}): {result.stderr.strip()[:256]}"
        )

    raw = result.stdout.strip()
    if not raw:
        log.warning("trivy produced no output")
        return {"Results": []}

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Trivy output is not valid JSON: {exc}") from exc
