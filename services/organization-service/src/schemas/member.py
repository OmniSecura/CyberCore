import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

OrgRole = Literal["admin", "member", "viewer"]

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class MemberResponse(BaseModel):
    user_id: str
    role: str
    custom_role_id: Optional[str] = None
    invited_by: Optional[str]
    joined_at: datetime

    model_config = {"from_attributes": True}


class UpdateMemberRoleRequest(BaseModel):
    # Provide exactly one of: built-in `role` OR `custom_role_id`.
    # To clear a custom role and go back to a built-in role, provide `role` only.
    role: Optional[OrgRole] = None
    custom_role_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_exactly_one(self) -> "UpdateMemberRoleRequest":
        if self.role is None and self.custom_role_id is None:
            raise ValueError("Provide either 'role' or 'custom_role_id'")
        if self.role is not None and self.custom_role_id is not None:
            raise ValueError("Provide either 'role' or 'custom_role_id', not both")
        return self


class InviteRequest(BaseModel):
    email: str
    role: OrgRole = "member"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class InviteResponse(BaseModel):
    id: str
    invited_email: str
    role: str
    invited_by: str
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class AcceptInviteRequest(BaseModel):
    token: str
