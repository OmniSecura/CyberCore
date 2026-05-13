from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def run(source_dir: Path) -> list[dict]:
    """
    Run TruffleHog filesystem scan against source_dir.
    Outputs JSONL (one JSON object per line).
    Returns a list of secret-finding dicts (both verified and unverified).
    Raises FileNotFoundError if trufflehog binary is not installed.
    """
    result = subprocess.run(
        [
            "trufflehog",
            "filesystem",
            str(source_dir),
            "--json",
            "--no-update",
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=180,
    )

    # 0 = no findings, 183 = findings found, other non-zero = possible errors
    # We treat all exit codes as non-fatal since JSONL may still be valid
    if result.returncode not in (0, 183) and not result.stdout.strip():
        log.warning(
            "trufflehog exited %d with no output: %s",
            result.returncode, result.stderr.strip()[:256],
        )
        return []

    findings: list[dict] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return findings
