import httpx
import os
from fastapi import HTTPException, Request, Depends

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")

async def get_current_user(request: Request) -> dict:
    """
    Forward the cookie to auth-service /me and return the user dict.
    Raises 401 if the token is invalid or expired.
    """
    cookies = request.cookies

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/api/v1/users/me",
            cookies=cookies,
            timeout=5.0,
        )

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not response.is_success:
        raise HTTPException(status_code=502, detail="Auth service unavailable")

    return response.json()  # { id, email, full_name, ... }
