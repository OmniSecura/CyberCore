from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator

from ..privileges import ALL_PRIVILEGES


class CreateRoleRequest(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    privileges: list[str] = []

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Role name cannot be empty")
        if len(v) > 100:
            raise ValueError("Role name must be 100 characters or fewer")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be a 7-character hex string like #3B82F6")
        return v

    @field_validator("privileges")
    @classmethod
    def validate_privileges(cls, v: list[str]) -> list[str]:
        invalid = [p for p in v if p not in ALL_PRIVILEGES]
        if invalid:
            raise ValueError(f"Unknown privileges: {invalid}")
        return list(set(v))  # deduplicate


class UpdateRoleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    privileges: Optional[list[str]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Role name cannot be empty")
        if len(v) > 100:
            raise ValueError("Role name must be 100 characters or fewer")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be a 7-character hex string like #3B82F6")
        return v

    @field_validator("privileges")
    @classmethod
    def validate_privileges(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        invalid = [p for p in v if p not in ALL_PRIVILEGES]
        if invalid:
            raise ValueError(f"Unknown privileges: {invalid}")
        return list(set(v))


class RoleResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    color: Optional[str]
    privileges: list[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
