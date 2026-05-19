"""
Business logic for creating, listing, and revoking organization API keys.

Plaintext keys leave this module ONLY at creation time, inside the response
DTO. Everything persisted in the database is hashed.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..database.models.ApiKey import ApiKey
from ..security import api_key_cache

API_KEY_PREFIX = "ccl_"
# 32 URL-safe bytes ≈ 43 chars after base64. Combined with the prefix that
# gives ≈ 47-char tokens which are short enough for users to copy comfortably
# and long enough to make brute force pointless.
_RANDOM_BYTES = 32


def _generate_plaintext() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(_RANDOM_BYTES)}"


def _hash(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


class ApiKeyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        org_id: str,
        name: str,
        ttl_days: int | None = 365,
    ) -> tuple[ApiKey, str]:
        """
        Generate a new key, persist its hash, return (db_row, plaintext).

        `ttl_days`:
            * None or 0   → never expires (NULL in DB)
            * positive N  → key is rejected after now + N days

        The plaintext MUST be returned to the user immediately and never stored.
        """
        plaintext = _generate_plaintext()
        expires_at: datetime | None = None
        if ttl_days and ttl_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=ttl_days)

        row = ApiKey(
            org_id=org_id,
            name=name,
            key_hash=_hash(plaintext),
            key_prefix=plaintext[:12],
            expires_at=expires_at,
        )
        self.db.add(row)
        self.db.flush()
        return row, plaintext

    def list_for_org(self, org_id: str) -> list[ApiKey]:
        return (
            self.db.query(ApiKey)
            .filter(ApiKey.org_id == org_id)
            .order_by(ApiKey.created_at.desc())
            .all()
        )

    def get(self, key_id: str) -> ApiKey | None:
        return self.db.query(ApiKey).filter(ApiKey.id == key_id).first()

    def revoke(self, key_id: str) -> ApiKey | None:
        """
        Mark a key as inactive. We cannot drop it from the cache by plaintext
        (we don't have it) — but cache entries expire after API_KEY_CACHE_TTL,
        so revocation takes effect within that window.
        """
        row = self.get(key_id)
        if row is None:
            return None
        row.is_active = False
        self.db.flush()
        return row
