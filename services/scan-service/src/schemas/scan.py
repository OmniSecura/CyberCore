from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, HttpUrl


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
