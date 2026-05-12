from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def run(source_dir: Path) -> list[dict]:
    """
    Run Gitleaks against source_dir scanning files directly (no git history).
    Returns a list of secret-finding dicts.
    Exit code 0 = no secrets, 1 = secrets found (both are success for us).
    Raises RuntimeError on Gitleaks internal errors (exit ≥ 2).
    Raises FileNotFoundError if gitleaks binary is not installed.
    """
    result = subprocess.run(
        [
            "gitleaks",
            "detect",
            "--source", str(source_dir),
            "--report-format", "json",
            "--report-path", "-",  # write JSON to stdout
            "--no-git",
            "--exit-code", "0",    # always exit 0 so we control error detection
            "--redact",            # redact actual secret values in output
            "--no-banner",
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=180,
    )

    if result.returncode >= 2:
        raise RuntimeError(
            f"Gitleaks error (exit {result.returncode}): {result.stderr.strip()}"
        )

    raw = result.stdout.strip()
    if not raw or raw == "null":
        return []

    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gitleaks output is not valid JSON: {exc}") from exc
