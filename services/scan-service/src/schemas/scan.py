from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator, HttpUrl


# Allowed schemes for the user-supplied repository URL. We deliberately reject
# any other transport (ssh://, ext::, file://, scp-style …) — see the matching
# validator in the worker's git_utils.validate_git_url.
_ALLOWED_GIT_SCHEMES = ("http", "https", "git")
_HOST_RE = re.compile(r"^[A-Za-z0-9.\-]{1,255}$")


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
    findings: list[ScanFindingOut] = []

    model_config = {"from_attributes": True}


class ScanJobListOut(BaseModel):
    total: int
    items: list[ScanJobOut]


class FindingsListOut(BaseModel):
    total: int
    items: list[ScanFindingOut]
    severity_counts: dict[str, int]
    # True when len(items) < total — UI uses this to show a "results truncated"
    # banner instead of silently misrepresenting per-tool counts.
    truncated: bool = False
