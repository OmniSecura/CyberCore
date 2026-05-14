from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


# Allowed schemes for the user-supplied repository URL. We deliberately reject
# any other transport (ssh://, ext::, file://, scp-style …) — see the matching
# validator in the worker's git_utils.validate_git_url.
_ALLOWED_GIT_SCHEMES = ("http", "https", "git")
_ALLOWED_WEB_SCHEMES = ("http", "https")
_HOST_RE = re.compile(r"^[A-Za-z0-9.\-]{1,255}$")


def _is_private_or_local(hostname: str) -> bool:
    """
    True when the hostname is a literal IP that points at private/loopback/
    link-local space. DNS names get resolved later by the worker — this is
    just the cheap first-line check that catches `http://127.0.0.1`,
    `http://10.0.0.5`, etc. submitted by the client.
    """
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return hostname.lower() in ("localhost",)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


# ── Request schemas ────────────────────────────────────────────────────────────

class SubmitGitScanRequest(BaseModel):
    name: str
    target_url: str

    @field_validator("target_url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("target_url must not be empty")
        if v.startswith("-"):
            raise ValueError("target_url must not start with '-'")
        if any(ch.isspace() or ord(ch) < 0x20 for ch in v):
            raise ValueError("target_url must not contain whitespace or control characters")
        parsed = urlparse(v)
        scheme = (parsed.scheme or "").lower()
        if scheme not in _ALLOWED_GIT_SCHEMES:
            raise ValueError(
                f"Unsupported URL scheme '{parsed.scheme}'. "
                f"Allowed: {', '.join(_ALLOWED_GIT_SCHEMES)}"
            )
        if not parsed.hostname or not _HOST_RE.match(parsed.hostname):
            raise ValueError("target_url must include a valid hostname")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        if len(v) > 255:
            raise ValueError("name must be at most 255 characters")
        return v


# DAST profiles. `passive` is spider + passive analysis only — never sends
# attack payloads. `active` adds the active scanner (real XSS/SQLi/etc probes)
# and is gated on a higher privilege at the router layer.
DastProfile = Literal["passive", "active"]


class SubmitWebScanRequest(BaseModel):
    name: str
    target_url: str
    profile: DastProfile = "passive"

    @field_validator("target_url")
    @classmethod
    def url_ok(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("target_url must not be empty")
        if v.startswith("-"):
            raise ValueError("target_url must not start with '-'")
        if any(ch.isspace() or ord(ch) < 0x20 for ch in v):
            raise ValueError("target_url must not contain whitespace or control characters")
        parsed = urlparse(v)
        scheme = (parsed.scheme or "").lower()
        if scheme not in _ALLOWED_WEB_SCHEMES:
            raise ValueError(
                f"Unsupported URL scheme '{parsed.scheme}'. "
                f"Allowed: {', '.join(_ALLOWED_WEB_SCHEMES)}"
            )
        host = parsed.hostname or ""
        if not host or not _HOST_RE.match(host):
            raise ValueError("target_url must include a valid hostname")
        if _is_private_or_local(host):
            raise ValueError(
                "Cannot scan private, loopback, or link-local addresses. "
                "Use a publicly reachable URL."
            )
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        if len(v) > 255:
            raise ValueError("name must be at most 255 characters")
        return v


# ── Response schemas ───────────────────────────────────────────────────────────

class ScanFindingOut(BaseModel):
    id: str
    tool: str
    rule_id: str
    severity: str
    confidence: Optional[str]
    title: str
    message: str
    file_path: str
    line_start: Optional[int]
    line_end: Optional[int]
    code_snippet: Optional[str]
    cwe: Optional[str]
    owasp: Optional[str]
    fingerprint: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanJobOut(BaseModel):
    id: str
    organization_id: str
    created_by: str
    name: str
    scan_type: str
    status: str
    target_type: str
    target_url: Optional[str]
    target_path: Optional[str] = None
    celery_task_id: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    findings_count: int
    extra: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScanJobDetailOut(ScanJobOut):
    # NOTE: previously this declared `findings: list[ScanFindingOut] = []`,
    # which made Pydantic with `from_attributes=True` access `job.findings`
    # and trigger SQLAlchemy lazy-loading of every finding on each detail
    # request. The dashboard polls this endpoint every 3 s while a scan is
    # active and never uses the embedded list (it calls /findings separately),
    # so loading thousands of rows per poll was pure waste. The detail view
    # is now identical to the list view — clients should hit /findings.
    model_config = {"from_attributes": True}


class ScanJobListOut(BaseModel):
    total: int
    items: list[ScanJobOut]


class ScanStatusCountsOut(BaseModel):
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total: int = 0


class FindingsListOut(BaseModel):
    total: int
    items: list[ScanFindingOut]
    severity_counts: dict[str, int]
    # True when len(items) < total — UI uses this to show a "results truncated"
    # banner instead of silently misrepresenting per-tool counts.
    truncated: bool = False
