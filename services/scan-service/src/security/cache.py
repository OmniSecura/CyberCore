"""
Tiny in-process TTL+LRU cache used to memoize the result of outbound calls
to auth-service and organization-service.

Why: every API request previously made up to three blocking inter-service HTTP
calls (auth `users/me`, org `slug -> uuid`, org `my-privileges`). With the
dashboard polling every 3 s while a scan is running, a single user with two
tabs open hammers those services dozens of times per minute. Caching the
results for a handful of seconds eliminates the vast majority of those calls
without meaningfully extending the window in which a logged-out cookie or a
revoked role is still accepted.

Trade-off: on logout, the user's cookie may continue to be accepted by this
service for up to USER_CACHE_TTL seconds (10s by default — short enough that
no real attack lives in that window, configurable via env if you disagree).
Privilege/role revocations have the same staleness.

The cache is process-local. With multiple Uvicorn workers each maintains its
own copy, which is fine — entries are tiny and TTLs are short.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections import OrderedDict
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")

USER_CACHE_TTL = float(os.getenv("SCAN_USER_CACHE_TTL_SECONDS", "10"))
PRIV_CACHE_TTL = float(os.getenv("SCAN_PRIV_CACHE_TTL_SECONDS", "10"))
# Slug → UUID mapping rarely changes; cache it longer.
ORG_ID_CACHE_TTL = float(os.getenv("SCAN_ORG_ID_CACHE_TTL_SECONDS", "300"))


class TTLCache(Generic[K, V]):
    """Bounded TTL+LRU cache. Not thread-safe in the strict sense but safe
    under the asyncio single-writer model FastAPI uses."""

    def __init__(self, ttl: float, max_size: int = 4096) -> None:
        self._ttl = ttl
        self._max = max_size
        self._store: "OrderedDict[K, tuple[float, V]]" = OrderedDict()

    def get(self, key: K) -> V | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires, value = item
        if expires < time.monotonic():
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: K, value: V) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)
        self._store.move_to_end(key)
        while len(self._store) > self._max:
            self._store.popitem(last=False)

    def invalidate(self, key: K) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


def cookie_key(cookies: dict[str, str]) -> str:
    """
    Deterministic, anonymous cache key built from the cookies that influence
    auth (we don't know which exact cookie name the auth service uses, so the
    full sorted bag is hashed). We hash so raw session tokens never sit in a
    Python dict.
    """
    if not cookies:
        return "anon"
    blob = "\x1f".join(f"{k}={v}" for k, v in sorted(cookies.items()))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# Module-level singletons. Imported by current_user / org_privilege / scan_router.
user_cache: TTLCache[str, dict] = TTLCache(USER_CACHE_TTL)
priv_cache: TTLCache[tuple[str, str], frozenset[str]] = TTLCache(PRIV_CACHE_TTL)
org_id_cache: TTLCache[str, str] = TTLCache(ORG_ID_CACHE_TTL)
