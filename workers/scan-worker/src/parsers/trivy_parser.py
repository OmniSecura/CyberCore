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
    "UNKNOWN":  "info",
    "INFO":     "info",
}


def parse(report: dict, source_dir: Path) -> list[dict[str, Any]]:
    """Convert a Trivy JSON report into normalised ScanFinding dicts.
    Handles both vulnerability results and IaC misconfigurations.
    """
    results = []

    for entry in report.get("Results", []):
        target = entry.get("Target", "")
        try:
            target_rel = str(Path(target).relative_to(source_dir))
        except (ValueError, TypeError):
            target_rel = target

        # ── Dependency vulnerabilities ────────────────────────────────────────
        for vuln in entry.get("Vulnerabilities") or []:
            vuln_id  = vuln.get("VulnerabilityID", "UNKNOWN")
            pkg      = vuln.get("PkgName", "")
            installed = vuln.get("InstalledVersion", "")
            fixed    = vuln.get("FixedVersion", "")
            sev      = _SEVERITY.get(vuln.get("Severity", "UNKNOWN").upper(), "medium")
            title    = vuln.get("Title") or f"{vuln_id} in {pkg}"
            desc     = vuln.get("Description", "")
            cwes     = vuln.get("CweIDs") or []

            msg = f"{pkg}@{installed} is affected by {vuln_id}."
            if fixed:
                msg += f" Fix: upgrade to {fixed}."
            if desc:
                msg += f" {desc[:300]}"

            fingerprint = hashlib.sha256(
                f"trivy:vuln:{vuln_id}:{pkg}:{installed}".encode()
            ).hexdigest()[:64]

            results.append({
                "id":           str(uuid.uuid4()),
                "tool":         "trivy",
                "rule_id":      vuln_id,
                "severity":     sev,
                "confidence":   "high",
                "title":        title,
                "message":      msg,
                "file_path":    target_rel,
                "line_start":   None,
                "line_end":     None,
                "code_snippet": None,
                "cwe":          cwes[0] if cwes else None,
                "owasp":        "A06:2021 – Vulnerable and Outdated Components",
                "fingerprint":  fingerprint,
            })

        # ── IaC misconfigurations ─────────────────────────────────────────────
        for misconf in entry.get("Misconfigurations") or []:
            if misconf.get("Status") != "FAIL":
                continue

            check_id   = misconf.get("ID", "UNKNOWN")
            sev        = _SEVERITY.get(misconf.get("Severity", "UNKNOWN").upper(), "medium")
            title      = misconf.get("Title", check_id)
            desc       = misconf.get("Description", "")
            msg        = misconf.get("Message") or desc
            resolution = misconf.get("Resolution", "")
            if resolution:
                msg += f" Resolution: {resolution}"

            cause      = misconf.get("CauseMetadata", {})
            line_start = cause.get("StartLine")
            line_end   = cause.get("EndLine")

            fingerprint = hashlib.sha256(
                f"trivy:misconf:{check_id}:{target_rel}:{line_start}".encode()
            ).hexdigest()[:64]

            results.append({
                "id":           str(uuid.uuid4()),
                "tool":         "trivy",
                "rule_id":      check_id,
                "severity":     sev,
                "confidence":   "high",
                "title":        title,
                "message":      msg,
                "file_path":    target_rel,
                "line_start":   line_start,
                "line_end":     line_end if line_end != line_start else None,
                "code_snippet": None,
                "cwe":          None,
                "owasp":        "A05:2021 – Security Misconfiguration",
                "fingerprint":  fingerprint,
            })

    return results
