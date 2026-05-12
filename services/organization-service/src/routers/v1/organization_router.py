from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...security.auth_client import get_current_user
from ...services.organization_service import OrgService
from ...schemas.organization import (
    AcceptOwnershipTransferRequest,
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    TransferOwnershipRequest,
    ReactivateOrganizationRequest,
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
    async def create_org(
        self,
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
    async def get_my_orgs(
        self,
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

    # ── Get single org ────────────────────────────────────────────────────────

    @org_router.get("/{slug}", status_code=status.HTTP_200_OK, response_model=OrganizationResponse)
    async def get_org(
        self,
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
    async def update_org(
        self,
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
    async def soft_delete_org(
        self,
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
    # Two-step: owner initiates → email sent → recipient accepts via token.

    @org_router.patch("/{slug}/transfer-ownership", status_code=status.HTTP_200_OK)
    async def transfer_ownership(
        self,
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
    async def accept_transfer_ownership(
        self,
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
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(e))

    # ── Reactivate ────────────────────────────────────────────────────────────
    # User must provide a new slug if the original one was taken after deletion.
    # If new_slug is not provided, we attempt to restore the original slug.

    @org_router.post("/{org_id}/reactivate", status_code=status.HTTP_200_OK)
    async def reactivate_org(
        self,
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
            # Slug conflict — tell the user to pick a different one
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
