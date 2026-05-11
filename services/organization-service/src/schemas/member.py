import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

OrgRole = Literal["admin", "member", "viewer"]

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class MemberResponse(BaseModel):
    user_id: str
    role: str
    invited_by: Optional[str]
    joined_at: datetime

    model_config = {"from_attributes": True}


class UpdateMemberRoleRequest(BaseModel):
    role: OrgRole


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
