from datetime import datetime
from pydantic import BaseModel, model_validator

class CreateOrganizationRequest(BaseModel):
    organization_name: str
    organization_slug: str
    organization_description: str | None = None
