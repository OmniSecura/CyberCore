from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any


def parse(report: dict, source_dir: Path) -> list[dict[str, Any]]:
    """
    Convert pip-audit JSON report into normalised ScanFinding dicts.
    One finding is emitted per (package, vulnerability) pair.
    """
    findings = []
    for dep in report.get("dependencies", []):
        name    = dep.get("name", "unknown")
        version = dep.get("version", "unknown")

        for vuln in dep.get("vulns", []):
            vuln_id     = vuln.get("id", "UNKNOWN")
            description = vuln.get("description", "").strip()
            fix_versions = vuln.get("fix_versions", [])
            fix_note = (
                f"Fix available in: {', '.join(fix_versions)}"
                if fix_versions else "No fix version available yet."
            )

            fingerprint = hashlib.sha256(
                f"pip-audit:{name}:{version}:{vuln_id}".encode()
            ).hexdigest()[:64]

            # Derive severity from CVSS prefix in vuln ID if present
            severity = _infer_severity(vuln_id, description)

            # CWE/OWASP from common advisory patterns
            cwe, owasp = _classify_vuln(description)

            findings.append({
                "id":           str(uuid.uuid4()),
                "tool":         "pip-audit",
                "rule_id":      vuln_id,
                "severity":     severity,
                "confidence":   "high",
                "title":        f"{name} {version} — {vuln_id}",
                "message":      (
                    f"{description}\n\n{fix_note}"
                    if description else fix_note
                ),
                "file_path":    f"[dependency] {name}=={version}",
                "line_start":   None,
                "line_end":     None,
                "code_snippet": None,
                "cwe":          cwe,
                "owasp":        owasp,
                "fingerprint":  fingerprint,
            })

    return findings


def _infer_severity(vuln_id: str, description: str) -> str:
    text = (vuln_id + " " + description).lower()
    if any(k in text for k in ("critical",)):
        return "critical"
    if any(k in text for k in ("high",)):
        return "high"
    if any(k in text for k in ("moderate", "medium")):
        return "medium"
    if any(k in text for k in ("low",)):
        return "low"
    # GHSA IDs default to medium; CVE IDs assume high unless we have CVSS
    return "medium"


def _classify_vuln(description: str) -> tuple[str | None, str | None]:
    d = description.lower()
    if any(k in d for k in ("sql injection", "sqli")):
        return "CWE-89", "A03:2021 – Injection"
    if any(k in d for k in ("xss", "cross-site scripting")):
        return "CWE-79", "A03:2021 – Injection"
    if any(k in d for k in ("path traversal", "directory traversal")):
        return "CWE-22", "A01:2021 – Broken Access Control"
    if any(k in d for k in ("rce", "remote code execution", "code execution")):
        return "CWE-94", "A03:2021 – Injection"
    if any(k in d for k in ("ssrf",)):
        return "CWE-918", "A10:2021 – Server-Side Request Forgery"
    if any(k in d for k in ("xxe",)):
        return "CWE-611", "A05:2021 – Security Misconfiguration"
    if any(k in d for k in ("deserialization",)):
        return "CWE-502", "A08:2021 – Software and Data Integrity Failures"
    if any(k in d for k in ("dos", "denial of service")):
        return "CWE-400", None
    if any(k in d for k in ("open redirect",)):
        return "CWE-601", "A01:2021 – Broken Access Control"
    return None, None
