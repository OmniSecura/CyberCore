"""
Token blacklist — persisted in Redis so revocations survive auth-service restarts.

Each entry is stored as:
    SETEX  auth:bl:<jti>  <ttl_seconds>  "1"

Redis auto-expires the key when the token would naturally expire anyway, so the
blacklist never grows unboundedly and no manual cleanup is needed.

If Redis is unavailable the module falls back to an in-memory dict. Revocations
are still honoured within the lifetime of the running process; they are lost on
restart (which is the original behaviour). A warning is logged so operators know
to fix the Redis connection.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

# Use DB 1 to stay separate from Celery (which defaults to DB 0).
REDIS_URL  = os.getenv("REDIS_URL", "redis://localhost:6379/1")
_KEY_PREFIX = "auth:bl:"

# ── Lazy Redis client ─────────────────────────────────────────────────────────

_redis_client = None
_redis_lock   = threading.Lock()


def _get_redis():
    """
    Lazy-initialise and return a Redis client.
    Returns None if Redis is unreachable, so callers fall back to in-memory.
    Connection is attempted once; if it succeeds the client is reused forever.
    A failed attempt is retried on the next call (client stays None).
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    with _redis_lock:
        if _redis_client is not None:        # double-checked locking
            return _redis_client
        try:
            import redis as _redis
            client = _redis.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,    # fail fast on connect
                socket_timeout=1,            # fail fast on read/write
            )
            client.ping()
            _redis_client = client
            log.info("Token blacklist: Redis connected (%s)", REDIS_URL)
        except Exception as exc:
            log.warning(
                "Token blacklist: Redis unavailable (%s). "
                "Revocations will be lost on auth-service restart.",
                exc,
            )
    return _redis_client


# ── In-memory fallback ────────────────────────────────────────────────────────
# Used when Redis is down. Mirrors the original implementation.

_fallback: dict[str, int] = {}   # jti -> exp (Unix timestamp)
_fb_lock  = threading.Lock()


def _fb_add(jti: str, exp: int) -> None:
    with _fb_lock:
        _fallback[jti] = exp
        _fb_cleanup()


def _fb_has(jti: str) -> bool:
    with _fb_lock:
        return jti in _fallback


def _fb_cleanup() -> None:
    """Remove entries whose token has already naturally expired."""
    now = int(datetime.now(timezone.utc).timestamp())
    stale = [j for j, e in _fallback.items() if e < now]
    for j in stale:
        del _fallback[j]


# ── Public API ────────────────────────────────────────────────────────────────

def blacklist_token(jti: str, exp_timestamp: int) -> None:
    """
    Revoke a token immediately.

    The entry lives in Redis until the token's natural expiry (``exp``), after
    which Redis deletes it automatically — no background cleanup needed.
    """
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = max(exp_timestamp - now, 1)   # at least 1 second so SETEX never errors

    r = _get_redis()
    if r is not None:
        try:
            r.setex(f"{_KEY_PREFIX}{jti}", ttl, "1")
            return
        except Exception as exc:
            log.warning(
                "Token blacklist: Redis write failed (%s). Falling back to in-memory.", exc
            )

    _fb_add(jti, exp_timestamp)


def is_blacklisted(jti: str) -> bool:
    """Return True if the token has been explicitly revoked."""
    r = _get_redis()
    if r is not None:
        try:
            return bool(r.exists(f"{_KEY_PREFIX}{jti}"))
        except Exception as exc:
            log.warning(
                "Token blacklist: Redis read failed (%s). Checking in-memory fallback.", exc
            )

    return _fb_has(jti)
