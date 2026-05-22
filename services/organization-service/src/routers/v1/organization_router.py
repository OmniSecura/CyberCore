from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...global_settings import MAX_FREE_ORGS_PER_OWNER
from ...security.auth_client import get_current_user
from ...security.limiter.rate_limit import limiter
from ...security.limiter import settings
from ...services.organization_service import OrgService
from ...schemas.organization import (
    AcceptOwnershipTransferRequest,
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    TransferOwnershipRequest,
    ReactivateOrganizationRequest,
    FreeCapStatusResponse,
    OrganizationResponse,
    PaginatedOrganizationsResponse,
)

org_router = APIRouter(prefix="/organizations", tags=["Org"])


def _get_service(db: Session = Depends(get_db)) -> OrgService:
    return OrgService(db)


@cbv(org_router)
class OrganizationRouter:

    # ── Create ────────────────────────────────────────────────────────────────

    @org_router.post("/", status_code=status.HTTP_201_CREATED)
    @limiter.limit(settings.POST_ORGANIZATIONS)
    async def create_org(
        self,
        request: Request,
        data: CreateOrganizationRequest,
        current_user: dict = Depends(get_current_user),
        service: OrgService = Depends(_get_service),
    ):
        try:
            service.create_organization(data=data, creator_id=current_user["id"])
            return {"message": "Organization created successfully"}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # ── List my orgs ──────────────────────────────────────────────────────────

    @org_router.get("/my", status_code=status.HTTP_200_OK, response_model=PaginatedOrganizationsResponse)
    @limiter.limit(settings.GET_ORGANIZATIONS_MY)
    async def get_my_orgs(
        self,
        request: Request,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        current_user: dict = Depends(get_current_user),
        service: OrgService = Depends(_get_service),
    ):
        orgs_with_roles, total = service.list_user_orgs_paginated(
            user_id=current_user["id"], page=page, page_size=page_size,
        )

        items: list[OrganizationResponse] = []
        for org, role in orgs_with_roles:
            item = OrganizationResponse.model_validate(org)
            item.role = role
            item.member_count = service.count_org_members(org.id)
            items.append(item)

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return PaginatedOrganizationsResponse(
            items=items, total=total, page=page,
            page_size=page_size, total_pages=total_pages,
        )

    # ── Free-plan ownership cap status ────────────────────────────────────────

    @org_router.get("/free-cap-status", status_code=status.HTTP_200_OK, response_model=FreeCapStatusResponse)
    @limiter.limit(settings.GET_ORGANIZATIONS_FREE_CAP_STATUS)
    async def get_free_cap_status(
        self,
        request: Request,
        current_user: dict = Depends(get_current_user),
        service: OrgService = Depends(_get_service),
    ):
        owned = service.count_owned_free_orgs(current_user["id"])
        return FreeCapStatusResponse(
            owned=owned,
            max=MAX_FREE_ORGS_PER_OWNER,
            can_create=owned < MAX_FREE_ORGS_PER_OWNER,
        )

    # ── Get single org ────────────────────────────────────────────────────────

    @org_router.get("/{slug}", status_code=status.HTTP_200_OK, response_model=OrganizationResponse)
    @limiter.limit(settings.GET_ORGANIZATIONS_SLUG)
    async def get_org(
        self,
        request: Request,
        slug: str,
        current_user: dict = Depends(get_current_user),
        service: OrgService = Depends(_get_service),
    ):
        try:
            org = service.get_org_for_user(slug=slug, user_id=current_user["id"])
            result = OrganizationResponse.model_validate(org)
            result.role = service.get_user_role(org=org, user_id=current_user["id"])
            result.member_count = service.count_org_members(org.id)
            return result
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # ── Update ────────────────────────────────────────────────────────────────

    @org_router.patch("/{slug}", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.PATCH_ORGANIZATIONS_SLUG)
    async def update_org(
        self,
        request: Request,
        slug: str,
        data: UpdateOrganizationRequest,
        current_user: dict = Depends(get_current_user),
        service: OrgService = Depends(_get_service),
    ):
        try:
            service.update_organization(slug=slug, data=data, actor_id=current_user["id"])
            return {"message": "Organization updated successfully"}
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # ── Soft delete ───────────────────────────────────────────────────────────

    @org_router.delete("/{slug}", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.DELETE_ORGANIZATIONS_SLUG)
    async def soft_delete_org(
        self,
        request: Request,
        slug: str,
        current_user: dict = Depends(get_current_user),
        service: OrgService = Depends(_get_service),
    ):
        try:
            service.soft_delete_organization(slug=slug, actor_id=current_user["id"])
            return {"message": "Organization deleted successfully"}
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # ── Transfer ownership ────────────────────────────────────────────────────

    @org_router.patch("/{slug}/transfer-ownership", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.PATCH_ORGANIZATIONS_TRANSFER_OWNERSHIP)
    async def transfer_ownership(
        self,
        request: Request,
        slug: str,
        data: TransferOwnershipRequest,
        current_user: dict = Depends(get_current_user),
        service: OrgService = Depends(_get_service),
    ):
        try:
            service.initiate_transfer_ownership(
                slug=slug,
                actor_id=current_user["id"],
                new_owner_id=data.new_owner_id,
            )
            return {"message": "Transfer initiated — the recipient must accept via the email link"}
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    @org_router.post("/transfer-ownership/accept", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.POST_ORGANIZATIONS_TRANSFER_OWNERSHIP_ACCEPT)
    async def accept_transfer_ownership(
        self,
        request: Request,
        data: AcceptOwnershipTransferRequest,
        current_user: dict = Depends(get_current_user),
        service: OrgService = Depends(_get_service),
    ):
        try:
            org = service.accept_ownership_transfer(
                token=data.token,
                user_id=current_user["id"],
            )
            return {
                "message": "Ownership accepted successfully",
                "organization_slug": org.organization_slug,
                "organization_name": org.organization_name,
            }
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # ── Reactivate ────────────────────────────────────────────────────────────

    @org_router.post("/{org_id}/reactivate", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.POST_ORGANIZATIONS_REACTIVATE)
    async def reactivate_org(
        self,
        request: Request,
        org_id: str,
        data: ReactivateOrganizationRequest,
        current_user: dict = Depends(get_current_user),
        service: OrgService = Depends(_get_service),
    ):
        try:
            org = service.reactivate_organization(
                org_id=org_id,
                actor_id=current_user["id"],
                new_slug=data.new_slug,
            )
            return {
                "message": "Organization reactivated successfully",
                "organization_slug": org.organization_slug,
            }
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
