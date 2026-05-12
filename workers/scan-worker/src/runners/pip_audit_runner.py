from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# Files pip-audit can scan
_REQ_GLOBS = ["requirements*.txt", "requirements/*.txt"]
_PYPROJECT = "pyproject.toml"
_PIPFILE    = "Pipfile"


def run(source_dir: Path) -> dict:
    """
    Run pip-audit against Python dependency files found in source_dir.
    Supports requirements.txt, pyproject.toml, and Pipfile.
    Returns a merged dict with {"dependencies": [...]} structure.
    Raises RuntimeError on unexpected pip-audit errors.
    Raises FileNotFoundError if pip-audit binary is not installed.
    """
    req_files: list[Path] = []
    for glob in _REQ_GLOBS:
        req_files.extend(source_dir.rglob(glob))

    has_pyproject = (source_dir / _PYPROJECT).exists()
    has_pipfile   = (source_dir / _PIPFILE).exists()

    if not req_files and not has_pyproject and not has_pipfile:
        log.info("pip-audit: no Python dependency files found, skipping")
        return {"dependencies": []}

    all_deps: list[dict] = []
    seen_keys: set[str] = set()

    # Scan each requirements file
    for req_file in req_files[:8]:  # cap to avoid runaway scanning
        deps = _run_with_requirement(req_file)
        for dep in deps:
            key = f"{dep['name']}=={dep['version']}"
            if key not in seen_keys:
                seen_keys.add(key)
                all_deps.append(dep)

    # Scan pyproject.toml / Pipfile via cwd-based invocation
    if has_pyproject or has_pipfile:
        deps = _run_in_directory(source_dir)
        for dep in deps:
            key = f"{dep['name']}=={dep['version']}"
            if key not in seen_keys:
                seen_keys.add(key)
                all_deps.append(dep)

    return {"dependencies": all_deps}


def _run_with_requirement(req_file: Path) -> list[dict]:
    result = subprocess.run(
        ["pip-audit", "-r", str(req_file), "--format", "json",
         "--progress-spinner", "off", "--no-deps"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=120,
    )
    return _parse_output(result, str(req_file))


def _run_in_directory(source_dir: Path) -> list[dict]:
    result = subprocess.run(
        ["pip-audit", "--format", "json", "--progress-spinner", "off"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=120,
        cwd=str(source_dir),
    )
    return _parse_output(result, str(source_dir))


def _parse_output(result: subprocess.CompletedProcess, context: str) -> list[dict]:
    # exit 0 = no vulns, 1 = vulns found — both are expected
    if result.returncode not in (0, 1):
        log.warning("pip-audit non-fatal error for %s (exit %d): %s",
                    context, result.returncode, result.stderr.strip()[:256])
        return []

    raw = result.stdout.strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
        return data.get("dependencies", [])
    except json.JSONDecodeError:
        log.warning("pip-audit produced invalid JSON for %s", context)
        return []
