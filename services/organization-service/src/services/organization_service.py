import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from ..database.models.Organization import Organization
from ..schemas.organization import CreateOrganizationRequest


class OrgService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_slug(self, slug: str):
        return (
            self.db.query(Organization)
            .filter(Organization.organization_slug == slug)
            .first()
        )

    def create_organization(self, data: CreateOrganizationRequest, creator_id: str):
        if self.get_by_slug(data.organization_slug):
            ValueError(f"Organization with slug {data.organization_slug} already exists")

        new_organization = Organization(
            owner_id=creator_id,
            organization_slug=data.organization_slug,
            organization_name=data.organization_name,
            organization_description=data.organization_description,
        )
        self.db.add(new_organization)
        self.db.flush()
        return f"Organization {data.organization_name} created successfully"
