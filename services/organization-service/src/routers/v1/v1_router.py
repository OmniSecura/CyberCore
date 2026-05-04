from fastapi import APIRouter
from .organization_router import org_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(org_router, tags=["Org"])
