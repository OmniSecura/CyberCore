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

    # gosec exit codes: 0 = clean, 1 = issues found, 2 = Go build errors,
    # >2 = gosec internal failure. Treat 2 as a real error so the user sees
    # "couldn't compile your Go code" instead of a green "no findings" report
    # that just means gosec never ran.
    if result.returncode >= 2:
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
