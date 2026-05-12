from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

# Semgrep severity strings → our normalized levels
_SEVERITY = {
    "ERROR":   "high",
    "WARNING": "medium",
    "INFO":    "low",
    "HIGH":    "high",
    "MEDIUM":  "medium",
    "LOW":     "low",
    "CRITICAL": "critical",
}


def _extract_cwe(metadata: dict) -> str | None:
    cwe = metadata.get("cwe") or metadata.get("CWE")
    if isinstance(cwe, list):
        cwe = cwe[0] if cwe else None
    return str(cwe)[:256] if cwe else None


def _extract_owasp(metadata: dict) -> str | None:
    owasp = metadata.get("owasp") or metadata.get("OWASP")
    if isinstance(owasp, list):
        owasp = owasp[0] if owasp else None
    return str(owasp)[:64] if owasp else None


def parse(report: dict, source_dir: Path) -> list[dict[str, Any]]:
    """
    Convert a Semgrep JSON report into our normalised finding dicts.
    """
    findings = []
    for item in report.get("results", []):
        rule_id = item.get("check_id", "UNKNOWN")
        extra = item.get("extra", {})
        metadata = extra.get("metadata", {})

        sev_raw = (extra.get("severity") or metadata.get("severity") or "WARNING").upper()

        file_path = item.get("path", "")
        try:
            file_path = str(Path(file_path).relative_to(source_dir))
        except ValueError:
            pass

        start = item.get("start", {})
        end = item.get("end", {})
        snippet = extra.get("lines", "").strip() or None
        message = extra.get("message", "").strip()
        title = (
            metadata.get("name")
            or rule_id.split(".")[-1].replace("-", " ").replace("_", " ").title()
        )

        fingerprint = hashlib.sha256(
            f"{rule_id}:{file_path}:{start.get('line', 0)}:{message}".encode()
        ).hexdigest()[:64]

        findings.append({
            "id": str(uuid.uuid4()),
            "tool": "semgrep",
            "rule_id": rule_id,
            "severity": _SEVERITY.get(sev_raw, "medium"),
            "confidence": None,
            "title": title,
            "message": message,
            "file_path": file_path,
            "line_start": start.get("line"),
            "line_end": end.get("line"),
            "code_snippet": snippet,
            "cwe": _extract_cwe(metadata),
            "owasp": _extract_owasp(metadata),
            "fingerprint": fingerprint,
        })

    return findings
