from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...security.auth_client import get_current_user
from ...services.member_service import MemberService
from ...services.invite_service import InviteService
from ...schemas.member import (
    AcceptInviteRequest,
    InviteRequest,
    InviteResponse,
    MemberResponse,
    UpdateMemberRoleRequest,
)

member_router = APIRouter(prefix="/organizations/members", tags=["Members"])
invite_router = APIRouter(prefix="/invites", tags=["Invites"])


def _member_svc(db: Session = Depends(get_db)) -> MemberService:
    return MemberService(db)


def _invite_svc(db: Session = Depends(get_db)) -> InviteService:
    return InviteService(db)


# ── Members ────────────────────────────────────────────────────────────────────

@cbv(member_router)
class MemberRouter:

    @member_router.get("/{slug}/members", status_code=status.HTTP_200_OK)
    async def list_members(
        self,
        slug: str,
        current_user: dict = Depends(get_current_user),
        service: MemberService = Depends(_member_svc),
    ):
        try:
            members = service.list_members(slug=slug, actor_id=current_user["id"])
            return [MemberResponse.model_validate(m) for m in members]
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    @member_router.patch("/{slug}/members/{user_id}", status_code=status.HTTP_200_OK)
    async def update_member_role(
        self,
        slug: str,
        user_id: str,
        data: UpdateMemberRoleRequest,
        current_user: dict = Depends(get_current_user),
        service: MemberService = Depends(_member_svc),
    ):
        try:
            service.update_member_role(
                slug=slug,
                user_id=user_id,
                actor_id=current_user["id"],
                role=data.role,
                custom_role_id=data.custom_role_id,
            )
            return {"message": "Member role updated successfully"}
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @member_router.delete("/{slug}/members/{user_id}", status_code=status.HTTP_200_OK)
    async def remove_member(
        self,
        slug: str,
        user_id: str,
        current_user: dict = Depends(get_current_user),
        service: MemberService = Depends(_member_svc),
    ):
        try:
            service.remove_member(
                slug=slug,
                user_id=user_id,
                actor_id=current_user["id"],
            )
            return {"message": "Member removed successfully"}
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # ── Invites (org-scoped) ───────────────────────────────────────────────────

    @member_router.post("/{slug}/invites", status_code=status.HTTP_201_CREATED)
    async def create_invite(
        self,
        slug: str,
        data: InviteRequest,
        current_user: dict = Depends(get_current_user),
        service: InviteService = Depends(_invite_svc),
    ):
        try:
            invite = service.create_invite(
                slug=slug,
                actor_id=current_user["id"],
                actor_name=current_user.get("full_name") or current_user["email"],
                email=data.email,
                role=data.role,
            )
            return {"message": "Invite sent successfully", "invite_id": invite.id}
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    @member_router.get("/{slug}/invites", status_code=status.HTTP_200_OK)
    async def list_invites(
        self,
        slug: str,
        current_user: dict = Depends(get_current_user),
        service: InviteService = Depends(_invite_svc),
    ):
        try:
            invites = service.list_invites(slug=slug, actor_id=current_user["id"])
            return [InviteResponse.model_validate(i) for i in invites]
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    @member_router.delete("/{slug}/invites/{invite_id}", status_code=status.HTTP_200_OK)
    async def revoke_invite(
        self,
        slug: str,
        invite_id: str,
        current_user: dict = Depends(get_current_user),
        service: InviteService = Depends(_invite_svc),
    ):
        try:
            service.revoke_invite(
                slug=slug,
                invite_id=invite_id,
                actor_id=current_user["id"],
            )
            return {"message": "Invite revoked successfully"}
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ── Accept invite (token-based, no org slug needed) ───────────────────────────

@cbv(invite_router)
class InviteRouter:

    @invite_router.post("/accept", status_code=status.HTTP_200_OK)
    async def accept_invite(
        self,
        data: AcceptInviteRequest,
        current_user: dict = Depends(get_current_user),
        service: InviteService = Depends(_invite_svc),
    ):
        try:
            invite, org = service.accept_invite(
                token=data.token,
                user_id=current_user["id"],
                user_email=current_user["email"],
            )
            return {
                "message": "Successfully joined the organization",
                "organization_slug": org.organization_slug,
                "organization_name": org.organization_name,
                "role": invite.role,
            }
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
