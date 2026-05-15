"""
ZAP alert → normalised finding dict.

Important schema-fit notes:

  • The shared ScanFinding row was designed for SAST and expects `file_path`
    to be set NOT NULL. For DAST we re-use that column as the request URL —
    it's still "where the problem lives". The `param`/`method`/`attack`/
    `evidence` fields don't have dedicated columns in v1; we fold them into
    `message` (for the human-readable description) so the existing UI shows
    them without a schema migration.

  • Fingerprint is rule_id : url : param : evidence so re-running the scan
    after a fix removes findings cleanly and an alert that fires on multiple
    parameters of one URL is counted as multiple findings (which it is).
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

# ZAP "risk" strings → our normalised severity set.
_RISK_TO_SEVERITY = {
    "high":          "high",
    "medium":        "medium",
    "low":           "low",
    "informational": "info",
    "info":          "info",
}

# ZAP "confidence" strings → matches the SAST `confidence` column values.
_CONFIDENCE = {
    "user confirmed": "high",
    "high":           "high",
    "medium":         "medium",
    "low":            "low",
    "false positive": "low",
}


def _build_message(alert: dict) -> str:
    """
    Glue together ZAP's structured fields into a single human-readable block.
    Order matches what an analyst usually reads first:
      description → method/param → attack payload → evidence snippet → solution.
    """
    parts: list[str] = []
    if desc := (alert.get("description") or "").strip():
        parts.append(desc)

    meta_bits: list[str] = []
    if method := (alert.get("method") or "").strip():
        meta_bits.append(f"Method: {method}")
    if param := (alert.get("param") or "").strip():
        meta_bits.append(f"Parameter: {param}")
    if meta_bits:
        parts.append("  •  ".join(meta_bits))

    if attack := (alert.get("attack") or "").strip():
        parts.append(f"Attack payload:\n{attack}")
    if evidence := (alert.get("evidence") or "").strip():
        parts.append(f"Evidence:\n{evidence}")
    if solution := (alert.get("solution") or "").strip():
        parts.append(f"Suggested fix:\n{solution}")
    return "\n\n".join(parts)


def _normalise_cwe(value: Any) -> str | None:
    if value in (None, "", 0, "0", "-1"):
        return None
    s = str(value).strip()
    if s.startswith("CWE-"):
        return s[:256]
    return f"CWE-{s}"[:256]


def parse(alerts: list[dict], _ctx: Any = None) -> list[dict[str, Any]]:
    """
    Convert ZAP `core/view/alerts` items into our normalised finding dicts.

    The `_ctx` second argument is a no-op kept for signature parity with the
    SAST parsers (which receive the source_dir). The DAST task can call the
    parser the same way without a special case.
    """
    findings: list[dict[str, Any]] = []
    for alert in alerts or []:
        rule_id = str(alert.get("pluginId") or alert.get("alertRef") or "zap-unknown")[:128]
        url     = (alert.get("url") or "").strip()
        param   = (alert.get("param") or "").strip()
        evidence = (alert.get("evidence") or "").strip()

        risk = (alert.get("risk") or "informational").strip().lower()
        severity = _RISK_TO_SEVERITY.get(risk, "info")

        confidence_raw = (alert.get("confidence") or "").strip().lower()
        confidence = _CONFIDENCE.get(confidence_raw)

        # Fingerprint dedups across re-runs and across alerts that ZAP emits
        # once per parameter-with-the-same-evidence.
        fp_input = f"{rule_id}:{url}:{param}:{evidence}"
        fingerprint = hashlib.sha256(fp_input.encode()).hexdigest()[:64]

        # The `name` field is the human-friendly alert title; ZAP also exposes
        # `alert` which is the same value in older versions.
        title = (alert.get("name") or alert.get("alert") or rule_id)[:1024]

        findings.append({
            "id": str(uuid.uuid4()),
            "tool": "zap",
            "rule_id": rule_id,
            "severity": severity,
            "confidence": confidence,
            "title": title,
            "message": _build_message(alert),
            # Re-use file_path as URL location — see module docstring.
            "file_path": url[:2048] or "(unknown URL)",
            "line_start": None,
            "line_end": None,
            "code_snippet": evidence or None,
            "cwe": _normalise_cwe(alert.get("cweid")),
            "owasp": None,
            "fingerprint": fingerprint,
        })
    return findings
