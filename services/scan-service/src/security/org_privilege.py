"""
Privilege checker for cross-service use.

Usage in any router:

    from .security.org_privilege import require_org_privilege

    @router.post("/{slug}/scans")
    async def start_scan(
        slug: str,
        request: Request,
        _: None = Depends(require_org_privilege("scans.run")),
    ):
        ...
"""

import os
import httpx
from fastapi import Depends, HTTPException, Request, status

from .cache import cookie_key, priv_cache
from .http_client import get_org_service_client

ORG_SERVICE_URL = os.getenv("ORG_SERVICE_URL", "http://localhost:8081")


async def _fetch_privileges(slug: str, request: Request) -> frozenset[str]:
    """
    Resolve the set of privileges the current user holds in `slug`.

    Cached per (cookie, slug) for SCAN_PRIV_CACHE_TTL_SECONDS (10s default).
    A short TTL bounds the staleness window for revoked roles while still
    eliminating the vast majority of inter-service calls during polling.
    """
    cache_key = (cookie_key(request.cookies), slug)
    cached = priv_cache.get(cache_key)
    if cached is not None:
        return cached

    client = get_org_service_client()
    try:
        resp = await client.get(
            f"{ORG_SERVICE_URL}/api/v1/organizations/roles/{slug}/my-privileges",
            cookies=request.cookies,
            timeout=5.0,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Organization service unavailable",
        )

    if resp.status_code == 401:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    if resp.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    if not resp.is_success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Organization service error")

    privs = frozenset(resp.json().get("privileges", []))
    priv_cache.set(cache_key, privs)
    return privs


def require_org_privilege(privilege: str):
    """
    FastAPI dependency factory.
    Returns a dependency that raises 403 if the current user lacks `privilege`
    in the org identified by the `{slug}` path parameter.

    The slug MUST be a path parameter named `slug` in the same route.
    """
    async def _check(slug: str, request: Request) -> None:
        privs = await _fetch_privileges(slug, request)
        if privilege not in privs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing privilege: {privilege}",
            )

    return Depends(_check)
