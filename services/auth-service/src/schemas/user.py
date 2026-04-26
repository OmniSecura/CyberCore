from datetime import datetime
from pydantic import BaseModel, model_validator

from ..security.template_matching import validate_registration


class CreateUser(BaseModel):
    email: str
    full_name: str
    password: str

    @model_validator(mode="after")
    def validate_fields(self) -> "CreateUser":
        result = validate_registration(self.email, self.full_name, self.password)
        if not result.valid:
            raise ValueError(result.all_errors())
        return self


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    """
    Safe subset of User fields returned to the client.

    Deliberately excludes: password_hash, mfa_secret, failed_login_attempts,
    locked_until, last_login_ip, is_superadmin, deleted_at.
    Only fields the user needs to see about their own account are included.
    """
    id:             str
    email:          str
    full_name:      str
    is_active:      bool
    email_verified: bool
    created_at:     datetime

    model_config = {"from_attributes": True}