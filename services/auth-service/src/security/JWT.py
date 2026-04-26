import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette import status

from ..database.db_connection import get_db
from ..database.models.User import User
from .token_blacklist import is_blacklisted

# ── Config ────────────────────────────────────────────────────────────────────

ALGORITHM                   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS   = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

_ACCESS_COOKIE  = "access_token"
_REFRESH_COOKIE = "refresh_token"

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY must be at least 32 characters long. "
        "Generate one with: openssl rand -hex 32"
    )

# ── Cookie helper ─────────────────────────────────────────────────────────────

def _set_cookie(response, key: str, value: str, max_age: int, path: str = "/") -> None:
    """
    Write a token into an httpOnly, Secure, SameSite=Lax cookie.

    httpOnly  — JavaScript cannot read it (blocks XSS token theft).
    Secure    — sent only over HTTPS.
    SameSite  — Lax blocks cross-site POST requests (CSRF protection).
    path      — limits which endpoints the browser sends the cookie to.
    """
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max_age,
        path=path,
    )


def _delete_cookie(response, key: str, path: str = "/") -> None:
    """Remove a cookie by setting its max_age to 0."""
    response.delete_cookie(key=key, path=path, httponly=True, secure=True, samesite="lax")


# ── Token creation ────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    """
    Build a short-lived access token and return the signed string.
    Caller is responsible for writing it into the response cookie.
    Expires in ACCESS_TOKEN_EXPIRE_MINUTES (default 15 min).
    """
    now    = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub":  user_id,
        "type": "access",
        "jti":  str(uuid.uuid4()),
        "iat":  now,
        "exp":  expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    Build a long-lived refresh token and return the signed string.
    Caller is responsible for writing it into the response cookie.
    Expires in REFRESH_TOKEN_EXPIRE_DAYS (default 7 days).
    """
    now    = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub":  user_id,
        "type": "refresh",
        "jti":  str(uuid.uuid4()),
        "iat":  now,
        "exp":  expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def set_auth_cookies(response, user_id: str) -> None:
    """
    Create both tokens and write them into the response cookies.

    Called after successful login or token refresh.
    Access token cookie is available site-wide (path="/").
    Refresh token cookie is restricted to the /users/refresh endpoint.
    """
    access_token  = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    _set_cookie(
        response,
        key=_ACCESS_COOKIE,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    _set_cookie(
        response,
        key=_REFRESH_COOKIE,
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/users/refresh",   # browser only sends this cookie to the refresh endpoint
    )


def clear_auth_cookies(response) -> None:
    """
    Remove both auth cookies from the browser.
    Called on logout and account deletion.
    """
    _delete_cookie(response, _ACCESS_COOKIE,  path="/")
    _delete_cookie(response, _REFRESH_COOKIE, path="/users/refresh")


# ── Token decoding ────────────────────────────────────────────────────────────

def _decode_token(token: str, expected_type: str) -> dict:
    """
    Verify signature, expiry, required claims, type claim, and blacklist.
    Raises 401 on any failure — error messages are kept generic on purpose
    so attackers learn nothing about why a token was rejected.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                "verify_exp": True,
                "verify_iat": True,
                "require": ["sub", "exp", "iat", "jti", "type"],
            },
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    jti = payload.get("jti")
    if not jti or is_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    return payload


def _get_jti_and_exp(token: str) -> Optional[tuple[str, int]]:
    """
    Extract (jti, exp) from a token without validating expiry.
    Used during logout to blacklist tokens that are near expiry.
    Returns None if the token cannot be decoded at all.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            return jti, exp
        return None
    except jwt.PyJWTError:
        return None


def blacklist_from_request_cookies(request: Request) -> None:
    """
    Read both tokens from the current request cookies and blacklist them.
    Called during logout and account deletion to immediately invalidate
    the session even before the tokens naturally expire.
    """
    from .token_blacklist import blacklist_token

    for cookie_name in (_ACCESS_COOKIE, _REFRESH_COOKIE):
        token = request.cookies.get(cookie_name)
        if token:
            result = _get_jti_and_exp(token)
            if result:
                jti, exp = result
                blacklist_token(jti, exp)


# ── FastAPI dependencies ──────────────────────────────────────────────────────

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extracts the access token from the cookie,
    validates it, and returns the active user.

    Raises 401 (always with the same generic 'Unauthorized' message) if:
        - No access token cookie is present
        - Token is invalid, expired, or blacklisted
        - User does not exist, is inactive, or is soft-deleted
        - Account is locked out
    """
    token = request.cookies.get(_ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    payload = _decode_token(token, expected_type="access")
    user_id = payload["sub"]

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active == True,
            User.deleted_at.is_(None),
        )
        .first()
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    return user


def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency — same as get_current_user but also requires is_superadmin.
    Returns 403 if the user is not a superadmin.
    """
    if not current_user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return current_user