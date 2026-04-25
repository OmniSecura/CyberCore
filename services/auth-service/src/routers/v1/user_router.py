from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from fastapi_utils.cbv import cbv

from ...services.user_service import UserService
from ...database.models.User import User
from ...database.db_connection import get_db
from ...schemas.user import CreateUser



auth_router = APIRouter(prefix="/users", tags=["Auth"])


def _get_service(db: Session = Depends(get_db)) -> UserService:
    """Wires the session from get_db into the service."""
    return UserService(db)


@cbv(auth_router)
class AuthRouter:

    @auth_router.post("/register", status_code=status.HTTP_201_CREATED)
    def create_user(self, user_data: CreateUser, service: UserService = Depends(_get_service)):
        try:
            service.create_user(user_data)
            return {"message": "Welcome to Cybercore, your account has been created successfully!"}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @auth_router.delete("/{user_id}", status_code=status.HTTP_200_OK)
    def delete_user(
            self,
            user_id: str,
            service: UserService = Depends(_get_service)
    ):
        try:
            return {"message": service.soft_delete_user(user_id)}
        except LookupError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))



