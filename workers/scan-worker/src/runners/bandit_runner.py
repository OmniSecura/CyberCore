from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# Bandit severity/confidence levels map to our normalized levels
_SEVERITY_MAP = {
    "HIGH":   "high",
    "MEDIUM": "medium",
    "LOW":    "low",
}

_CONFIDENCE_MAP = {
    "HIGH":   "high",
    "MEDIUM": "medium",
    "LOW":    "low",
}


def run(source_dir: Path) -> dict:
    """
    Run Bandit against source_dir and return the parsed JSON report.
    Raises RuntimeError if Bandit itself crashes (exit code 2+).
    Exit code 1 means issues were found — that is expected and not an error.
    """
    result = subprocess.run(
        [
            "bandit",
            "-r", str(source_dir),
            "-f", "json",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=300,
    )

    if result.returncode >= 2:
        raise RuntimeError(
            f"Bandit crashed (exit {result.returncode}): {result.stderr.strip()}"
        )

    raw = result.stdout.strip()
    if not raw:
        log.warning("Bandit produced no output")
        return {"results": [], "metrics": {}}

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Bandit output is not valid JSON: {exc}") from exc
