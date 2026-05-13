from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def run(source_dir: Path) -> list[dict]:
    """
    Run Hadolint against every Dockerfile found in source_dir.
    Returns a merged list of finding dicts.
    Exit code 0 = no issues, 1 = issues found (both expected).
    Raises FileNotFoundError if hadolint binary is not installed.
    """
    dockerfiles = [
        p for p in source_dir.rglob("*")
        if p.name.startswith("Dockerfile") or p.suffix.lower() == ".dockerfile"
    ]

    if not dockerfiles:
        log.info("hadolint: no Dockerfiles found, skipping")
        return []

    all_findings: list[dict] = []
    for dockerfile in dockerfiles[:16]:  # cap to avoid runaway
        all_findings.extend(_run_one(dockerfile))

    return all_findings


def _run_one(dockerfile: Path) -> list[dict]:
    result = subprocess.run(
        ["hadolint", "--format", "json", str(dockerfile)],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=30,
    )

    raw = result.stdout.strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        log.warning("hadolint produced invalid JSON for %s", dockerfile)
        return []
