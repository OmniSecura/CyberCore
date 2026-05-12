from fastapi import APIRouter

from .scan_router import scan_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(scan_router)
