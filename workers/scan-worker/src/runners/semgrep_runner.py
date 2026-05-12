from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# Default ruleset — security-focused, low false-positive rate
DEFAULT_CONFIG = "p/owasp-top-ten"


def run(source_dir: Path, config: str = DEFAULT_CONFIG) -> dict:
    """
    Run Semgrep against source_dir with the given config and return the JSON report.
    Raises RuntimeError on Semgrep internal errors (exit code 2+).
    Exit code 1 means findings — that is expected.
    """
    result = subprocess.run(
        [
            "semgrep",
            "--config", config,
            "--json",
            "--no-git-ignore",
            "--timeout", "60",
            str(source_dir),
        ],
        capture_output=True,
        text=True,
        timeout=360,
    )

    # Exit codes: 0 = clean, 1 = findings found, 2+ = error
    if result.returncode >= 2:
        raise RuntimeError(
            f"Semgrep error (exit {result.returncode}): {result.stderr.strip()}"
        )

    raw = result.stdout.strip()
    if not raw:
        log.warning("Semgrep produced no output")
        return {"results": []}

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Semgrep output is not valid JSON: {exc}") from exc
