"""
POST /api/v1/ingest

The single endpoint consumed by the `cyberlog` Python client.
Authenticates the request via API key, validates the batch, and pushes
every entry onto the Redis queue. The actual DB write is performed
asynchronously by log-consumer.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...global_settings import MAX_BATCH_SIZE
from ...schemas.log import IngestRequest, IngestResponse
from ...security.api_key_auth import AuthContext, require_api_key
from ...security.limiter.rate_limit import limiter
from ...security.limiter import settings
from ...services import log_queue

ingest_router = APIRouter(prefix="/ingest")


@ingest_router.post(
    "",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(settings.POST_INGEST)
def ingest_logs(
    request: Request,
    payload: IngestRequest,
    ctx: AuthContext = Depends(require_api_key),
) -> IngestResponse:
    if not payload.logs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch must contain at least one log entry.",
        )

    if len(payload.logs) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch too large (max {MAX_BATCH_SIZE} entries per request).",
        )

    serialised = [
        {
            "org_id":    ctx.org_id,
            "level":     entry.level,
            "message":   entry.message,
            "project":   entry.project,
            "timestamp": entry.timestamp.isoformat(),
            "fields":    entry.fields,
        }
        for entry in payload.logs
    ]

    accepted = log_queue.enqueue(serialised)
    if accepted == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log queue temporarily unavailable. Please retry.",
        )

    return IngestResponse(
        accepted=accepted,
        queue_depth=log_queue.queue_depth(),
    )
