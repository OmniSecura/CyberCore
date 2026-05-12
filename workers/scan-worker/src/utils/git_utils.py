from __future__ import annotations

import logging
import os
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)


def _force_remove(func, path, exc_info):
    """onerror handler: strip read-only bit then retry (needed for .git objects on Windows)."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _rmtree(path: Path) -> None:
    shutil.rmtree(path, onerror=_force_remove)


def clone_repo(url: str, dest: Path, depth: int = 1) -> None:
    """Shallow-clone a public git repository into dest."""
    if dest.exists():
        _rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", "--depth", str(depth), "--single-branch", url, str(dest)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git clone failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    log.info("Cloned %s → %s", url, dest)


def extract_zip(zip_path: str | Path, dest: Path) -> None:
    """Extract a ZIP archive into dest."""
    if dest.exists():
        _rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)
    log.info("Extracted %s → %s", zip_path, dest)


def cleanup(path: Path) -> None:
    """Remove a workspace directory, best-effort."""
    try:
        _rmtree(path)
    except Exception:
        pass
