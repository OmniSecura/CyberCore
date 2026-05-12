import os

import httpx
from fastapi import Depends, HTTPException, Request

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")


async def get_current_user(request: Request) -> dict:
    """Forward cookie to auth-service and return user dict."""
    async with httpx.AsyncClient() as client:
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

    return resp.json()


async def get_current_user_id(user: dict = Depends(get_current_user)) -> str:
    return user["id"]
