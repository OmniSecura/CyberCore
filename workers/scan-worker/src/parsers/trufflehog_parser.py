from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any


def parse(findings: list[dict], source_dir: Path) -> list[dict[str, Any]]:
    """Convert TruffleHog JSONL findings into normalised ScanFinding dicts."""
    results = []

    for item in findings:
        detector = item.get("DetectorName", "secret")
        verified = bool(item.get("Verified", False))
        redacted = item.get("Redacted") or item.get("Raw", "")

        # Extract file + line from SourceMetadata
        fs_meta   = item.get("SourceMetadata", {}).get("Data", {}).get("Filesystem", {})
        file_path = fs_meta.get("file", "")
        line      = fs_meta.get("line")

        try:
            file_path = str(Path(file_path).relative_to(source_dir))
        except (ValueError, TypeError):
            file_path = file_path.lstrip("/\\")

        sev            = "critical" if verified else "high"
        confidence     = "high"     if verified else "medium"
        verified_label = "verified active" if verified else "unverified"

        title   = f"Exposed {detector} credential ({verified_label})"
        message = (
            f"TruffleHog found a {verified_label} {detector} secret in {file_path or 'unknown file'}. "
            "Rotate this credential immediately and purge it from git history."
        )
        if verified:
            message += " This secret was confirmed active against the provider."

        fingerprint = hashlib.sha256(
            f"trufflehog:{detector}:{file_path}:{line}:{str(redacted)[:32]}".encode()
        ).hexdigest()[:64]

        results.append({
            "id":           str(uuid.uuid4()),
            "tool":         "trufflehog",
            "rule_id":      f"trufflehog-{detector.lower().replace(' ', '-')}",
            "severity":     sev,
            "confidence":   confidence,
            "title":        title,
            "message":      message,
            "file_path":    file_path,
            "line_start":   line,
            "line_end":     None,
            "code_snippet": str(redacted)[:200] if redacted else None,
            "cwe":          "CWE-798",
            "owasp":        "A07:2021 – Identification and Authentication Failures",
            "fingerprint":  fingerprint,
        })

    return results
