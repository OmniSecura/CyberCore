from fastapi import APIRouter

from .ingest_router import ingest_router
from .auth_router import auth_router
from .logs_router import logs_router
from .api_keys_router import api_keys_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(ingest_router,  tags=["Ingest"])
v1_router.include_router(auth_router,    tags=["Auth"])
v1_router.include_router(logs_router,    tags=["Logs"])
v1_router.include_router(api_keys_router, tags=["API Keys"])
