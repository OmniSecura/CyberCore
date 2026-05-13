from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

_SEVERITY_MAP = {
    "HIGH":   "high",
    "MEDIUM": "medium",
    "LOW":    "low",
}

_CONFIDENCE_MAP = {
    "HIGH":   "high",
    "MEDIUM": "medium",
    "LOW":    "low",
}


def parse(report: dict, source_dir: Path) -> list[dict[str, Any]]:
    """
    Convert gosec JSON report into normalised ScanFinding dicts.
    """
    findings = []
    for issue in report.get("Issues", []):
        file_path = issue.get("file", "")
        try:
            file_path = str(Path(file_path).relative_to(source_dir))
        except ValueError:
            pass

        rule_id    = issue.get("rule_id", "UNKNOWN")
        details    = issue.get("details", "").strip()
        code       = issue.get("code", "").strip() or None
        cwe_info   = issue.get("cwe", {})
        cwe        = f"CWE-{cwe_info['id']}" if cwe_info.get("id") else None

        try:
            line = int(issue.get("line", 0)) or None
        except (ValueError, TypeError):
            line = None

        fingerprint = hashlib.sha256(
            f"gosec:{rule_id}:{file_path}:{line}:{details}".encode()
        ).hexdigest()[:64]

        findings.append({
            "id":           str(uuid.uuid4()),
            "tool":         "gosec",
            "rule_id":      rule_id,
            "severity":     _SEVERITY_MAP.get(issue.get("severity", "").upper(), "medium"),
            "confidence":   _CONFIDENCE_MAP.get(issue.get("confidence", "").upper()),
            "title":        details or rule_id,
            "message":      details,
            "file_path":    file_path,
            "line_start":   line,
            "line_end":     None,
            "code_snippet": code,
            "cwe":          cwe,
            "owasp":        None,
            "fingerprint":  fingerprint,
        })

    return findings
