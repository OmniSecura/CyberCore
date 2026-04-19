from fastapi import APIRouter
from .user_router import auth_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth_router, tags=["Auth"])
