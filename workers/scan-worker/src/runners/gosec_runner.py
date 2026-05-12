from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def run(source_dir: Path) -> dict:
    """
    Run gosec against all Go packages in source_dir.
    Returns the gosec JSON report dict with an "Issues" list.
    Exit code 0 = no issues, 1 = issues found (both are success).
    Raises RuntimeError on gosec internal errors.
    Raises FileNotFoundError if gosec binary is not installed.
    """
    result = subprocess.run(
        [
            "gosec",
            "-fmt", "json",
            "-quiet",
            "./...",
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=180,
        cwd=str(source_dir),
    )

    # Exit 0 = clean, 1 = issues, 2 = build errors (non-fatal)
    if result.returncode > 2:
        raise RuntimeError(
            f"gosec error (exit {result.returncode}): {result.stderr.strip()[:256]}"
        )

    raw = result.stdout.strip()
    if not raw:
        log.warning("gosec produced no output")
        return {"Issues": []}

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gosec output is not valid JSON: {exc}") from exc
