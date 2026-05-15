from __future__ import annotations

import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form, Response, status
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...schemas.scan import (
    SubmitGitScanRequest,
    SubmitWebScanRequest,
    ScanJobOut,
    ScanJobDetailOut,
    ScanJobListOut,
    ScanStatusCountsOut,
    FindingsListOut,
)
from ...security.cache import org_id_cache
from ...security.http_client import get_org_service_client
from ...security.org_privilege import require_org_privilege
from ...security.current_user import get_current_user_id
from ...services.scan_service import ScanService

scan_router = APIRouter(prefix="/scans",tags=["Scans"])

ORG_SERVICE_URL = os.getenv("ORG_SERVICE_URL", "http://localhost:8081")


async def _resolve_org_id(slug: str, request: Request) -> str:
    """Resolve org slug → UUID via organization service.

    Cached for SCAN_ORG_ID_CACHE_TTL_SECONDS (5 min default) — slug→UUID
    mappings are essentially immutable. The cache is global (not cookie-keyed)
    because the response is the same regardless of caller. The privilege check
    that runs alongside this lookup is what enforces access; this function is
    pure name resolution.
    """
    cached = org_id_cache.get(slug)
    if cached is not None:
        return cached

    client = get_org_service_client()
    try:
        r = await client.get(
            f"{ORG_SERVICE_URL}/api/v1/organizations/{slug}",
            cookies=request.cookies,
            timeout=5.0,
        )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Organization service unavailable")
    if r.is_success:
        org_id = r.json()["id"]
        org_id_cache.set(slug, org_id)
        return org_id
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Organization not found")
    raise HTTPException(status_code=502, detail="Organization service unavailable")


def _svc(db: Session = Depends(get_db)) -> ScanService:
    return ScanService(db)


# ── Submit git scan ────────────────────────────────────────────────────────────

@scan_router.post(
    "/organizations/{slug}/scans/git",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScanJobOut,
)
async def submit_git_scan(
    slug: str,
    request: Request,
    body: SubmitGitScanRequest,
    user_id: str = Depends(get_current_user_id),
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.run"),
):
    org_id = await _resolve_org_id(slug, request)
    return svc.submit_git_scan(org_id, user_id, body)


# ── Submit web (DAST) scan ─────────────────────────────────────────────────────

@scan_router.post(
    "/organizations/{slug}/scans/web",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScanJobOut,
)
async def submit_web_scan(
    slug: str,
    request: Request,
    body: SubmitWebScanRequest,
    user_id: str = Depends(get_current_user_id),
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.run"),
):
    org_id = await _resolve_org_id(slug, request)
    return svc.submit_web_scan(org_id, user_id, body)


# ── Submit upload scan ─────────────────────────────────────────────────────────

@scan_router.post(
    "/organizations/{slug}/scans/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScanJobOut,
)
async def submit_upload_scan(
    slug: str,
    request: Request,
    name: str = Form(...),
    file: UploadFile = File(..., description="ZIP archive of the source code"),
    user_id: str = Depends(get_current_user_id),
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.run"),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip uploads are accepted")
    org_id = await _resolve_org_id(slug, request)
    return await svc.submit_upload_scan(org_id, user_id, name, file)


# ── List scans ─────────────────────────────────────────────────────────────────

@scan_router.get(
    "/organizations/{slug}/scans",
    response_model=ScanJobListOut,
)
async def list_scans(
    slug: str,
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.view"),
):
    org_id = await _resolve_org_id(slug, request)
    total, items = svc.list_jobs(org_id, offset, limit, status_filter)
    return ScanJobListOut(total=total, items=items)


# ── Stats (per-status counts) ──────────────────────────────────────────────────

@scan_router.get(
    "/organizations/{slug}/scans/stats",
    response_model=ScanStatusCountsOut,
)
async def scan_stats(
    slug: str,
    request: Request,
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.view"),
):
    org_id = await _resolve_org_id(slug, request)
    return ScanStatusCountsOut(**svc.get_status_counts(org_id))


# ── Get scan detail ────────────────────────────────────────────────────────────

@scan_router.get(
    "/organizations/{slug}/scans/{job_id}",
    response_model=ScanJobDetailOut,
)
async def get_scan(
    slug: str,
    job_id: str,
    request: Request,
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.view"),
):
    org_id = await _resolve_org_id(slug, request)
    return svc.get_job(org_id, job_id)


# ── List findings ──────────────────────────────────────────────────────────────

@scan_router.get(
    "/organizations/{slug}/scans/{job_id}/findings",
    response_model=FindingsListOut,
)
async def list_findings(
    slug: str,
    job_id: str,
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    severity: Optional[str] = Query(default=None),
    tool: Optional[str] = Query(default=None),
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.view"),
):
    org_id = await _resolve_org_id(slug, request)
    total, items, severity_counts = svc.list_findings(
        org_id, job_id, offset, limit, severity, tool
    )
    return FindingsListOut(
        total=total,
        items=items,
        severity_counts=severity_counts,
        truncated=(offset + len(items)) < total,
    )


# ── Export findings ────────────────────────────────────────────────────────────

@scan_router.get(
    "/organizations/{slug}/scans/{job_id}/export",
)
async def export_findings(
    slug: str,
    job_id: str,
    request: Request,
    format: str = Query(default="json", regex="^(json|html)$"),
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.view"),
):
    """
    Stream a JSON or HTML report of the scan back as a file download. The
    body is fully built server-side (no streaming or large queries) because
    even big scans rarely exceed a few MB once serialised.
    """
    org_id = await _resolve_org_id(slug, request)
    content, content_type, filename = svc.export_findings(org_id, job_id, format)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Cancel scan ────────────────────────────────────────────────────────────────

@scan_router.post(
    "/organizations/{slug}/scans/{job_id}/cancel",
    response_model=ScanJobOut,
)
async def cancel_scan(
    slug: str,
    job_id: str,
    request: Request,
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.manage"),
):
    org_id = await _resolve_org_id(slug, request)
    return svc.cancel_job(org_id, job_id)


# ── Delete scan ────────────────────────────────────────────────────────────────

@scan_router.delete(
    "/organizations/{slug}/scans/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_scan(
    slug: str,
    job_id: str,
    request: Request,
    svc: ScanService = Depends(_svc),
    _priv: None = require_org_privilege("scans.manage"),
):
    org_id = await _resolve_org_id(slug, request)
    svc.delete_job(org_id, job_id)
