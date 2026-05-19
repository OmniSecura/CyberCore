"""
Query helpers for the dashboard side of the API.
Reads from `logs` table with org-scoped filtering.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ..database.models.Log import Log


class LogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_logs(
        self,
        org_id: str,
        *,
        project: str | None = None,
        level: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Log], int]:
        q = self.db.query(Log).filter(Log.org_id == org_id)

        if project:
            q = q.filter(Log.project == project)
        if level:
            q = q.filter(Log.level == level)
        if since:
            q = q.filter(Log.timestamp >= since)
        if until:
            q = q.filter(Log.timestamp <= until)

        total = q.count()
        items = (
            q.order_by(Log.timestamp.desc())
            .offset(offset)
            .limit(min(limit, 1000))
            .all()
        )
        return items, total
