from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

_SEVERITY = {
    "error":   "high",
    "warning": "medium",
    "info":    "low",
    "style":   "info",
}

# Known DL codes that map to a CWE
_CWE: dict[str, str] = {
    "DL3002": "CWE-250",  # USER root
    "DL3003": "CWE-78",   # WORKDIR with cd
    "DL4006": "CWE-78",   # pipefail missing
}


def parse(findings: list[dict], source_dir: Path) -> list[dict[str, Any]]:
    """Convert Hadolint JSON findings into normalised ScanFinding dicts."""
    results = []
    for item in findings:
        code    = item.get("code", "UNKNOWN")
        level   = (item.get("level") or "warning").lower()
        sev     = _SEVERITY.get(level, "medium")
        message = item.get("message", code)

        file_path = item.get("file", "")
        try:
            file_path = str(Path(file_path).relative_to(source_dir))
        except (ValueError, TypeError):
            file_path = file_path.lstrip("/\\")

        line = item.get("line")

        fingerprint = hashlib.sha256(
            f"hadolint:{code}:{file_path}:{line}".encode()
        ).hexdigest()[:64]

        results.append({
            "id":           str(uuid.uuid4()),
            "tool":         "hadolint",
            "rule_id":      code,
            "severity":     sev,
            "confidence":   "high",
            "title":        f"Dockerfile lint: {code}",
            "message":      message,
            "file_path":    file_path,
            "line_start":   line,
            "line_end":     None,
            "code_snippet": None,
            "cwe":          _CWE.get(code),
            "owasp":        "A05:2021 – Security Misconfiguration",
            "fingerprint":  fingerprint,
        })

    return results
