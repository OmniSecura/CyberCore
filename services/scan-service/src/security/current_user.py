import os

import httpx
from fastapi import Depends, HTTPException, Request

from .cache import cookie_key, user_cache
from .http_client import get_auth_service_client

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")


async def get_current_user(request: Request) -> dict:
    """Forward cookie to auth-service and return user dict.

    Result is cached per-cookie for SCAN_USER_CACHE_TTL_SECONDS (10s default)
    to keep the polling dashboard from hammering auth-service. Only successful
    lookups are cached — 401s/5xxs go through every time so a re-login picks
    up immediately.
    """
    key = cookie_key(request.cookies)
    cached = user_cache.get(key)
    if cached is not None:
        return cached

    client = get_auth_service_client()
    try:
        resp = await client.get(
            f"{AUTH_SERVICE_URL}/api/v1/users/me",
            cookies=request.cookies,
            timeout=5.0,
        )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Auth service unavailable")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not resp.is_success:
        raise HTTPException(status_code=502, detail="Auth service unavailable")

    data = resp.json()
    user_cache.set(key, data)
    return data


async def get_current_user_id(user: dict = Depends(get_current_user)) -> str:
    return user["id"]
