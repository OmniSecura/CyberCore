from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...database.models.Organization import Organization
from ...security.auth_client import get_current_user
from ...security.limiter.rate_limit import limiter
from ...security.limiter import settings
from ...services.role_service import RoleService
from ...schemas.role import CreateRoleRequest, UpdateRoleRequest, RoleResponse
from ...privileges import get_registry_for_api, get_user_privileges

role_router = APIRouter(prefix="/organizations/roles", tags=["Roles"])


def _role_svc(db: Session = Depends(get_db)) -> RoleService:
    return RoleService(db)


def _get_active_org(db: Session, slug: str) -> Organization:
    org = (
        db.query(Organization)
        .filter(Organization.organization_slug == slug, Organization.deleted_at.is_(None))
        .first()
    )
    if not org:
        raise LookupError("Organization not found")
    return org


@role_router.get("/privileges", status_code=status.HTTP_200_OK)
@limiter.limit(settings.GET_ROLES_PRIVILEGES)
async def list_privileges(request: Request):
    """Returns all available privileges grouped by category."""
    return get_registry_for_api()


@role_router.get("/{slug}/my-privileges", status_code=status.HTTP_200_OK)
@limiter.limit(settings.GET_ROLES_MY_PRIVILEGES)
async def my_privileges(
    request: Request,
    slug: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the set of privileges the current user has in this org."""
    try:
        org = _get_active_org(db, slug)
        privs = get_user_privileges(db, org, current_user["id"])
        return {"privileges": sorted(privs)}
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@cbv(role_router)
class RoleRouter:

    @role_router.get("/{slug}", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.GET_ROLES)
    async def list_roles(
        self,
        request: Request,
        slug: str,
        current_user: dict = Depends(get_current_user),
        service: RoleService = Depends(_role_svc),
    ):
        try:
            roles = service.list_roles(slug=slug, actor_id=current_user["id"])
            return [RoleResponse.model_validate(r) for r in roles]
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    @role_router.post("/{slug}", status_code=status.HTTP_201_CREATED)
    @limiter.limit(settings.POST_ROLES)
    async def create_role(
        self,
        request: Request,
        slug: str,
        data: CreateRoleRequest,
        current_user: dict = Depends(get_current_user),
        service: RoleService = Depends(_role_svc),
    ):
        try:
            role = service.create_role(
                slug=slug,
                actor_id=current_user["id"],
                name=data.name,
                description=data.description,
                color=data.color,
                privileges=data.privileges,
            )
            return RoleResponse.model_validate(role)
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    @role_router.patch("/{slug}/{role_id}", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.PATCH_ROLES)
    async def update_role(
        self,
        request: Request,
        slug: str,
        role_id: str,
        data: UpdateRoleRequest,
        current_user: dict = Depends(get_current_user),
        service: RoleService = Depends(_role_svc),
    ):
        try:
            role = service.update_role(
                slug=slug,
                role_id=role_id,
                actor_id=current_user["id"],
                name=data.name,
                description=data.description,
                color=data.color,
                privileges=data.privileges,
            )
            return RoleResponse.model_validate(role)
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    @role_router.delete("/{slug}/{role_id}", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.DELETE_ROLES)
    async def delete_role(
        self,
        request: Request,
        slug: str,
        role_id: str,
        current_user: dict = Depends(get_current_user),
        service: RoleService = Depends(_role_svc),
    ):
        try:
            service.delete_role(
                slug=slug,
                role_id=role_id,
                actor_id=current_user["id"],
            )
            return {"message": "Role deleted successfully"}
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
