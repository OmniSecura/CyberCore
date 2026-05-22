"""
Dashboard-facing endpoints for reading logs.

Auth model (placeholder): the caller supplies the active org_id via the
`X-Org-Id` header. In production this should be wrapped behind the same
JWT-issued cookie flow used by auth-service; once that middleware is shared
across services, swap _resolve_org() for the real dependency.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...schemas.log import LogListResponse, LogResponse
from ...security.limiter.rate_limit import limiter
from ...security.limiter import settings
from ...services.log_service import LogService

logs_router = APIRouter(prefix="/logs")


def _resolve_org(x_org_id: str | None = Header(default=None)) -> str:
    if not x_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'X-Org-Id' header.",
        )
    return x_org_id


@logs_router.get("", response_model=LogListResponse)
@limiter.limit(settings.GET_LOGS)
def list_logs(
    request: Request,
    org_id: str = Depends(_resolve_org),
    project: str | None = Query(default=None),
    level: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> LogListResponse:
    svc = LogService(db)
    items, total = svc.list_logs(
        org_id=org_id,
        project=project,
        level=level,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    return LogListResponse(
        items=[LogResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )
