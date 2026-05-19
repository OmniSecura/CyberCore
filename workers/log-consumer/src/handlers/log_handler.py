"""
Persists a batch of dequeued log entries into the `logs` table.

Each entry is a dict in the shape produced by log-service's ingest_router:
    {
        "org_id":    str,
        "project":   str,
        "level":     str,
        "message":   str,
        "timestamp": str (ISO-8601),
        "fields":   dict,
    }
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Iterable

from sqlalchemy import insert

from ..database.db_connection import db_session
from ..database.models.Log import Log

log = logging.getLogger(__name__)


def _parse_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.utcnow()
    try:
        # Python's fromisoformat handles the format produced by `datetime.isoformat()`.
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        log.warning("Bad timestamp '%s' — falling back to ingest time.", raw)
        return datetime.utcnow()


def persist_batch(entries: Iterable[dict]) -> int:
    """
    Bulk-insert a batch of validated entries. Returns the number of rows
    actually written. Bad rows are skipped (and logged); a single bad row
    never blocks the rest of the batch.
    """
    now  = datetime.utcnow()
    rows = []
    for raw in entries:
        try:
            rows.append({
                "id":          str(uuid.uuid4()),
                "org_id":      raw["org_id"],
                "project":     raw["project"],
                "level":       raw["level"],
                "message":     raw["message"],
                "fields":      raw.get("fields") or {},
                "timestamp":   _parse_timestamp(raw.get("timestamp")),
                "ingested_at": now,
            })
        except (KeyError, TypeError) as exc:
            log.warning("Dropping malformed log entry (%s): %r", exc, raw)

    if not rows:
        return 0

    with db_session() as db:
        db.execute(insert(Log), rows)

    return len(rows)
