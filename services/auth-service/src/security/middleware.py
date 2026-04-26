import jwt
import os
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .token_blacklist import is_blacklisted

ALGORITHM       = "HS256"
JWT_SECRET_KEY  = os.getenv("JWT_SECRET_KEY", "")
_ACCESS_COOKIE  = "access_token"
_REFRESH_COOKIE = "refresh_token"

# Endpoints that never need a valid access token
_PUBLIC_PATHS = {
    "/v1/users/login",
    "/v1/users/register",
    "/v1/users/refresh",
    "/v1/email/verify",
    "/v1/email/reset-password/request",
    "/v1/email/reset-password/confirm",
    "/health",
    "/docs",
    "/openapi.json",
    "/",
}



class AutoRefreshMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically refreshes the access token when it is
    expired or close to expiry, as long as a valid refresh token cookie
    is present.

    Flow per request:
        1. If the path is public — pass through immediately.
        2. Read the access token cookie.
        3. If the access token is still valid — pass through.
        4. If the access token is missing or expired — read the refresh token cookie.
        5. Validate the refresh token (signature, expiry, blacklist).
        6. Issue a new access token and write it into the response cookie.
        7. Continue the request with the new token visible in request.cookies.

    This means the client (browser) never has to manually call /refresh —
    the server handles rotation transparently on every request.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        access_token = request.cookies.get(_ACCESS_COOKIE)

        if access_token and self._is_valid_access_token(access_token):
            return await call_next(request)

        # Access token missing or expired — try refresh token
        refresh_token = request.cookies.get(_REFRESH_COOKIE)
        if not refresh_token:
            return await call_next(request)  # let the endpoint handle 401

        user_id = self._validate_refresh_token(refresh_token)
        if not user_id:
            return await call_next(request)  # let the endpoint handle 401

        # Issue new access token
        from .JWT import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
        new_access_token = create_access_token(user_id)

        # Inject the new token into the request scope so the endpoint sees it
        scope = request.scope
        cookies = dict(request.cookies)
        cookies[_ACCESS_COOKIE] = new_access_token

        # Rebuild the cookie header with the new token
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        headers = list(scope.get("headers", []))
        headers = [(k, v) for k, v in headers if k != b"cookie"]
        headers.append((b"cookie", cookie_header.encode()))
        scope["headers"] = headers

        response = await call_next(request)

        # Write the new access token cookie into the response
        response.set_cookie(
            key=_ACCESS_COOKIE,
            value=new_access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
        return response

    def _is_valid_access_token(self, token: str) -> bool:
        """Return True if the token is signed, not expired, and not blacklisted."""
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"require": ["sub", "exp", "iat", "jti", "type"]},
            )
            if payload.get("type") != "access":
                return False
            jti = payload.get("jti")
            if not jti or is_blacklisted(jti):
                return False
            return True
        except jwt.PyJWTError:
            return False

    def _validate_refresh_token(self, token: str) -> str | None:
        """
        Validate the refresh token and return the user_id on success.
        Returns None if the token is invalid, expired, or blacklisted.
        """
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"require": ["sub", "exp", "iat", "jti", "type"]},
            )
            if payload.get("type") != "refresh":
                return None
            jti = payload.get("jti")
            if not jti or is_blacklisted(jti):
                return None
            return payload.get("sub")
        except jwt.PyJWTError:
            return None