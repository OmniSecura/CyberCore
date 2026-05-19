"""
Thin wrapper around the Redis list that buffers logs between log-service
and log-consumer.

Producer side (this module):  LPUSH cyberlog:queue '{json}'
Consumer side (log-consumer):  BRPOP cyberlog:queue
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Any

from ..global_settings import LOG_QUEUE_KEY, REDIS_URL

log = logging.getLogger(__name__)

_redis_client = None
_redis_lock   = threading.Lock()


def _get_redis():
    """Lazy connect. Returns None when Redis is unavailable."""
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
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            client.ping()
            _redis_client = client
            log.info("Log queue: Redis connected (%s)", REDIS_URL)
        except Exception as exc:
            log.warning("Log queue: Redis unavailable (%s).", exc)
    return _redis_client


def enqueue(entries: list[dict[str, Any]]) -> int:
    """
    Push a batch of entries onto the queue.

    Each entry is serialised to a single JSON string so the consumer can
    process them one-by-one with BRPOP. Returns the number of entries
    accepted (= len(entries) on success, 0 if Redis is down).
    """
    if not entries:
        return 0

    r = _get_redis()
    if r is None:
        return 0

    try:
        # LPUSH accepts multiple values in a single round trip.
        payloads = [json.dumps(e, default=str) for e in entries]
        r.lpush(LOG_QUEUE_KEY, *payloads)
        return len(entries)
    except Exception as exc:
        log.error("Log queue: enqueue failed (%s).", exc)
        return 0


def queue_depth() -> int | None:
    """Best-effort current length. Returns None if Redis is down."""
    r = _get_redis()
    if r is None:
        return None
    try:
        return r.llen(LOG_QUEUE_KEY)
    except Exception:
        return None
