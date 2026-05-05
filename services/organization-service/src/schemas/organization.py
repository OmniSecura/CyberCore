from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import re

_SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

class CreateOrganizationRequest(BaseModel):
    organization_name: str
    organization_slug: str
    organization_description: Optional[str] = None

    @field_validator("organization_slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError(
                "Slug may only contain lowercase letters, digits and hyphens"
            )
        return v


class UpdateOrganizationRequest(BaseModel):
    organization_name: Optional[str] = None
    organization_slug: Optional[str] = None
    organization_description: Optional[str] = None

class OrganizationResponse(BaseModel):
    organization_name: str
    organization_slug: str
    organization_description: Optional[str]
    plan: str
    created_at: datetime

    model_config = {"from_attributes": True}

class TransferOwnershipRequest(BaseModel):
    new_owner_id: str


class ReactivateOrganizationRequest(BaseModel):
    # Optional — if not provided, service attempts to restore original slug.
    # Required if the original slug was taken by another org after deletion.
    new_slug: Optional[str] = None

    @field_validator("new_slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError(
                "Slug may only contain lowercase letters, digits and hyphens"
            )
        return v
