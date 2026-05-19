"""
Redis-backed cache for API key → organization lookups.

The plaintext key is hashed (SHA-256) before being used as a Redis key, so the
raw secret never appears in Redis.

Cached value is a small JSON object:
    {"key_id": "...", "org_id": "...", "key_name": "..."}

A negative cache entry (the literal string "__invalid__") is stored for the
same TTL so that bursts of requests using a bad key don't hammer the database.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading

from ..global_settings import (
    API_KEY_CACHE_PREFIX,
    API_KEY_CACHE_TTL,
    REDIS_URL,
)

log = logging.getLogger(__name__)

_INVALID_SENTINEL = "__invalid__"

_redis_client = None
_redis_lock   = threading.Lock()


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def _redis_key(plaintext: str) -> str:
    return f"{API_KEY_CACHE_PREFIX}{_hash_key(plaintext)}"


def _get_redis():
    """Lazy connect. Returns None when Redis is unavailable — callers fall back to DB."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    with _redis_lock:
        if _redis_client is not None:
            return _redis_client
        try:
            import redis as _redis
            client = _redis.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            client.ping()
            _redis_client = client
            log.info("API-key cache: Redis connected (%s)", REDIS_URL)
        except Exception as exc:
            log.warning(
                "API-key cache: Redis unavailable (%s). "
                "Each ingest call will hit the database directly.",
                exc,
            )
    return _redis_client


# ── Public API ────────────────────────────────────────────────────────────────

def get_cached(plaintext: str) -> dict | None | False:  # type: ignore[valid-type]
    """
    Return:
        * dict  — cached hit (valid key)
        * False — cached negative hit (the key was already proven invalid)
        * None  — cache miss; caller must check the database
    """
    r = _get_redis()
    if r is None:
        return None
    try:
        raw = r.get(_redis_key(plaintext))
    except Exception as exc:
        log.warning("API-key cache read failed (%s) — falling back to DB.", exc)
        return None

    if raw is None:
        return None
    if raw == _INVALID_SENTINEL:
        return False
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def set_cached(plaintext: str, value: dict) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.set(_redis_key(plaintext), json.dumps(value), ex=API_KEY_CACHE_TTL)
    except Exception as exc:
        log.warning("API-key cache write failed (%s).", exc)


def set_invalid(plaintext: str) -> None:
    """Cache a negative result so repeated bad keys don't hit the DB."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.set(_redis_key(plaintext), _INVALID_SENTINEL, ex=API_KEY_CACHE_TTL)
    except Exception as exc:
        log.warning("API-key cache write failed (%s).", exc)


def invalidate(plaintext: str) -> None:
    """Drop a key from cache (called when an API key is revoked)."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.delete(_redis_key(plaintext))
    except Exception as exc:
        log.warning("API-key cache delete failed (%s).", exc)
