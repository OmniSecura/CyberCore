from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

_SEVERITY = {
    "CRITICAL": "critical",
    "HIGH":     "high",
    "MEDIUM":   "medium",
    "LOW":      "low",
    "INFO":     "info",
    "NONE":     "info",
}

_OWASP_BY_PREFIX: list[tuple[str, str]] = [
    ("CKV_DOCKER", "A05:2021 – Security Misconfiguration"),
    ("CKV_K8S",    "A05:2021 – Security Misconfiguration"),
    ("CKV_TF",     "A05:2021 – Security Misconfiguration"),
    ("CKV_AWS",    "A05:2021 – Security Misconfiguration"),
    ("CKV_GCP",    "A05:2021 – Security Misconfiguration"),
    ("CKV_AZURE",  "A05:2021 – Security Misconfiguration"),
    ("CKV2",       "A05:2021 – Security Misconfiguration"),
]


def _owasp(check_id: str) -> str:
    for prefix, cat in _OWASP_BY_PREFIX:
        if check_id.startswith(prefix):
            return cat
    return "A05:2021 – Security Misconfiguration"


def parse(report: dict, source_dir: Path) -> list[dict[str, Any]]:
    """Convert a Checkov JSON report into normalised ScanFinding dicts."""
    findings = []

    for check in report.get("failed_checks", []):
        check_id   = check.get("check_id", "UNKNOWN")
        check_meta = check.get("check", {})
        name       = check_meta.get("name") or check_id
        sev_raw    = (check_meta.get("severity") or "MEDIUM").upper()
        sev        = _SEVERITY.get(sev_raw, "medium")

        file_path = check.get("file_path", "")
        try:
            file_path = str(Path(file_path.lstrip("/\\")).relative_to(source_dir))
        except (ValueError, TypeError):
            file_path = file_path.lstrip("/\\")

        line_range = check.get("file_line_range") or [None, None]
        line_start = line_range[0] if line_range else None
        line_end   = line_range[1] if len(line_range) > 1 else None
        if line_end == line_start:
            line_end = None

        # code_block is [[line_no, "code\n"], ...]
        code_block = check.get("code_block") or []
        snippet = "".join(
            row[1] for row in code_block
            if isinstance(row, (list, tuple)) and len(row) > 1
        ).strip()[:500] or None

        resource = check.get("resource", "")
        message  = f"{name}"
        if resource:
            message += f" [{resource}]"

        fingerprint = hashlib.sha256(
            f"checkov:{check_id}:{file_path}:{line_start}".encode()
        ).hexdigest()[:64]

        findings.append({
            "id":           str(uuid.uuid4()),
            "tool":         "checkov",
            "rule_id":      check_id,
            "severity":     sev,
            "confidence":   "medium",
            "title":        name,
            "message":      message,
            "file_path":    file_path,
            "line_start":   line_start,
            "line_end":     line_end,
            "code_snippet": snippet,
            "cwe":          None,
            "owasp":        _owasp(check_id),
            "fingerprint":  fingerprint,
        })

    return findings
