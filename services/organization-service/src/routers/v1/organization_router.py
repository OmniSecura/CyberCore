from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...database.models.Organization import Organization
from ...security.auth_client import get_current_user
from ...services.organization_service import OrgService
from ...schemas.organization import CreateOrganizationRequest


org_router = APIRouter(prefix="/organization", tags=["Org"])

def _get_service(db: Session = Depends(get_db)) -> OrgService:
    return OrgService(db)

@cbv(org_router)
class OrganizationRouter:

    @org_router.post("/organization", status_code=status.HTTP_201_CREATED)
    async def create_org(
            self,
            data: CreateOrganizationRequest,
            current_user: dict = Depends(get_current_user),
            service: OrgService = Depends(_get_service),
    ):
        try:
            new_org = service.create_organization(
                data=data,
                creator_id=current_user["id"],  # ← ["id"]
            )
            return {"message": "Organization created successfully"}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
