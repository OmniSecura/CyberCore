"""
Dashboard-facing endpoints for managing organization API keys.

Same auth caveat as logs_router: the caller passes `X-Org-Id`; replace with
real JWT middleware once shared.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...schemas.api_key import (
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
)
from ...security.limiter.rate_limit import limiter
from ...security.limiter import settings
from ...services.api_key_service import ApiKeyService

api_keys_router = APIRouter(prefix="/api-keys")


def _resolve_org(x_org_id: str | None = Header(default=None)) -> str:
    if not x_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'X-Org-Id' header.",
        )
    return x_org_id


@api_keys_router.post(
    "",
    response_model=CreateApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.POST_API_KEYS)
def create_api_key(
    request: Request,
    payload: CreateApiKeyRequest,
    caller_org: str = Depends(_resolve_org),
    db: Session = Depends(get_db),
) -> CreateApiKeyResponse:
    if payload.org_id != caller_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="org_id in body does not match X-Org-Id header.",
        )

    svc = ApiKeyService(db)
    row, plaintext = svc.create(
        org_id=payload.org_id,
        name=payload.name,
        ttl_days=payload.ttl_days,
    )

    return CreateApiKeyResponse(
        id=row.id,
        org_id=row.org_id,
        name=row.name,
        key_prefix=row.key_prefix,
        is_active=row.is_active,
        last_used_at=row.last_used_at,
        created_at=row.created_at,
        expires_at=row.expires_at,
        plaintext_key=plaintext,
    )


@api_keys_router.get("", response_model=list[ApiKeyResponse])
@limiter.limit(settings.GET_API_KEYS)
def list_api_keys(
    request: Request,
    org_id: str = Depends(_resolve_org),
    db: Session = Depends(get_db),
) -> list[ApiKeyResponse]:
    svc = ApiKeyService(db)
    rows = svc.list_for_org(org_id)
    return [ApiKeyResponse.model_validate(r) for r in rows]


@api_keys_router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.DELETE_API_KEYS)
def revoke_api_key(
    request: Request,
    key_id: str,
    org_id: str = Depends(_resolve_org),
    db: Session = Depends(get_db),
) -> None:
    svc = ApiKeyService(db)
    row = svc.get(key_id)
    if row is None or row.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )
    svc.revoke(key_id)
