from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import urlparse

log = logging.getLogger(__name__)

# Only http(s) and git over TLS are accepted. This blocks dangerous git
# transports such as ext::, file://, ssh://, and any leading-dash flag-like
# value that would otherwise be parsed as a `git clone` option.
_ALLOWED_GIT_SCHEMES = ("http", "https", "git")
_HOST_RE = re.compile(r"^[A-Za-z0-9.\-]{1,255}$")


def _force_remove(func, path, exc_info):
    """onerror handler: strip read-only bit then retry (needed for .git objects on Windows)."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _rmtree(path: Path) -> None:
    shutil.rmtree(path, onerror=_force_remove)


def validate_git_url(url: str) -> str:
    """
    Validate a user-supplied git repository URL.

    Rejects anything that is not a plain http(s)/git URL with a sensible host —
    in particular `ext::`, `file://`, `ssh://`, scp-style `user@host:path`,
    leading-dash strings (which `git clone` would parse as an option), and
    embedded whitespace/control characters.

    Returns the cleaned URL on success; raises ValueError otherwise.
    """
    if not isinstance(url, str):
        raise ValueError("URL must be a string")
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("URL must not be empty")
    if cleaned.startswith("-"):
        raise ValueError("URL must not start with '-'")
    if any(ch.isspace() or ord(ch) < 0x20 for ch in cleaned):
        raise ValueError("URL must not contain whitespace or control characters")

    parsed = urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_GIT_SCHEMES:
        raise ValueError(
            f"Unsupported URL scheme '{parsed.scheme}'. "
            f"Allowed: {', '.join(_ALLOWED_GIT_SCHEMES)}"
        )
    if not parsed.hostname or not _HOST_RE.match(parsed.hostname):
        raise ValueError("URL must include a valid hostname")
    return cleaned


def clone_repo(url: str, dest: Path, depth: int = 1) -> None:
    """Shallow-clone a public git repository into dest."""
    safe_url = validate_git_url(url)
    if dest.exists():
        _rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # `--` separates options from positional args so that even a future bypass
    # of the URL validator cannot turn the URL into another git flag.
    env = dict(os.environ)
    env.setdefault("GIT_TERMINAL_PROMPT", "0")  # never block waiting on credentials
    result = subprocess.run(
        ["git", "clone", "--depth", str(depth), "--single-branch", "--", safe_url, str(dest)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git clone failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    log.info("Cloned %s → %s", safe_url, dest)


_DEFAULT_MAX_UNCOMPRESSED = int(
    os.getenv("SCAN_ZIP_MAX_UNCOMPRESSED_BYTES", str(5 * 1024 * 1024 * 1024))  # 5 GiB
)
_DEFAULT_MAX_ENTRIES = int(os.getenv("SCAN_ZIP_MAX_ENTRIES", "200000"))


def extract_zip(
    zip_path: str | Path,
    dest: Path,
    max_uncompressed_bytes: int = _DEFAULT_MAX_UNCOMPRESSED,
    max_entries: int = _DEFAULT_MAX_ENTRIES,
) -> None:
    """
    Extract a ZIP archive into ``dest`` with two defenses:

      • zip-slip — every entry is resolved against ``dest`` and rejected if it
        escapes the destination directory (absolute paths, leading "/", "..",
        or symlink-style traversal). Python's own zipfile.extractall sanitises
        most of this since 3.6.2 but we belt-and-brace it.
      • zip-bomb — both the uncompressed total size and the entry count are
        bounded. Limits configurable via SCAN_ZIP_MAX_UNCOMPRESSED_BYTES /
        SCAN_ZIP_MAX_ENTRIES.

    Raises RuntimeError on any violation; the caller (the SAST task) catches
    that and marks the job as failed.
    """
    if dest.exists():
        _rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()

    with zipfile.ZipFile(zip_path, "r") as zf:
        infos = zf.infolist()
        if len(infos) > max_entries:
            raise RuntimeError(
                f"ZIP rejected: too many entries ({len(infos)} > {max_entries})"
            )

        total_uncompressed = 0
        for info in infos:
            name = info.filename
            # Reject absolute paths and traversal at the string level first —
            # cheaper than resolving every entry, catches the obvious cases.
            if name.startswith(("/", "\\")) or any(
                part in ("..",) for part in Path(name).parts
            ):
                raise RuntimeError(f"ZIP rejected: unsafe entry path '{name}'")

            # Then verify the resolved target really lives inside dest.
            target = (dest / name).resolve()
            try:
                target.relative_to(dest_resolved)
            except ValueError:
                raise RuntimeError(f"ZIP rejected: entry escapes target '{name}'")

            total_uncompressed += info.file_size
            if total_uncompressed > max_uncompressed_bytes:
                raise RuntimeError(
                    f"ZIP rejected: uncompressed size exceeds "
                    f"{max_uncompressed_bytes} bytes"
                )

        zf.extractall(dest)

    log.info(
        "Extracted %s → %s (%d entries, %d bytes)",
        zip_path, dest, len(infos), total_uncompressed,
    )


def cleanup(path: Path) -> None:
    """Remove a workspace directory, best-effort."""
    try:
        _rmtree(path)
    except Exception:
        pass
