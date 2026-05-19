from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


LogLevel = Literal["debug", "info", "warning", "error", "critical"]


class IngestLogEntry(BaseModel):
    """One log entry sent by the cyberlog client inside an ingest batch."""
    level: LogLevel
    message: str
    project: str
    timestamp: datetime
    fields: dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    """Body of POST /v1/ingest — a batch of log entries."""
    logs: list[IngestLogEntry]


class IngestResponse(BaseModel):
    accepted: int
    queue_depth: int | None = None


class LogResponse(BaseModel):
    """Single log entry returned to the dashboard."""
    id: str
    org_id: str
    project: str
    level: str
    message: str
    fields: dict[str, Any]
    timestamp: datetime
    ingested_at: datetime

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    items: list[LogResponse]
    total: int
    limit: int
    offset: int


class ValidateResponse(BaseModel):
    """Returned by GET /v1/auth/validate — used by the library at startup."""
    org_id: str
    key_id: str
    key_name: str
