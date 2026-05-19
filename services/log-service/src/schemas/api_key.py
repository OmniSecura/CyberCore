from datetime import datetime
from pydantic import BaseModel, Field


# Common TTL presets the dashboard exposes as radio buttons.
# Backend accepts any positive integer; these are just convenient values.
TTL_DAYS_PRESETS = [30, 90, 180, 365, 730]   # 1m / 3m / 6m / 1y / 2y


class CreateApiKeyRequest(BaseModel):
    org_id: str = Field(..., min_length=1, max_length=36)
    name: str = Field(..., min_length=1, max_length=120)

    # How many days the key is valid for. NULL or 0 = never expires.
    # Capped at ~10 years to prevent accidental "forever" keys.
    ttl_days: int | None = Field(default=365, ge=0, le=3650)


class ApiKeyResponse(BaseModel):
    """Metadata about a key — never includes the plaintext value."""
    id: str
    org_id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class CreateApiKeyResponse(ApiKeyResponse):
    """
    Returned ONCE when a key is created — includes the plaintext key.
    The plaintext is never persisted and never returned again.
    """
    plaintext_key: str
