from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any


def parse(findings: list[dict], source_dir: Path) -> list[dict[str, Any]]:
    """
    Convert Gitleaks secret-finding dicts into normalised ScanFinding dicts.
    The Match/Secret fields are already redacted by the --redact flag in the runner.
    """
    results = []
    for item in findings:
        file_path = item.get("File", "")
        try:
            file_path = str(Path(file_path).relative_to(source_dir))
        except ValueError:
            pass

        rule_id   = item.get("RuleID", "secret-detected")
        desc      = item.get("Description", rule_id.replace("-", " ").title())
        match     = item.get("Match", "")        # already redacted
        line      = item.get("StartLine")
        line_end  = item.get("EndLine")

        fingerprint = hashlib.sha256(
            f"gitleaks:{rule_id}:{file_path}:{line}".encode()
        ).hexdigest()[:64]

        results.append({
            "id":           str(uuid.uuid4()),
            "tool":         "gitleaks",
            "rule_id":      rule_id,
            "severity":     "high",
            "confidence":   "high",
            "title":        f"Exposed secret: {desc}",
            "message":      (
                f"Potential {desc} detected in {file_path}. "
                "Rotate this credential immediately and purge it from git history."
            ),
            "file_path":    file_path,
            "line_start":   line,
            "line_end":     line_end if line_end != line else None,
            "code_snippet": match or None,
            "cwe":          "CWE-798",
            "owasp":        "A07:2021 – Identification and Authentication Failures",
            "fingerprint":  fingerprint,
        })

    return results
