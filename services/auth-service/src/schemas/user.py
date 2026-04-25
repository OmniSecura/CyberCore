from pydantic import BaseModel, EmailStr, field_validator, model_validator
from ..security.template_matching import (
    validate_email,
    validate_full_name,
    validate_password,
    validate_registration,
)

class CreateUser(BaseModel):
    email: str
    full_name: str
    password: str
    @model_validator(mode="after")
    def validate_all_fields(self) -> "CreateUser":
        # Validate all at the same time
        result = validate_registration(self.email, self.full_name, self.password)
        if not result.valid:
            raise ValueError(str(result.all_errors()))
        return self
