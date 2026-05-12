from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

_SEVERITY_MAP = {
    "critical": "critical",
    "high":     "high",
    "moderate": "medium",
    "medium":   "medium",
    "low":      "low",
    "info":     "info",
}


def parse(report: dict, source_dir: Path) -> list[dict[str, Any]]:
    """
    Convert npm audit v2 JSON into normalised ScanFinding dicts.
    One finding per vulnerable package.
    """
    findings = []
    vulns = report.get("vulnerabilities", {})

    for pkg_name, vuln in vulns.items():
        severity  = _SEVERITY_MAP.get(vuln.get("severity", "low"), "low")
        via       = vuln.get("via", [])
        range_str = vuln.get("range", "")

        # Gather advisory info from the `via` list (direct advisories)
        advisories = [v for v in via if isinstance(v, dict)]
        advisory   = advisories[0] if advisories else {}

        vuln_id     = advisory.get("url", "").split("/")[-1] or pkg_name
        description = advisory.get("title", f"Vulnerable dependency: {pkg_name}")
        cwe_list    = advisory.get("cwe", [])
        cwe         = cwe_list[0] if cwe_list else None

        fix_info = vuln.get("fixAvailable")
        if isinstance(fix_info, dict):
            fix_note = f"Fix available: upgrade to {fix_info.get('name')} {fix_info.get('version')}"
        elif fix_info is True:
            fix_note = "Fix available via `npm audit fix`."
        else:
            fix_note = "No fix available yet. Consider an alternative package."

        fingerprint = hashlib.sha256(
            f"npm-audit:{pkg_name}:{range_str}:{vuln_id}".encode()
        ).hexdigest()[:64]

        findings.append({
            "id":           str(uuid.uuid4()),
            "tool":         "npm-audit",
            "rule_id":      vuln_id or pkg_name,
            "severity":     severity,
            "confidence":   "high",
            "title":        f"{pkg_name} ({range_str}) — {description}",
            "message":      f"{description}\n\nAffected range: {range_str}\n{fix_note}",
            "file_path":    "[dependency] package.json",
            "line_start":   None,
            "line_end":     None,
            "code_snippet": None,
            "cwe":          str(cwe)[:64] if cwe else None,
            "owasp":        "A06:2021 – Vulnerable and Outdated Components",
            "fingerprint":  fingerprint,
        })

    return findings
