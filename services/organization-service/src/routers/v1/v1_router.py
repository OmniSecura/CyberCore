from fastapi import APIRouter
from .organization_router import org_router
from .member_router import invite_router, member_router
from .role_router import role_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(org_router, tags=["Org"])
v1_router.include_router(member_router, tags=["Members"])
v1_router.include_router(invite_router, tags=["Invites"])
v1_router.include_router(role_router, tags=["Roles"])
