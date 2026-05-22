"""
GET /api/v1/auth/validate

Called by the cyberlog client at startup to verify its API key and resolve
the owning organization. Successful validation returns lightweight metadata
that the client can echo back in error messages ("Logging as Acme Corp …").
"""
from fastapi import APIRouter, Depends, Request

from ...schemas.log import ValidateResponse
from ...security.api_key_auth import AuthContext, require_api_key
from ...security.limiter.rate_limit import limiter
from ...security.limiter import settings

auth_router = APIRouter(prefix="/auth")


@auth_router.get("/validate", response_model=ValidateResponse)
@limiter.limit(settings.GET_AUTH_VALIDATE)
def validate(request: Request, ctx: AuthContext = Depends(require_api_key)) -> ValidateResponse:
    return ValidateResponse(
        org_id=ctx.org_id,
        key_id=ctx.key_id,
        key_name=ctx.key_name,
    )
