"""
FastAPI dependency that authenticates ingest calls using a `ccl_*` API key.

Lookup order:
    1. Redis cache (positive or negative)
    2. Database (fallback)

The key is accepted in either header:
    Authorization: Bearer ccl_xxx
    X-Api-Key: ccl_xxx
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database.db_connection import get_db
from ..database.models.ApiKey import ApiKey
from . import api_key_cache


API_KEY_PREFIX = "ccl_"


@dataclass
class AuthContext:
    """What an authenticated ingest call carries forward."""
    org_id: str
    key_id: str
    key_name: str


def _extract_key(request: Request) -> str:
    """Pull the plaintext key out of the request headers (or raise 401)."""
    raw = request.headers.get("authorization", "")
    if raw.lower().startswith("bearer "):
        key = raw[7:].strip()
    else:
        key = request.headers.get("x-api-key", "").strip()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide it via 'Authorization: Bearer ccl_...' "
                   "or 'X-Api-Key' header.",
        )

    if not key.startswith(API_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid API key format (expected '{API_KEY_PREFIX}…' prefix).",
        )

    return key


def _hash_plaintext(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def require_api_key(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthContext:
    """FastAPI dependency. Returns AuthContext on success, raises 401 otherwise."""
    plaintext = _extract_key(request)

    # ── 1. Try Redis cache ────────────────────────────────────────────────────
    cached = api_key_cache.get_cached(plaintext)
    if cached is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )
    if cached:
        return AuthContext(
            org_id=cached["org_id"],
            key_id=cached["key_id"],
            key_name=cached["key_name"],
        )

    # ── 2. Fall back to the database ──────────────────────────────────────────
    key_hash = _hash_plaintext(plaintext)
    row: ApiKey | None = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        .first()
    )

    if row is None:
        api_key_cache.set_invalid(plaintext)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )

    # Reject expired keys. We negative-cache to avoid hammering the DB if the
    # client keeps retrying with the same dead key.
    if row.expires_at is not None and row.expires_at <= datetime.utcnow():
        api_key_cache.set_invalid(plaintext)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired. Generate a new one in the dashboard.",
        )

    # Best-effort usage tracking. Don't fail the request if this fails.
    try:
        row.last_used_at = datetime.utcnow()
        db.flush()
    except Exception:
        pass

    ctx_dict = {
        "key_id":   row.id,
        "org_id":   row.org_id,
        "key_name": row.name,
    }
    api_key_cache.set_cached(plaintext, ctx_dict)

    return AuthContext(
        org_id=row.org_id,
        key_id=row.id,
        key_name=row.name,
    )
