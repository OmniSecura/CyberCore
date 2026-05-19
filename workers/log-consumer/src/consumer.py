"""
Long-running BRPOP loop that drains the `cyberlog:queue` Redis list into
the `logs` MySQL table.

Loop strategy:
    1. BRPOP for one entry (blocks up to BRPOP_TIMEOUT s).
    2. Drain whatever else is on the list with non-blocking RPOPs, up to
       BATCH_SIZE entries OR BATCH_TIMEOUT seconds.
    3. Bulk-insert the batch through `log_handler.persist_batch`.
    4. Repeat.

Why not Celery: one Celery task per log line burns broker round-trips
and serialiser CPU. BRPOP + batch insert is simpler and an order of
magnitude faster for this workload.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import time

import redis

from .database.db_connection import _connector
from .database.models.Base import Base
from .database.models.Log import Log  # noqa: F401  (registers the table)
from .global_settings import (
    BATCH_SIZE,
    BATCH_TIMEOUT,
    BRPOP_TIMEOUT,
    LOG_QUEUE_KEY,
    REDIS_URL,
)
from .handlers.log_handler import persist_batch

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("log-consumer")


# ── Graceful shutdown ─────────────────────────────────────────────────────────

_shutdown = False


def _handle_signal(signum, _frame) -> None:
    global _shutdown
    log.info("Received signal %s — finishing current batch then exiting.", signum)
    _shutdown = True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _connect_redis() -> redis.Redis:
    """Reconnect-with-backoff loop. Blocks until Redis is reachable."""
    delay = 1
    while not _shutdown:
        try:
            client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            client.ping()
            log.info("Connected to Redis at %s (queue=%s)", REDIS_URL, LOG_QUEUE_KEY)
            return client
        except Exception as exc:
            log.warning("Redis connect failed (%s) — retrying in %ss", exc, delay)
            time.sleep(delay)
            delay = min(delay * 2, 30)
    raise SystemExit(0)


def _ensure_tables() -> None:
    """Create the `logs` table if DB_CREATE_TABLES=true (matches log-service)."""
    if os.getenv("DB_CREATE_TABLES", "false").lower() != "true":
        return
    try:
        # Self-heal: create log_db itself if the init script never ran.
        # Idempotent and safe to run from both log-service and log-consumer.
        _connector.ensure_database_exists()
        Base.metadata.create_all(bind=_connector.get_engine())
        log.info("Verified log_db tables exist.")
    except Exception as exc:
        log.error("Could not create tables (%s). Continuing — log-service "
                  "may have created them already.", exc)


def _drain_until_full(r: redis.Redis, batch: list[dict], deadline: float) -> None:
    """Non-blocking RPOP until BATCH_SIZE or BATCH_TIMEOUT is reached."""
    while len(batch) < BATCH_SIZE and time.monotonic() < deadline:
        raw = r.rpop(LOG_QUEUE_KEY)
        if raw is None:
            return
        try:
            batch.append(json.loads(raw))
        except json.JSONDecodeError:
            log.warning("Dropping non-JSON entry from queue: %r", raw)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    _ensure_tables()
    r = _connect_redis()

    while not _shutdown:
        try:
            popped = r.brpop(LOG_QUEUE_KEY, timeout=BRPOP_TIMEOUT)
        except redis.exceptions.ConnectionError as exc:
            log.warning("Redis connection lost (%s) — reconnecting.", exc)
            r = _connect_redis()
            continue

        if popped is None:
            # Idle tick — gives the signal handler a chance to fire.
            continue

        _, raw = popped
        batch: list[dict] = []
        try:
            batch.append(json.loads(raw))
        except json.JSONDecodeError:
            log.warning("Dropping non-JSON entry from queue: %r", raw)

        # Fill the batch as much as we can within the deadline.
        deadline = time.monotonic() + BATCH_TIMEOUT
        try:
            _drain_until_full(r, batch, deadline)
        except redis.exceptions.ConnectionError as exc:
            log.warning("Redis drain failed (%s) — persisting what we have.", exc)

        if not batch:
            continue

        try:
            written = persist_batch(batch)
            log.info("Wrote %d log entries.", written)
        except Exception:
            # Catch-all so a single bad batch never kills the worker.
            log.exception("Failed to persist batch of %d entries.", len(batch))

    log.info("Log-consumer stopped cleanly.")


if __name__ == "__main__":
    main()
