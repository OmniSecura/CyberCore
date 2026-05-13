from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def run(source_dir: Path) -> dict:
    """
    Run `npm audit --json` against a Node.js project in source_dir.
    Requires package.json to be present; creates package-lock.json if missing.
    Returns the npm audit v2 JSON report dict.
    Raises RuntimeError on npm internal errors.
    Raises FileNotFoundError if npm binary is not installed.
    """
    pkg_json = source_dir / "package.json"
    if not pkg_json.exists():
        log.info("npm-audit: no package.json found, skipping")
        return {"vulnerabilities": {}, "metadata": {"vulnerabilities": {"total": 0}}}

    lock = source_dir / "package-lock.json"
    if not lock.exists():
        # Generate lock file without downloading node_modules
        log.info("npm-audit: generating package-lock.json (--package-lock-only)")
        install = subprocess.run(
            ["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-fund"],
            cwd=str(source_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if install.returncode != 0 or not lock.exists():
            # Without a lockfile, `npm audit` will report 0 findings but the
            # result is meaningless. Fail loudly so the job records an error
            # for this tool instead of silently passing.
            stderr = (install.stderr or "").strip()[:512]
            raise RuntimeError(
                f"npm install --package-lock-only failed (exit {install.returncode}): {stderr}"
            )

    result = subprocess.run(
        ["npm", "audit", "--json"],
        cwd=str(source_dir),
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=120,
    )

    # npm audit exit codes: 0=clean, 1=low/moderate, 2=high/critical, 8=not authed
    # All ≤ 7 are "successful audit runs" (may have findings)
    if result.returncode > 7:
        raise RuntimeError(
            f"npm audit error (exit {result.returncode}): {result.stderr.strip()[:256]}"
        )

    raw = result.stdout.strip()
    if not raw:
        log.warning("npm audit produced no output")
        return {"vulnerabilities": {}, "metadata": {"vulnerabilities": {"total": 0}}}

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"npm audit output is not valid JSON: {exc}") from exc
